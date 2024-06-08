"""
For models other than those from OpenAI, use LiteLLM if possible.
Create all models managed by Ollama here, since they need to talk to ollama server.
"""

import sys
from collections.abc import Mapping
from copy import deepcopy
from typing import Literal, cast

import httpx
import ollama
import timeout_decorator
from ollama._types import Message, Options
from openai.types.chat import ChatCompletionMessage

from app.model import common
from app.model.common import Model


class OllamaModel(Model):
    """
    Base class for creating Singleton instances of Ollama models.
    """

    _instances = {}

    def __new__(cls):
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
            cls._instances[cls]._initialized = False
        return cls._instances[cls]

    def __init__(self, name: str):
        if self._initialized:
            return
        # local models are free
        super().__init__(name, 0.0, 0.0)
        self.client: ollama.Client | None = None
        self._initialized = True

    def setup(self) -> None:
        """
        Check API key.
        """
        self.check_api_key()
        try:
            self.send_empty_request()
            print(f"Model {self.name} is up and running.")
        except timeout_decorator.TimeoutError as e:
            print(
                "Ollama server is taking too long (more than 2 mins) to respond. Please check whether it's running.",
                e,
            )
            sys.exit(1)
        except Exception as e:
            print("Could not communicate with ollama server due to exception.", e)
            sys.exit(1)

    @timeout_decorator.timeout(120)  # 2 min
    def send_empty_request(self):
        """
        Send an empty request to the model, for two purposes
        (1) check whether the model is up and running
        (2) preload the model for faster response time (models will be kept in memory for 5 mins after loaded)
        (see https://github.com/ollama/ollama/blob/main/docs/faq.md#how-can-i-pre-load-a-model-to-get-faster-response-times)
        """
        # localhost is used when (1) running both ACR and ollama on host machine; and
        #   (2) running ollama in host, and ACR in container with --net=host
        local_client = ollama.Client(host="http://localhost:11434")
        # docker_host_client is used when running ollama in host and ACR in container, and
        # Docker Desktop is installed
        docker_host_client = ollama.Client(host="http://host.docker.internal:11434")
        try:
            local_client.chat(model=self.name, messages=[])
            self.client = local_client
            return
        except httpx.ConnectError:
            # failed to connect to client at localhost
            pass

        try:
            docker_host_client.chat(model=self.name, messages=[])
            self.client = docker_host_client
        except httpx.ConnectError:
            # also failed to connect via host.docker.internal
            print("Could not connect to ollama server.")
            sys.exit(1)

    def check_api_key(self) -> str:
        return "No key required for local models."

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

    def call(
        self,
        messages: list[dict],
        top_p=1,
        tools=None,
        response_format: Literal["text", "json_object"] = "text",
        **kwargs,
    ):
        stop_words = ["assistant", "\n\n \n\n"]
        json_stop_words = deepcopy(stop_words)
        json_stop_words.append("```")
        json_stop_words.append(" " * 10)
        # FIXME: ignore tools field since we don't use tools now

        assert self.client is not None
        try:
            # build up options for ollama
            options = {"temperature": common.MODEL_TEMP, "top_p": top_p}
            if response_format == "json_object":
                # additional instructions for json mode
                json_instruction = {
                    "role": "user",
                    "content": "Stop your response after a valid json is generated.",
                }
                messages.append(json_instruction)
                # give more stop words and lower max_token for json mode
                options.update({"stop": json_stop_words, "num_predict": 128})
                response = self.client.chat(
                    model=self.name,
                    messages=cast(list[Message], messages),
                    format="json",
                    options=cast(Options, options),
                    stream=False,
                )
            else:
                options.update({"stop": stop_words, "num_predict": 1024})
                response = self.client.chat(
                    model=self.name,
                    messages=cast(list[Message], messages),
                    options=cast(Options, options),
                    stream=False,
                )

            assert isinstance(response, Mapping)
            resp_msg = response.get("message", None)
            if resp_msg is None:
                return "", 0, 0, 0

            content: str = resp_msg.get("content", "")
            return content, 0, 0, 0

        except Exception as e:
            # FIXME: catch appropriate exception from ollama
            raise e


class Llama3_8B(OllamaModel):
    def __init__(self):
        super().__init__("llama3")
        self.note = "Llama3 8B model."


class Llama3_70B(OllamaModel):
    def __init__(self):
        super().__init__("llama3:70b")
        self.note = "Llama3 70B model."
