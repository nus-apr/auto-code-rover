import sys
import threading
from abc import ABC, abstractmethod

from app.log import log_and_cprint

# Variables for each process. Since models are singleton objects, their references are copied
# to each process, but they all point to the same objects. For safe updating costs per process,
# we define the accumulators here.

thread_cost = threading.local()
thread_cost.process_cost = 0.0
thread_cost.process_input_tokens = 0
thread_cost.process_output_tokens = 0


class ClaudeContentPolicyViolation(RuntimeError):
    pass


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
            f"Model ({self.name}) API request cost info: "
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
    if model_name not in MODEL_HUB:
        print(f"Invalid model name: {model_name}")
        sys.exit(1)
    SELECTED_MODEL = MODEL_HUB[model_name]
    SELECTED_MODEL.setup()


# the model temperature to use
# For OpenAI models: this value should be from 0 to 2
MODEL_TEMP: float = 0.0
