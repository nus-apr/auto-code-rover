"""
An agent, which is only responsible for the write_patch tool call.
"""

import json
from copy import deepcopy
from os.path import join as pjoin

from app import globals
from app.analysis.sbfl import MethodId
from app.api import agent_common, validation
from app.data_structures import MessageThread
from app.log import log_and_print
from app.model.gpt import call_gpt
from app.post_process import (
    ExtractStatus,
    extract_diff_one_instance,
    record_extract_status,
)

SYSTEM_PROMPT = """You are a software developer maintaining a large project.
You are working on an issue submitted to your project.
The issue contains a description marked between <issue> and </issue>.
You ultimate goal is to write a patch that resolves this issue.
"""


USER_PROMPT_INIT = """Write a patch for the issue, based on the retrieved context. You can import necessary libraries.
Return the patch in the format below. Within <file></file>, replace "..." with actual file path. Within <original></original>, replace "..." with the original code snippet from the program. Within <patched></patched>, replace "..." with the fixed version of the original code. When adding orignal code and updated code, pay attention to indentation, as the code is in Python.
You can write multiple modifications if needed.

# modification 1
```python
<file>...</file>
<original>...</original>
<patched>...</patched>
```

# modification 2
```python
<file>...</file>
<original>...</original>
<patched>...</patched>
```

# modification 3
...
"""


def run_with_retries(
    logger,
    message_thread: MessageThread,
    output_dir: str,
    project_path,
    test_cmd,
    repo_name,
    env_name,
    task_id: str,
    testcases_passing,
    testcases_failing,
    retries=3,
) -> tuple[str, float, int, int]:
    """
    Since the agent may not always write an applicable patch, we allow for retries.
    This is a wrapper around the actual run.
    """
    # (1) replace system prompt
    messages = deepcopy(message_thread.messages)
    new_thread: MessageThread = MessageThread(messages=messages)
    new_thread = agent_common.replace_system_prompt(new_thread, SYSTEM_PROMPT)

    # (2) add the initial user prompt
    new_thread.add_user(USER_PROMPT_INIT)

    can_stop = False
    result_msg = ""

    all_cost = 0.0
    all_input_tokens = 0
    all_output_tokens = 0

    for i in range(1, retries + 2):
        if i > 1:
            debug_file = pjoin(output_dir, f"debug_agent_write_patch_{i - 1}.json")
            with open(debug_file, "w") as f:
                json.dump(new_thread.to_msg(), f, indent=4)

        if can_stop or i > retries:
            break

        log_and_print(logger, f"Trying to write a patch. Try {i} of {retries}.")

        raw_patch_file = pjoin(output_dir, f"agent_patch_raw_{i}")

        # actually calling gpt
        res_text, _, _, cost, input_tokens, output_tokens = call_gpt(
            logger, new_thread.to_msg()
        )

        all_cost += cost
        all_input_tokens += input_tokens
        all_output_tokens += output_tokens

        new_thread.add_model(res_text, [])  # no tools

        log_and_print(
            logger, f"Raw patch produced in try {i}. Writing patch into file."
        )

        with open(raw_patch_file, "w") as f:
            f.write(res_text)

        # Attemp to extract a real patch from the raw patch
        diff_file = pjoin(output_dir, f"extracted_patch_{i}.diff")
        extract_status, extract_msg = extract_diff_one_instance(
            raw_patch_file, diff_file
        )

        # record the extract status. This is for classifying the task at the end of workflow
        record_extract_status(output_dir, extract_status)

        if extract_status == ExtractStatus.APPLICABLE_PATCH:
            # patch generated is applicable and all edits are ok, so we can think about validation
            if globals.enable_validation:
                # if we have a patch extracted, apply it and validate
                run_test_suite_log_file = pjoin(output_dir, f"run_test_suite_{i}.log")
                patch_is_correct, err_message = validation.validate(
                    diff_file,
                    repo_name,
                    output_dir,
                    project_path,
                    test_cmd,
                    env_name,
                    testcases_passing,
                    testcases_failing,
                    run_test_suite_log_file,
                    logger,
                )
                if patch_is_correct:
                    result_msg = (
                        "Written a patch that resolves the issue. Congratulations!"
                    )
                    new_thread.add_user(result_msg)  # just for logging
                    can_stop = True
                # the following two branches cannot be swapped, because
                # --enable-perfect-angelic is meant to override --enable-angelic
                elif globals.enable_perfect_angelic:
                    msg = (
                        f"Written an applicable patch, but it did not resolve the issue. Error message: {err_message}.",
                    )

                    incorrect_locations = validation.perfect_angelic_debug(
                        task_id, diff_file, project_path
                    )
                    angelic_msg = angelic_debugging_message(incorrect_locations)

                    result_msg = f"{msg}\n{angelic_msg}"
                    new_thread.add_user(result_msg)
                    continue
                elif globals.enable_angelic:
                    raise NotImplementedError(
                        "Angelic debugging has not been integrated"
                    )
                else:
                    result_msg = f"Written an applicable patch, but it did not resolve the issue. {err_message} "
                    result_msg += " Please try again."
                    new_thread.add_user(result_msg)
                    continue
            elif globals.enable_perfect_angelic:
                incorrect_locations = validation.perfect_angelic_debug(
                    task_id, diff_file, project_path
                )

                msg = "Extracted a patch."
                if angelic_msg := angelic_debugging_message(incorrect_locations):
                    result_msg = f"{msg}\n{angelic_msg}"
                else:
                    result_msg = msg

                new_thread.add_user(result_msg)
                continue
            elif globals.enable_angelic:
                raise NotImplementedError("Angelic debugging has not been integrated")
            else:
                result_msg = "Extracted a patch. Since validation is disabled, you should validation the patch later on. Ending the workflow."
                new_thread.add_user(result_msg)  # just for logging
                can_stop = True

        else:
            # we dont have a valid patch
            new_prompt = (
                "Your edit could not be applied to the program. "
                + extract_msg
                + " Please try again."
            )
            new_thread.add_user(new_prompt)
            result_msg = "Failed to write a valid patch."

    return result_msg, all_cost, all_input_tokens, all_output_tokens


def angelic_debugging_message(incorrect_locations: list[tuple[str, MethodId]]) -> str:
    msg = []

    if incorrect_locations:
        msg.append("The following methods should not have been changed:")
        msg.extend(
            f"    {filename}: {method_id!s}"
            for filename, method_id in incorrect_locations
        )

    return "\n".join(msg)
