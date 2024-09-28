"""
Interfacing with OpenAI models.
"""

import json
import os
import sys
from typing import Literal, cast

from loguru import logger
from openai import BadRequestError, OpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion_message_tool_call import (
    Function as OpenaiFunction,
)
from openai.types.chat.chat_completion_tool_choice_option_param import (
    ChatCompletionToolChoiceOptionParam,
)
from openai.types.chat.completion_create_params import ResponseFormat
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.data_structures import FunctionCallIntent
from app.log import log_and_print
from app.model import common
from app.model.common import Model


class OpenaiModel(Model):
    """
    Base class for creating Singleton instances of OpenAI models.
    We use native API from OpenAI instead of LiteLLM.
    """

    _instances = {}

    def __new__(cls):
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
            cls._instances[cls]._initialized = False
        return cls._instances[cls]

    def __init__(
        self,
        name: str,
        max_output_token: int,
        cost_per_input: float,
        cost_per_output: float,
        parallel_tool_call: bool = False,
    ):
        if self._initialized:
            return
        super().__init__(name, cost_per_input, cost_per_output, parallel_tool_call)
        # max number of output tokens allowed in model response
        # sometimes we want to set a lower number for models with smaller context window,
        # because output token limit consumes part of the context window
        self.max_output_token = max_output_token
        # client for making request
        self.client: OpenAI | None = None
        self._initialized = True

    def setup(self) -> None:
        """
        Check API key, and initialize OpenAI client.
        """
        if self.client is None:
            key = self.check_api_key()
            self.client = OpenAI(api_key=key)

    def check_api_key(self) -> str:
        key = os.getenv("OPENAI_KEY")
        if not key:
            print("Please set the OPENAI_KEY env var")
            sys.exit(1)
        return key

    def extract_resp_content(
        self, chat_completion_message: ChatCompletionMessage
    ) -> str:
        """
        Given a chat completion message, extract the content from it.
        """
        content = chat_completion_message.content
        if content is None:
            return ""
        else:
            return content

    def extract_resp_func_calls(
        self,
        chat_completion_message: ChatCompletionMessage,
    ) -> list[FunctionCallIntent]:
        """
        Given a chat completion message, extract the function calls from it.
        Args:
            chat_completion_message (ChatCompletionMessage): The chat completion message.
        Returns:
            List[FunctionCallIntent]: A list of function calls.
        """
        result = []
        tool_calls = chat_completion_message.tool_calls
        if tool_calls is None:
            return result

        call: ChatCompletionMessageToolCall
        for call in tool_calls:
            called_func: OpenaiFunction = call.function
            func_name = called_func.name
            func_args_str = called_func.arguments
            # maps from arg name to arg value
            if func_args_str == "":
                args_dict = {}
            else:
                try:
                    args_dict = json.loads(func_args_str, strict=False)
                except json.decoder.JSONDecodeError:
                    args_dict = {}
            func_call_intent = FunctionCallIntent(func_name, args_dict, called_func)
            result.append(func_call_intent)

        return result

    # FIXME: the returned type contains OpenAI specific Types, which should be avoided
    @retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
    def call(
        self,
        messages: list[dict],
        top_p: float = 1,
        tools: list[dict] | None = None,
        response_format: Literal["text", "json_object"] = "text",
        temperature: float | None = None,
        **kwargs,
    ) -> tuple[
        str,
        list[ChatCompletionMessageToolCall] | None,
        list[FunctionCallIntent],
        float,
        int,
        int,
    ]:
        """
        Calls the openai API to generate completions for the given inputs.
        Assumption: we only retrieve one choice from the API response.

        Args:
            messages (List): A list of messages.
                            Each item is a dict (e.g. {"role": "user", "content": "Hello, world!"})
            top_p (float): The top_p to use. We usually do not vary this, so not setting it as a cmd-line argument. (from 0 to 1)
            tools (List, optional): A list of tools.

        Returns:
            Raw response and parsed components.
            The raw response is to be sent back as part of the message history.
        """
        if temperature is None:
            temperature = common.MODEL_TEMP

        assert self.client is not None
        try:
            if tools is not None and len(tools) == 1:
                # there is only one tool => force the model to use it
                tool_name = tools[0]["function"]["name"]
                tool_choice = {"type": "function", "function": {"name": tool_name}}
                response: ChatCompletion = self.client.chat.completions.create(
                    model=self.name,
                    messages=messages,  # type: ignore
                    tools=tools,  # type: ignore
                    tool_choice=cast(ChatCompletionToolChoiceOptionParam, tool_choice),
                    temperature=temperature,
                    response_format=cast(ResponseFormat, {"type": response_format}),
                    max_tokens=self.max_output_token,
                    top_p=top_p,
                    stream=False,
                )
            else:
                response: ChatCompletion = self.client.chat.completions.create(
                    model=self.name,
                    messages=messages,  # type: ignore
                    tools=tools,  # type: ignore
                    temperature=temperature,
                    response_format=cast(ResponseFormat, {"type": response_format}),
                    max_tokens=self.max_output_token,
                    top_p=top_p,
                    stream=False,
                )

            usage_stats = response.usage
            assert usage_stats is not None

            input_tokens = int(usage_stats.prompt_tokens)
            output_tokens = int(usage_stats.completion_tokens)
            cost = self.calc_cost(input_tokens, output_tokens)

            common.thread_cost.process_cost += cost
            common.thread_cost.process_input_tokens += input_tokens
            common.thread_cost.process_output_tokens += output_tokens

            raw_response = response.choices[0].message
            # log_and_print(f"Raw model response: {raw_response}")
            content = self.extract_resp_content(raw_response)
            raw_tool_calls = raw_response.tool_calls
            func_call_intents = self.extract_resp_func_calls(raw_response)
            return (
                content,
                raw_tool_calls,
                func_call_intents,
                cost,
                input_tokens,
                output_tokens,
            )
        except BadRequestError as e:
            logger.debug("BadRequestError ({}): messages={}", e.code, messages)
            if e.code == "context_length_exceeded":
                log_and_print("Context length exceeded")
            raise e


