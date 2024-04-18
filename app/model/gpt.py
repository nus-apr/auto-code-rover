"""
Interfacing with GPT models.
"""

import json
import os
import sys
from typing import Literal, cast

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import (
    Function as OpenaiFunction,
)
from openai.types.chat.chat_completion_tool_choice_option_param import (
    ChatCompletionToolChoiceOptionParam,
)
from openai.types.chat.completion_create_params import ResponseFormat
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app import globals
from app.data_structures import FunctionCallIntent
from app.log import log_and_cprint, log_and_print

load_dotenv()

openai_key = os.getenv("OPENAI_KEY")
if not openai_key:
    print("Please set the OPENAI_KEY env var")
    sys.exit(1)

client = OpenAI(api_key=openai_key)


def calc_cost(logger, model_name, input_tokens, output_tokens) -> float:
    """
    Calculates the cost of a response from the openai API.

    Args:
        response (openai.ChatCompletion): The response from the API.

    Returns:
        float: The cost of the response.
    """
    cost = (
        globals.MODEL_COST_PER_INPUT[model_name] * input_tokens
        + globals.MODEL_COST_PER_OUTPUT[model_name] * output_tokens
    )
    log_and_cprint(
        logger,
        f"Model API request cost info: "
        f"input_tokens={input_tokens}, output_tokens={output_tokens}, cost={cost:.6f}",
        "yellow",
    )
    return cost


def extract_gpt_content(chat_completion_message: ChatCompletionMessage) -> str:
    """
    Given a chat completion message, extract the content from it.
    """
    content = chat_completion_message.content
    if content is None:
        return ""
    else:
        return content


def extract_gpt_func_calls(
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


@retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
def call_gpt(
    logger,
    messages,
    top_p=1,
    tools=None,
    response_format: Literal["text", "json_object"] = "text",
    **model_args,
) -> tuple[
    str, list[ChatCompletionMessageToolCall], list[FunctionCallIntent], float, int, int
]:
    """
    Calls the openai API to generate completions for the given inputs.
    Assumption: we only retrieve one choice from the API response.

    Args:
        messages (List): A list of messages.
                         Each item is a dict (e.g. {"role": "user", "content": "Hello, world!"})
        top_p (float): The top_p to use. We usually do not vary this, so not setting it as a cmd-line argument. (from 0 to 1)
        tools (List, optional): A list of tools.
        **model_args (dict): A dictionary of model arguments.

    Returns:
        Raw response and parsed components.
        The raw response is to be sent back as part of the message history.
    """
    try:
        if tools is not None and len(tools) == 1:
            # there is only one tool => force the model to use it
            tool_name = tools[0]["function"]["name"]
            tool_choice = {"type": "function", "function": {"name": tool_name}}
            response = client.chat.completions.create(
                model=globals.model,
                messages=messages,
                tools=tools,  # TODO: see what happens if this is []
                tool_choice=cast(ChatCompletionToolChoiceOptionParam, tool_choice),
                temperature=globals.model_temperature,
                response_format=ResponseFormat(type=response_format),
                max_tokens=1024,
                top_p=top_p,
                **model_args,
            )
        else:
            response = client.chat.completions.create(
                model=globals.model,
                messages=messages,
                # FIXME: how to get rid of type check warning?
                tools=tools,  # FIXME: see what happens if this is []
                temperature=globals.model_temperature,
                response_format=ResponseFormat(type=response_format),
                max_tokens=1024,
                top_p=top_p,
                **model_args,
            )

        input_tokens = int(response.usage.prompt_tokens)
        output_tokens = int(response.usage.completion_tokens)
        cost = calc_cost(logger, response.model, input_tokens, output_tokens)

        raw_response = response.choices[0].message
        log_and_print(logger, f"Raw model response: {raw_response}")
        content = extract_gpt_content(raw_response)
        raw_tool_calls = raw_response.tool_calls
        func_call_intents = extract_gpt_func_calls(raw_response)
        return (
            content,
            raw_tool_calls,
            func_call_intents,
            cost,
            input_tokens,
            output_tokens,
        )
    except BadRequestError as e:
        if e.code == "context_length_exceeded":
            log_and_print(logger, "Context length exceeded")
        raise e
