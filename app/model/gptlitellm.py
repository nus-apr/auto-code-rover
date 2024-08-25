"""
For models other than those from OpenAI, use LiteLLM if possible.
"""

import os
import sys
from typing import Literal

import litellm
from litellm.utils import Choices, Message, ModelResponse
from openai import BadRequestError
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.log import log_and_print
from app.model import common
from app.model.common import Model


class OpenaiLiteLLMModel(Model):
    """
    Base class for creating Singleton instances of Openai models.
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
        self._initialized = True

    def setup(self) -> None:
        """
        Check API key.
        """
        self.check_api_key()

    def check_api_key(self) -> str:
        key_name = "OPENAI_KEY"
        key = os.getenv(key_name)
        if not key:
            print(f"Please set the {key_name} env var")
            sys.exit(1)
        os.environ["OPENAI_API_KEY"] = key
        return key

    def extract_resp_content(self, chat_message: Message) -> str:
        """
        Given a chat completion message, extract the content from it.
        """
        content = chat_message.content
        if content is None:
            return ""
        else:
            return content

    @retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
    def call(
        self,
        messages: list[dict],
        top_p=1,
        tools=None,
        response_format: Literal["text", "json_object"] = "text",
        **kwargs,
    ):
        # FIXME: ignore tools field since we don't use tools now
        try:
            prefill_content = "{"
            if response_format == "json_object":  # prefill
                messages.append({"role": "assistant", "content": prefill_content})

            response = litellm.completion(
                model=(
                    self.name
                    if not self.name.startswith("litellm-")
                    else self.name[len("litellm-") :]
                ),
                messages=messages,
                temperature=common.MODEL_TEMP,
                max_tokens=1024,
                response_format={"type": response_format},
                top_p=top_p,
                base_url=os.getenv("OPENAI_API_BASE_URL", None),
                stream=False,
            )
            assert isinstance(response, ModelResponse)
            resp_usage = response.usage
            assert resp_usage is not None
            input_tokens = int(resp_usage.prompt_tokens)
            output_tokens = int(resp_usage.completion_tokens)
            cost = self.calc_cost(input_tokens, output_tokens)

            common.thread_cost.process_cost += cost
            common.thread_cost.process_input_tokens += input_tokens
            common.thread_cost.process_output_tokens += output_tokens

            first_resp_choice = response.choices[0]
            assert isinstance(first_resp_choice, Choices)
            resp_msg: Message = first_resp_choice.message
            content = self.extract_resp_content(resp_msg)
            if response_format == "json_object":
                # prepend the prefilled character
                if not content.startswith(prefill_content):
                    content = prefill_content + content

            return content, cost, input_tokens, output_tokens

        except BadRequestError as e:
            if e.code == "context_length_exceeded":
                log_and_print("Context length exceeded")
            raise e


class Gpt4o_20240513LiteLLM(OpenaiLiteLLMModel):
    def __init__(self):
        super().__init__(
            "litellm-gpt-4o-2024-05-13", 0.000005, 0.000015, parallel_tool_call=True
        )
        self.note = "Multimodal model. Up to Oct 2023."


class Gpt4_Turbo20240409LiteLLM(OpenaiLiteLLMModel):
    def __init__(self):
        super().__init__(
            "litellm-gpt-4-turbo-2024-04-09", 0.00001, 0.00003, parallel_tool_call=True
        )
        self.note = "Turbo with vision. Up to Dec 2023."


class Gpt4_0125PreviewLiteLLM(OpenaiLiteLLMModel):
    def __init__(self):
        super().__init__(
            "litellm-gpt-4-0125-preview", 0.00001, 0.00003, parallel_tool_call=True
        )
        self.note = "Turbo. Up to Dec 2023."


class Gpt4_1106PreviewLiteLLM(OpenaiLiteLLMModel):
    def __init__(self):
        super().__init__(
            "litellm-gpt-4-1106-preview", 0.00001, 0.00003, parallel_tool_call=True
        )
        self.note = "Turbo. Up to Apr 2023."


class Gpt35_Turbo0125LiteLLM(OpenaiLiteLLMModel):
    # cheapest gpt model
    def __init__(self):
        super().__init__(
            "litellm-gpt-3.5-turbo-0125", 0.0000005, 0.0000015, parallel_tool_call=True
        )
        self.note = "Turbo. Up to Sep 2021."


class Gpt35_Turbo1106LiteLLM(OpenaiLiteLLMModel):
    def __init__(self):
        super().__init__(
            "litellm-gpt-3.5-turbo-1106", 0.000001, 0.000002, parallel_tool_call=True
        )
        self.note = "Turbo. Up to Sep 2021."


class Gpt35_Turbo16k_0613LiteLLM(OpenaiLiteLLMModel):
    def __init__(self):
        super().__init__("litellm-gpt-3.5-turbo-16k-0613", 0.000003, 0.000004)
        self.note = "Turbo. Deprecated. Up to Sep 2021."


class Gpt35_Turbo0613LiteLLM(OpenaiLiteLLMModel):
    def __init__(self):
        super().__init__("litellm-gpt-3.5-turbo-0613", 0.0000015, 0.000002)
        self.note = "Turbo. Deprecated. Only 4k window. Up to Sep 2021."


class Gpt4_0613LiteLLM(OpenaiLiteLLMModel):
    def __init__(self):
        super().__init__("litellm-gpt-4-0613", 0.00003, 0.00006)
        self.note = "Not turbo. Up to Sep 2021."
