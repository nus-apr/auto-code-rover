import os
import sys
import threading
from abc import ABC, abstractmethod
from typing import Literal

import litellm
from litellm import cost_per_token
from litellm.utils import Choices, Message, ModelResponse
from openai import BadRequestError
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.log import log_and_cprint, log_and_print

# Variables for each process. Since models are singleton objects, their references are copied
# to each process, but they all point to the same objects. For safe updating costs per process,
# we define the accumulators here.

thread_cost = threading.local()
thread_cost.process_cost = 0.0
thread_cost.process_input_tokens = 0
thread_cost.process_output_tokens = 0


class Model(ABC):
    def __init__(
        self,
        name: str,
        cost_per_input: float,
        cost_per_output: float,
        parallel_tool_call: bool = False,
    ):
        self.name: str = name
        # cost stats - zero for local models
        self.cost_per_input: float = cost_per_input
        self.cost_per_output: float = cost_per_output
        # whether the model supports parallel tool call
        self.parallel_tool_call: bool = parallel_tool_call

    @abstractmethod
    def check_api_key(self) -> str:
        raise NotImplementedError("abstract base class")

    @abstractmethod
    def setup(self) -> None:
        raise NotImplementedError("abstract base class")

    @abstractmethod
    def call(self, messages: list[dict], **kwargs):
        raise NotImplementedError("abstract base class")

    def calc_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculates the cost of a request based on the number of input/output tokens.
        """
        input_cost = self.cost_per_input * input_tokens
        output_cost = self.cost_per_output * output_tokens
        cost = input_cost + output_cost
        log_and_cprint(
            f"Model API request cost info: "
            f"input_tokens={input_tokens}, output_tokens={output_tokens}, cost={cost:.6f}",
            style="yellow",
        )
        return cost

    def get_overall_exec_stats(self):
        return {
            "model": self.name,
            "input_cost_per_token": self.cost_per_input,
            "output_cost_per_token": self.cost_per_output,
            "total_input_tokens": thread_cost.process_input_tokens,
            "total_output_tokens": thread_cost.process_output_tokens,
            "total_tokens": thread_cost.process_input_tokens
            + thread_cost.process_output_tokens,
            "total_cost": thread_cost.process_cost,
        }


class LiteLLMGeneric(Model):
    """
    Base class for creating instances of LiteLLM-supported models.
    """

    _instances = {}

    def __new__(cls, model_name: str, cost_per_input: float, cost_per_output: float):
        if model_name not in cls._instances:
            cls._instances[model_name] = super().__new__(cls)
            cls._instances[model_name]._initialized = False
        return cls._instances[model_name]

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
        pass

    def check_api_key(self) -> str:
        return ""

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
                model=self.name,
                messages=messages,
                temperature=MODEL_TEMP,
                max_tokens=os.getenv("ACR_TOKEN_LIMIT", 1024),
                response_format=(
                    {"type": response_format} if "gpt" in self.name else None
                ),
                top_p=top_p,
                stream=False,
            )
            assert isinstance(response, ModelResponse)
            resp_usage = response.usage
            assert resp_usage is not None
            input_tokens = int(resp_usage.prompt_tokens)
            output_tokens = int(resp_usage.completion_tokens)
            cost = self.calc_cost(input_tokens, output_tokens)

            thread_cost.process_cost += cost
            thread_cost.process_input_tokens += input_tokens
            thread_cost.process_output_tokens += output_tokens

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


MODEL_HUB = {}


def register_model(model: Model):
    global MODEL_HUB
    MODEL_HUB[model.name] = model


def get_all_model_names():
    return list(MODEL_HUB.keys())


# To be set at runtime - the selected model for a run
SELECTED_MODEL: Model


def set_model(model_name: str):
    global SELECTED_MODEL
    if model_name not in MODEL_HUB and not model_name.startswith("litellm-generic-"):
        print(f"Invalid model name: {model_name}")
        sys.exit(1)
    if model_name.startswith("litellm-generic-"):
        real_model_name = model_name.removeprefix("litellm-generic-")
        prompt_tokens = 5
        completion_tokens = 10
        prompt_tokens_cost_usd_dollar, completion_tokens_cost_usd_dollar = (
            cost_per_token(
                model=real_model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )
        # litellm.set_verbose = True
        SELECTED_MODEL = LiteLLMGeneric(
            real_model_name,
            prompt_tokens_cost_usd_dollar,
            completion_tokens_cost_usd_dollar,
        )
    else:
        SELECTED_MODEL = MODEL_HUB[model_name]
    SELECTED_MODEL.setup()


# the model temperature to use
# For OpenAI models: this value should be from 0 to 2
MODEL_TEMP: float = 0.0
