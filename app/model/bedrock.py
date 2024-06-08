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


class BedrockModel(Model):
    """
    Base class for creating Singleton instances of Amazon Bedrock models.
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
        self._model_provider = self.name.split(".")[0]
        self._initialized = True

    def setup(self) -> None:
        """
        Check API key.
        """
        self.check_api_key()

    def check_api_key(self) -> str:
        # See https://litellm.vercel.app/docs/providers/bedrock
        required_env_vars = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION_NAME",
        ]
        if len(set(os.environ).intersection(required_env_vars)) != len(
            required_env_vars
        ):
            print(
                "Missing env vars. Please refer to https://litellm.vercel.app/docs/providers/bedrock"
            )
            sys.exit(1)
        return os.getenv(required_env_vars[-1])

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
        try:
            if self._model_provider == "bedrock/anthropic":
                # antropic models - prefilling response with { increase the success rate
                # of producing json output
                prefill_content = "{"
                if response_format == "json_object":  # prefill
                    messages.append({"role": "assistant", "content": prefill_content})

            response = litellm.completion(
                model=self.name,
                messages=messages,
                temperature=common.MODEL_TEMP,
                max_tokens=1024,
                top_p=top_p,
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


class AnthropicClaude2(BedrockModel):
    def __init__(self):
        super().__init__(
            "bedrock/anthropic.claude-v2:1",
            0.00000025,
            0.00000125,
            parallel_tool_call=True,
        )
        self.note = "Older Claude model"


class AnthropicClaude3Opus(BedrockModel):
    def __init__(self):
        super().__init__(
            "bedrock/anthropic.claude-3-opus-20240229-v1:0",
            0.000015,
            0.000075,
            parallel_tool_call=True,
        )
        self.note = "Most powerful model from Antropic"


class AnthropicClaude3Sonnet(BedrockModel):
    def __init__(self):
        super().__init__(
            "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
            0.000003,
            0.000015,
            parallel_tool_call=True,
        )
        self.note = "Most balanced (intelligence and speed) model from Antropic"


class AnthropicClaude3Haiku(BedrockModel):
    def __init__(self):
        super().__init__(
            "bedrock/anthropic.claude-3-haiku-20240307-v1:0",
            0.00000025,
            0.00000125,
            parallel_tool_call=True,
        )
        self.note = "Fastest model from Antropic"
