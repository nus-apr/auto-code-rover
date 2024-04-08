"""
A proxy agent. Process raw response into json format.
"""

import inspect
from logging import Logger
from typing import Any

from app.data_structures import MessageThread
from app.log import log_and_print
from app.model.gpt import call_gpt
from app.post_process import ExtractStatus, is_valid_json
from app.search.search_manage import SearchManager
from app.utils import parse_function_invocation

PROXY_PROMPT = """
You are a helpful assistant that retreive API calls and bug locations from a text into json format.
The text will consist of two parts:
1. do we need more context?
2. where are bug locations?
Extract API calls from question 1 (leave empty if not exist) and bug locations from question 2 (leave empty if not exist).

The API calls include:
search_method_in_class(method_name: str, class_name: str)
search_method_in_file(method_name: str, file_path: str)
search_method(method_name: str)
search_class_in_file(self, class_name, file_name: str)
search_class(class_name: str)
search_code_in_file(code_str: str, file_path: str)
search_code(code_str: str)

Provide your answer in JSON structure like this, you should ignore the argument placeholders in api calls.
For example, search_code(code_str="str") should be search_code("str")
search_method_in_file("method_name", "path.to.file") should be search_method_in_file("method_name", "path/to/file")

{
    "API_calls": ["api_call_1(args)", "api_call_2(args)", ...],
    "bug_locations":[{"file": "path/to/file", "class": "class_name", "method": "method_name"}, {"file": "path/to/file", "class": "class_name", "method": "method_name"} ... ]
}

NOTE: a bug location should at least has a "class" or "method".
"""


def run_with_retries(
    logger,
    text: str,
    retries=5,
) -> tuple[str | None, list[MessageThread], float, int, int]:
    all_cost = 0.0
    all_input_tokens = 0
    all_output_tokens = 0

    msg_threads = []
    for idx in range(1, retries + 1):
        log_and_print(
            logger, f"Trying to select search APIs in json. Try {idx} of {retries}."
        )

        res_text, new_thread, cost, input_tokens, output_tokens = run(
            logger,
            text,
        )
        msg_threads.append(new_thread)

        all_cost += cost
        all_input_tokens += input_tokens
        all_output_tokens += output_tokens

        extract_status, data = is_valid_json(res_text)

        if extract_status != ExtractStatus.IS_VALID_JSON:
            log_and_print(logger, "Invalid json. Will retry.")
            continue

        valid, diagnosis = is_valid_response(data)
        if not valid:
            log_and_print(logger, f"{diagnosis}. Will retry.")
            continue

        log_and_print(logger, "Extracted a valid json. Congratulations!")
        return res_text, msg_threads, all_cost, all_input_tokens, all_output_tokens
    return None, msg_threads, all_cost, all_input_tokens, all_output_tokens


def run(
    logger,
    text: str,
) -> tuple[str, MessageThread, float, int, int]:
    """
    Run the agent to extract issue to json format.
    """

    msg_thread = MessageThread()
    msg_thread.add_system(PROXY_PROMPT)
    msg_thread.add_user(text)
    res_text, _, _, cost, input_tokens, output_tokens = call_gpt(
        logger, msg_thread.to_msg(), response_format="json_object"
    )

    msg_thread.add_model(res_text, [])  # no tools

    return res_text, msg_thread, cost, input_tokens, output_tokens


def is_valid_response(data: Any, logger: Logger | None = None) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Json is not a dict"

    if not data.get("API_calls"):
        bug_locations = data.get("bug_locations")
        if not isinstance(bug_locations, list) or not bug_locations:
            return False, "Both API_calls and bug_locations are empty"

        for loc in bug_locations:
            if loc.get("class") or loc.get("method"):
                continue
            return False, "Bug location not detailed enough"
    else:
        for api_call in data["API_calls"]:
            if not isinstance(api_call, str):
                return False, "Every API call must be a string"

            try:
                func_name, func_args = parse_function_invocation(api_call, logger)
            except Exception:
                return False, "Every API call must be of form api_call(arg1, ..., argn)"

            function = getattr(SearchManager, func_name, None)
            if function is None:
                return False, f"the API call '{api_call}' calls a non-existent function"

            arg_spec = inspect.getfullargspec(function)
            arg_names = arg_spec.args[1:]  # first parameter is self

            if len(func_args) != len(arg_names):
                return False, f"the API call '{api_call}' has wrong number of arguments"

    return True, "OK"
