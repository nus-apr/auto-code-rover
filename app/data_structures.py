import json
from collections.abc import Mapping
from dataclasses import dataclass
from pprint import pformat

from openai.types.chat import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import (
    Function as OpenaiFunction,
)


@dataclass
class MethodId:
    class_name: str
    method_name: str

    def __str__(self):
        if self.class_name:
            return f"{self.class_name}.{self.method_name}"
        return self.method_name

    def __hash__(self):
        return hash((self.class_name, self.method_name))


class FunctionCallIntent:
    """An intent to call a tool function.

    This object created from OpenAI API response.
    """

    def __init__(
        self,
        func_name: str,
        arguments: Mapping[str, str],
        openai_func: OpenaiFunction | None,
    ):
        self.func_name = func_name
        self.arg_values = dict()
        self.arg_values.update(arguments)
        # record the original openai function object,
        # which is used when we want tell the model that it has
        # previously called this function/tool
        self.openai_func = openai_func or OpenaiFunction(
            arguments=json.dumps(arguments), name=func_name
        )

    def __str__(self):
        return f"Call function `{self.func_name}` with arguments {self.arg_values}."

    def to_dict(self):
        return {"func_name": self.func_name, "arguments": self.arg_values}

    def to_dict_with_result(self, call_ok: bool):
        return {
            "func_name": self.func_name,
            "arguments": self.arg_values,
            "call_ok": call_ok,
        }


class MessageThread:
    """
    Represents a thread of conversation with the model.
    Abstrated into a class so that we can dump this to a file at any point.
    """

    def __init__(self, messages=None):
        self.messages: list[dict] = messages or []

    def add(self, role: str, message: str):
        """
        Add a new message to the thread.
        Args:
            message (str): The content of the new message.
            role (str): The role of the new message.
        """
        self.messages.append({"role": role, "content": message})

    def add_system(self, message: str):
        self.messages.append({"role": "system", "content": message})

    def add_user(self, message: str):
        self.messages.append({"role": "user", "content": message})

    def add_tool(self, message: str, tool_call_id: str):
        m = {"role": "tool", "content": message, "tool_call_id": tool_call_id}
        self.messages.append(m)

    def add_model(
        self, message: str | None, tools: list[ChatCompletionMessageToolCall]
    ):
        # let's serialize tools into json first
        json_tools = []
        for tool in tools:
            this_tool_dict = {}
            this_tool_dict["id"] = tool.id
            this_tool_dict["type"] = tool.type
            # now serialize function as well
            func_obj: OpenaiFunction = tool.function
            func_args: str = func_obj.arguments
            func_name: str = func_obj.name
            this_tool_dict["function"] = {"name": func_name, "arguments": func_args}
            json_tools.append(this_tool_dict)

        if json_tools == []:
            # there is no tool calls from the model last time,
            # the best we could do is to return the generated text
            self.messages.append({"role": "assistant", "content": message})
        else:
            self.messages.append(
                {"role": "assistant", "content": None, "tool_calls": json_tools}
            )

    def to_msg(self) -> list[dict]:
        """
        Convert to the format to be consumed by the model.
        Returns:
            List[Dict]: The message thread.
        """
        return self.messages

    def __str__(self):
        return pformat(self.messages, width=160, sort_dicts=False)

    def save_to_file(self, file_path: str):
        """
        Save the current state of the message thread to a file.
        Args:
            file_path (str): The path to the file.
        """
        with open(file_path, "w") as f:
            json.dump(self.messages, f, indent=4)

    def get_round_number(self) -> int:
        """
        From the current message history, decide how many rounds have been completed.
        """
        completed_rounds = 0
        for message in self.messages:
            if message["role"] == "assistant":
                completed_rounds += 1
        return completed_rounds

    @classmethod
    def load_from_file(cls, file_path: str):
        """
        Load the message thread from a file.
        Args:
            file_path (str): The path to the file.
        Returns:
            MessageThread: The message thread.
        """
        with open(file_path) as f:
            messages = json.load(f)
        return cls(messages)
