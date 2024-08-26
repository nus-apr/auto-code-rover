"""
Interfacing with OpenAI models.
"""

import json
import os
import sys
from typing import Literal, cast

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
        cost_per_input: float,
        cost_per_output: float,
        parallel_tool_call: bool = False,
    ):
        if self._initialized:
            return
        super().__init__(name, cost_per_input, cost_per_output, parallel_tool_call)
        # client for making request
        self.client: OpenAI | None = None
        self._initialized = True

    def setup(self) -> None:
        """
        Check API key, base url, and initialize OpenAI client. The stop token ids are set because some open-sourced models did not define its eos-token well
        """
        if self.client is None:
            eval_api_key = self.check_api_key()
            eval_base_url = self.check_base_url()
            self.client = OpenAI(base_url=eval_base_url, api_key=eval_api_key)
        stop_token_ids = os.getenv("VLLM_STOP_TOKEN_IDS", "")
        if stop_token_ids:
            stop_token_ids = [int(sid) for sid in stop_token_ids.split(',')]
        self.vllm_extra_body = {"stop_token_ids": stop_token_ids} if stop_token_ids else None


    def check_api_key(self) -> str:
        # ZZ: for models served by vllm local server, there are no api key required by default 
        key = os.getenv("VLLM_API_KEY", "placeholder")
        if not key:
            print("Please set the OPENAI_KEY env var")
            sys.exit(1)
        return key

    def check_base_url(self) -> str:
        # ZZ: for models served by vllm local server, the base_url is a required parameter
        base_url = os.getenv("VLLM_BASE_URL")
        if not base_url:
            print("Please set the VLLM_BASE_URL env var")
            sys.exit(1)
        return base_url

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

    # FIXME: the returned type contains OpenAI specific Types, which should be avoided
    @retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
    def call(
        self,
        messages: list[dict],
        top_p: float = 1,
        tools: list[dict] | None = None,
        response_format: Literal["text", "json_object"] = "text",
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
        assert self.client is not None
        # ZZ: vllm does not support tools, manually handle the tool calling !
        # ZZ: if response_format is json_object, switch back to text and specify directly in the prompt since vllm is buggy with this setup
        orig_res_fm = response_format
        if response_format == 'json_object':
            messages[-1]['content'] += "\n\nPlease respond in JSON format directly without any introductory or concluding sentence."
            response_format = "text" # manually switch to text and ask for response in JSON format explicitly in prompt
        try:
            response: ChatCompletion = self.client.chat.completions.create(
                model=self.name,
                messages=messages,  # type: ignore
                temperature=common.MODEL_TEMP,
                response_format=ResponseFormat(type=response_format),
                max_tokens=None,
                top_p=top_p,
                stream=False,
                extra_body=self.vllm_extra_body # ZZ: vllm specific
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
            if orig_res_fm == 'json_object':
                # ZZ: manual cleanning for json format 
                if content.strip().startswith("```json"):
                    content = content.strip()[7:-4]
                if content.strip().startswith("```"):
                    content = content.strip()[3:-4]
            return (
                content,
                cost,
                input_tokens,
                output_tokens,
            )
        except BadRequestError as e:
            if e.code == "context_length_exceeded":
                log_and_print("Context length exceeded")
            print(e)
            raise e


class Llama3_70B_vllm(OpenaiModel):
    def __init__(self):
        super().__init__(
            "Llama-3.1-70B-Instruct", 0., 0., parallel_tool_call=True
        )
        self.note = "Meta-Llama-3.1-70B-Instruct served by local vllm server. Cost per input/output assumed to be zero."



class DeepseekCoderV2_16B_vllm(OpenaiModel):
    def __init__(self):
        super().__init__(
            "DeepSeek-Coder-V2-Lite-Instruct", 0., 0., parallel_tool_call=True
        )
        self.note = "DeepSeek-Coder-V2-Lite-Instruct served by local vllm server. Cost per input/output assumed to be zero."


class DeepseekCoderV2_API(OpenaiModel):
    def __init__(self):
        super().__init__(
            "deepseek-coder", 0., 0., parallel_tool_call=True
        )
        self.note = "DeepSeek-Coder-API served in openai style. Cost per input/output assumed to be zero."