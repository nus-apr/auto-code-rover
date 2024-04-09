"""
Interfacing with Claude models.
"""

# Experimental implementation

import json
import os
import sys
from typing import List, Tuple
from typing import Literal

from dotenv import load_dotenv
from anthropic import APIError, Anthropic
from anthropic.types.messages import Message, MessageToolCall
from anthropic.types.messages.message_tool_call import Function as AnthropicFunction
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app import globals
from app.data_structures import FunctionCallIntent
from app.log import log_and_cprint, log_and_print

load_dotenv()

CLAUDE_3_VERSION = "Claude-3-Opus"


anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_key:
    print("Please set the ANTHROPIC_API_KEY env var")
    sys.exit(1)

client = Anthropic(api_key=anthropic_key)

# Anthropic API pricing
COST_PER_INPUT_TOKEN = 15 / 1_000_000  # 15 USD per million input tokens
COST_PER_OUTPUT_TOKEN = 75 / 1_000_000  # 75 USD per million output tokens


def calc_cost(logger, model_name, input_tokens, output_tokens) -> float:
    cost = (
        COST_PER_INPUT_TOKEN * input_tokens
        + COST_PER_OUTPUT_TOKEN * output_tokens
    )
    log_and_cprint(
        logger,
        f"Model API request cost info: "
        f"input_tokens={input_tokens}, output_tokens={output_tokens}, cost={cost:.6f}",
        "yellow",
    )
    return cost


def extract_claude_content(message: Message) -> str:
    content = message.content
    if content is None:
        return ""
    else:
        return content


def extract_claude_func_calls(message: Message) -> List[FunctionCallIntent]:
    result = []
    tool_calls = message.tool_calls
    if tool_calls is None:
        return result

    call: MessageToolCall
    for call in tool_calls:
        called_func: AnthropicFunction = call.function
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
def call_claude(
    logger,
    messages,
    tools=None,
    response_format: Literal["text", "json_object"] = "text",
    **model_args,
) -> Tuple[str, list[MessageToolCall], List[FunctionCallIntent], float, int, int]:

    try:
        response = client.messages.create(
            model=CLAUDE_VERSION,
            messages=messages,
            tools=tools,
            temperature=globals.model_temperature,
            response_format=response_format,
            max_tokens=1024,
            **model_args,
        )

        input_tokens = int(response.usage.input_tokens)
        output_tokens = int(response.usage.output_tokens)
        cost = calc_cost(logger, response.model, input_tokens, output_tokens)

        raw_response = response.choices[0].message
        log_and_print(logger, f"Raw model response: {raw_response}")
        content = extract_claude_content(raw_response)
        raw_tool_calls = raw_response.tool_calls
        func_call_intents = extract_claude_func_calls(raw_response)
        return (
            content,
            raw_tool_calls,
            func_call_intents,
            cost,
            input_tokens,
            output_tokens,
        )
    except APIError as e:
        if e.code == "context_length_exceeded":
            log_and_print(logger, "Context length exceeded")
        raise e

