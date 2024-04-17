"""
Interfacing with Claude models using the Anthropic API.
"""
import json
import os
import sys
from typing import List, Tuple, Any
from dotenv import load_dotenv
import anthropic
from anthropic import APIError
from tenacity import retry, stop_after_attempt, wait_random_exponential
from app import globals
from app.data_structures import FunctionCallIntent
from app.log import log_and_cprint, log_and_print

"""
NOTE:

Mostly untested and experimental addition.
"""


load_dotenv()

anthropic_key = os.getenv("ANTHROPIC_KEY")
if not anthropic_key:
    print("Please set the ANTHROPIC_KEY env var")
    sys.exit(1)

client = anthropic.Anthropic(api_key=anthropic_key)

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

def extract_gpt_content(response) -> str:
    content = response.content
    if content is None:
        return ""
    else:
        return content

def extract_gpt_func_calls(response) -> List[FunctionCallIntent]:
    result = []
    tool_calls = response.tool_calls
    if tool_calls is None:
        return result
    
    for call in tool_calls:
        func_name = call.name
        func_args_str = call.arguments
        
        if func_args_str == "":
            args_dict = {}
        else:
            try:
                args_dict = json.loads(func_args_str, strict=False)
            except json.decoder.JSONDecodeError:
                args_dict = {}
        
        func_call_intent = FunctionCallIntent(func_name, args_dict, call)
        result.append(func_call_intent)
    
    return result

@retry(wait=wait_random_exponential(min=30, max=600), stop=stop_after_attempt(3))
def call_claude(
    logger,
    messages,
    tools=None,
    **model_args,
) -> Tuple[str, Any, List[FunctionCallIntent], float, int, int]:
    try:
        response = client.beta.tools.messages.create(
            model="claude-3-opus-20240229",
            messages=messages,
            tools=tools,
            max_tokens=1024,
            **model_args,
        )
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = calc_cost(logger, response.model, input_tokens, output_tokens)
        
        log_and_print(logger, f"Raw model response: {response}")
        
        content = extract_gpt_content(response)
        raw_tool_calls = response.tool_calls
        func_call_intents = extract_gpt_func_calls(response)

        return content, raw_tool_calls, func_call_intents, cost, input_tokens, output_tokens
        
    except APIError as e:
        log_and_print(logger, f"Anthropic API Error: {e}")
        raise e
