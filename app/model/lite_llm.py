"""
For models other than those from OpenAI, use LiteLLM if possible.
"""

import os
import sys
from typing import Literal

import litellm
from openai import BadRequestError
from openai.types.chat import ChatCompletionMessage
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.log import log_and_print
from app.model import common
from app.model.common import Model


class AntropicModel(Model):
    """
    Base class for creating Singleton instances of Antropic models.
    """

    _instances = {}

    def __new__(cls):
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
            cls._instances[cls]._initialized = False
        return cls._instances[cls]

    def __init__(self, name: str, cost_per_input: float, cost_per_output: float):
        if self._initialized:
            return
        super().__init__(name, cost_per_input, cost_per_output)
        self._initialized = True

    def setup(self) -> None:
        """
        Check API key.
        """
        self.check_api_key()

    def check_api_key(self) -> str:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            print("Please set the ANTHROPIC_API_KEY env var")
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

    @retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
    def call(
        self,
        messages: list[dict],
        top_p=1,
        tools=None,
        response_format: Literal["text", "json_object"] = "text",
    ):
        # FIXME: ignore tools field since we don't use tools now
        try:
            # FIXME: antropic does not support response_format field
            # so we should make it clean in the prompt, and possibly
            # prefill the assistant field with {
            prefill_content = "{"
            if response_format == "json_object":  # prefill
                messages.append({"role": "assistant", "content": prefill_content})

            response = litellm.completion(
                model=self.name,
                messages=messages,
                temperature=common.MODEL_TEMP,
                max_tokens=1024,
                top_p=top_p,
            )
            input_tokens = int(response.usage.prompt_tokens)
            output_tokens = int(response.usage.completion_tokens)
            cost = self.calc_cost(input_tokens, output_tokens)

            common.thread_cost.process_cost += cost
            common.thread_cost.process_input_tokens += input_tokens
            common.thread_cost.process_output_tokens += output_tokens

            raw_response = response.choices[0].message
            log_and_print(f"Raw model response: {raw_response}")
            content = self.extract_resp_content(raw_response)
            if response_format == "json_object":
                # prepend the prefilled character
                if not content.startswith(prefill_content):
                    content = prefill_content + content
            return content, cost, input_tokens, output_tokens

        except BadRequestError as e:
            if e.code == "context_length_exceeded":
                log_and_print("Context length exceeded")
            raise e


class Claude3Haiku(AntropicModel):
    def __init__(self):
        super().__init__("claude-3-haiku-20240307", 0.00000025, 0.00000125)
        self.parallel_tool_call = True
        self.note = "Fastest model from Antropic"


class Claude3Sonnet(AntropicModel):
    def __init__(self):
        super().__init__("claude-3-sonnet-20240229", 0.000003, 0.000015)
        self.parallel_tool_call = True
        self.note = "Most balanced (intelligence and speed) model from Antropic"


class Claude3Opus(AntropicModel):
    def __init__(self):
        super().__init__("claude-3-opus-20240229", 0.000015, 0.000075)
        self.parallel_tool_call = True
        self.note = "Most powerful model from Antropic"