class Gpt4o_20240806(OpenaiModel):
    def __init__(self):
        super().__init__(
            "gpt-4o-2024-08-06", 16384, 0.0000025, 0.000010, parallel_tool_call=True
        )
        self.note = "Multimodal model. Up to Apr 2023."


class Gpt4o_20240513(OpenaiModel):
    def __init__(self):
        super().__init__(
            "gpt-4o-2024-05-13", 4096, 0.000005, 0.000015, parallel_tool_call=True
        )
        self.note = "Multimodal model. Up to Oct 2023."


class Gpt4_Turbo20240409(OpenaiModel):
    def __init__(self):
        super().__init__(
            "gpt-4-turbo-2024-04-09", 4096, 0.00001, 0.00003, parallel_tool_call=True
        )
        self.note = "Turbo with vision. Up to Dec 2023."


class Gpt4_0125Preview(OpenaiModel):
    def __init__(self):
        super().__init__(
            "gpt-4-0125-preview", 4096, 0.00001, 0.00003, parallel_tool_call=True
        )
        self.note = "Turbo. Up to Dec 2023."


class Gpt4_1106Preview(OpenaiModel):
    def __init__(self):
        super().__init__(
            "gpt-4-1106-preview", 4096, 0.00001, 0.00003, parallel_tool_call=True
        )
        self.note = "Turbo. Up to Apr 2023."


class Gpt35_Turbo0125(OpenaiModel):
    # cheapest gpt model
    def __init__(self):
        super().__init__(
            "gpt-3.5-turbo-0125", 1024, 0.0000005, 0.0000015, parallel_tool_call=True
        )
        self.note = "Turbo. Up to Sep 2021."


class Gpt35_Turbo1106(OpenaiModel):
    def __init__(self):
        super().__init__(
            "gpt-3.5-turbo-1106", 1024, 0.000001, 0.000002, parallel_tool_call=True
        )
        self.note = "Turbo. Up to Sep 2021."


class Gpt35_Turbo16k_0613(OpenaiModel):
    def __init__(self):
        super().__init__("gpt-3.5-turbo-16k-0613", 1024, 0.000003, 0.000004)
        self.note = "Turbo. Deprecated. Up to Sep 2021."


class Gpt35_Turbo0613(OpenaiModel):
    def __init__(self):
        super().__init__("gpt-3.5-turbo-0613", 512, 0.0000015, 0.000002)
        self.note = "Turbo. Deprecated. Only 4k window. Up to Sep 2021."


class Gpt4_0613(OpenaiModel):
    def __init__(self):
        super().__init__("gpt-4-0613", 512, 0.00003, 0.00006)
        self.note = "Not turbo. Up to Sep 2021."


class Gpt4o_mini_20240718(OpenaiModel):
    def __init__(self):
        super().__init__("gpt-4o-mini-2024-07-18", 4096, 0.00000015, 0.0000006)
