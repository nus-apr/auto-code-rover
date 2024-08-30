import inspect
import json
import re
from collections.abc import Callable
from os.path import join as pjoin
from pathlib import Path

from loguru import logger
from termcolor import colored

from app import globals
from app.api.manage import ProjectApiManager
from app.data_structures import FunctionCallIntent, MessageThread
from app.log import (
    log_and_cprint,
    log_and_print,
    print_acr,
    print_banner,
    print_issue,
    print_retrieval,
)
from app.model import common, ollama
from app.search.search_manage import SearchManager
from app.utils import parse_function_invocation

# FIXME: the system prompt should be different for stratified/state machine.
SYSTEM_PROMPT = """You are a software developer maintaining a large project.
You are examining an issue submitted to your project and its test patch and fix patch.
The issue contains a description marked between <issue> and </issue>.
The test patch is some newly created unit test functions that check against the broken code. It will be wrapped between <test_patch> and </test_patch>.
Your task is to invoke a few search API calls on top of the test patch to gather the trace that reproduce the problem. 
Once you have a clear understanding on what is going on, you will be provided with the fix patch and explain why the patch resolve the problem.
"""

def prepare_contrast_prompt(fix_patch: str) -> str:
    """
    once the context collection is finished, provide fix_patch to the model and ask it to explain what is going on.
    """
    # Do we need special format for the explanation ?
    contrast_prompt = f"""Given the context collection is finished, let's analyse how the ground truth fix patch modified the codebase.
    Note that the fix patch passed the test patch so you can ensure that the correctness of the fix patch is guaranteed.
    
    <fix_patch>
    {fix_patch}
    </fix_patch>
    
    Please answer the following questions in your analysis:
    Fix Location: [Analyse the location of the modification within the whole reproduction code chain here. Explain the functionalities of the code components modified within the whole execution.] 
    Behavior Contrast: [Contrast the code behavior before and after the fix patch and analyse why it fixes the issue]
    Conclusion: [Briefly summarize the rationale behind the fix patch here]
    """
    return contrast_prompt

def prepare_issue_prompt(problem_stmt: str, test_patch: str) -> str:
    """
    Given the raw problem statement, sanitize it and prepare the issue prompt.
    Args:
        problem_stmt (str): The raw problem statement.
            Assumption: the problem statement is the content of a markdown file.
    Returns:
        str: The issue prompt.
    """
    # remove markdown comments
    problem_wo_comments = re.sub(r"<!--.*?-->", "", problem_stmt, flags=re.DOTALL)
    content_lines = problem_wo_comments.split("\n")
    # remove spaces and empty lines
    content_lines = [x.strip() for x in content_lines]
    content_lines = [x for x in content_lines if x != ""]
    problem_stripped = "\n".join(content_lines)
    # add tags
    result = "<issue>\n" + problem_stripped + "\n</issue>" + "\n\n<test_patch>\n" + test_patch + "\n</test_patch>"
    return result


def add_step_trigger(orig_prompt: str, is_first: bool = False) -> str:
    """
    Given the original prompt, add the trigger question for the next step.
    Args:
        orig_prompt (str): The original prompt.
        is_first (bool): Whether the trigger is for the first step.
    Returns:
        str: The prompt with trigger question.
    """
    if is_first:
        trigger = "What is the first step?"
    else:
        trigger = "What's the next step to complete the task? Be reminded that you are solving the initial issue."
    return orig_prompt + "\n" + trigger


def start_conversation_round_stratified(
    output_dir: str,
    msg_thread: MessageThread,
    api_manager: ProjectApiManager,
    fix_patch: str,
    repo_name: str,
    start_round_no: int = 0,
    print_callback: Callable[[dict], None] | None = None,
) -> bool:
    """
    This version uses json data to process API calls, instead of using the OpenAI function calling.
    Advantage is that multiple API calls can be made in a single round.
    """
    # ZZ: TODO: Be clear that the search is limited on the current working issue only 
    # ZZ: TODO: should introduce repo name here, check if the repo name need normalization or not here .. 
    prompt = (
        "Based on the test patch from the issue related to the bug, you can use the following search APIs to collect context about the related code components that cause the error in the issue."
        "However, note that the search scope is limited to the issue codebase. Do not use the search tools for codebases imported or outside the issue codebase."
        f"Do not use local file_path the user described in the issue description for search, use the path that start from the issue codebase {repo_name} instead."
        "\n- search_class(class_name: str): Search for a class in the codebase"
        "\n- search_method_in_file(method_name: str, file_path: str): Search for a method in a given file"
        "\n- search_method_in_class(method_name: str, class_name: str): Search for a method in a given class"
        "\n- search_method(method_name: str): Search for a method in the entire codebase"
        "\n- search_code(code_str: str): Search for a code snippet in the entire codebase"
        "\n- search_code_in_file(code_str: str, file_path: str): Search for a code snippet in a given file file"
        "\n\nNote that you can use multiple search APIs in one round."
        "\n\nNow analyze the test patch and select necessary APIs to construct the trace that reproduce the problem. Each API call must have concrete arguments as inputs. You do not need to search for all contexts in one shot."
    )
    msg_thread.add_user(prompt)

    round_no = start_round_no

    round_count = range(start_round_no, globals.conv_round_limit + 1)

    try_generate_locs = False
    if globals.disable_patch_generation:
        round_count = range(
            start_round_no, start_round_no + globals.context_generation_limit + 1
        )

    for round_no in round_count:
        api_manager.start_new_tool_call_layer()

        conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
        # save current state before starting a new round
        msg_thread.save_to_file(conversation_file)

        print_banner(f"CONTEXT RETRIEVAL ROUND {round_no}")

        print_acr(
            prompt,
            f"context retrieval round {start_round_no}",
            print_callback=print_callback,
        )

        res_text, *_ = common.SELECTED_MODEL.call(msg_thread.to_msg())
        msg_thread.add_model(res_text, tools=[])
        print_retrieval(res_text, f"round {round_no}", print_callback=print_callback)
        if res_text.strip() == "Context collection finished.":
            context_collection_finished = True
            selected_apis = """{"API_calls": [], "finished": "true"}"""
        else:
            context_collection_finished = False
            selected_apis, _, proxy_threads = api_manager.proxy_apis(res_text)
            proxy_log = Path(output_dir, f"agent_proxy_{round_no}.json")
            proxy_messages = [thread.to_msg() for thread in proxy_threads]
            proxy_log.write_text(json.dumps(proxy_messages, indent=4))

        if selected_apis is None and not context_collection_finished:
            # ZZ: TODO add error message ?
            msg = "The search API calls seem not valid. Please check the arguments you give carefully and try again."
            msg_thread.add_user(msg)
            print_acr(
                msg,
                f"context retrieval round {round_no}",
                print_callback=print_callback,
            )
            continue

        selected_apis_json = json.loads(selected_apis)

        json_api_calls = selected_apis_json.get("API_calls", [])
        formatted = []
        if json_api_calls:
            formatted.append("API calls:")
            for call in json_api_calls:
                formatted.extend([f"\n- `{call}`"])
            print_acr(
                "\n".join(formatted),
                "Agent-selected API calls",
                print_callback=print_callback,
            )

        # collected enough information to write patch
        if context_collection_finished and (not json_api_calls):
            # ZZ: TODO add fix patch contrast logic here
            # construct prompt => call => parse
            contrast_prompt = prepare_contrast_prompt(fix_patch)
            msg_thread.add_user(contrast_prompt)
            print_acr(
                contrast_prompt, f"Fix Patch Contrast", print_callback=print_callback
            )
            res_text, *_ = common.SELECTED_MODEL.call(msg_thread.to_msg())
            msg_thread.add_model(res_text, tools=[])
            print_retrieval(res_text, f"Fix Patch Contrast Response", print_callback=print_callback)
            break

        # prepare response from tools
        collated_tool_response = ""

        for api_call in json_api_calls:
            func_name, func_args = parse_function_invocation(api_call)

            arg_spec = inspect.getfullargspec(getattr(SearchManager, func_name))
            arg_names = arg_spec.args[1:]  # first parameter is self

            assert len(func_args) == len(
                arg_names
            ), f"Number of argument is wrong in API call: {api_call}"

            kwargs = dict(zip(arg_names, func_args))
            intent = FunctionCallIntent(func_name, kwargs, None)
            tool_output, _, _ = api_manager.dispatch_intent(intent, msg_thread)

            collated_tool_response += f"Result of {api_call}:\n\n"
            collated_tool_response += tool_output + "\n\n"

        msg_thread.add_user(collated_tool_response)
        print_acr(
            collated_tool_response,
            f"context retrieval round {round_no}",
            print_callback=print_callback,
        )

        msg = "Let's summarize the collected trace of context first"
        msg_thread.add_user(msg)
        print_acr(
            msg, f"context retrieval round {round_no}", print_callback=print_callback
        )

        res_text, *_ = common.SELECTED_MODEL.call(msg_thread.to_msg())
        msg_thread.add_model(res_text, tools=[])
        print_retrieval(res_text, f"round {round_no}", print_callback=print_callback)

        if round_no < globals.conv_round_limit:
            msg = (
                "Based on your analysis, answer below questions:"
                "\n- do we need more context: construct search API calls to get the rest context of the project from the test patch."
                "\n If we have gathered all context of the components that relates to the bug, simply respond `Context collection finished.` only."
            )
            if isinstance(common.SELECTED_MODEL, ollama.OllamaModel):
                # llama models tend to always output search APIs and buggy locations.
                msg += "\n\nNOTE: If you have already identified the bug locations, do not make any search API calls."
            msg_thread.add_user(msg)
            print_acr(
                msg,
                f"context retrieval round {round_no}",
                print_callback=print_callback,
            )
    else:
        log_msg = "Try writing patch anyway."
        # TODO can be improved more
        if globals.disable_patch_generation:
            all_locs = []
            for fix_location_file in Path(output_dir).glob("*fix_locations_*.json"):
                all_locs += json.loads(Path(fix_location_file).read_text())
            all_locs = list(set(map(json.dumps, all_locs)))
            Path(output_dir, "fix_locations.json").write_text(
                json.dumps(all_locs, indent=4)
            )
            try_generate_locs = all_locs != []
            log_msg = "Try outputing some locations still."

        logger.info(f"Too many rounds. {log_msg}")


    logger.info("Ending workflow.")
    conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
    msg_thread.save_to_file(conversation_file)

    return True


def search_for_bug_location(
    api_manager: ProjectApiManager,
    msg_thread: MessageThread,
    bug_location: dict[str, str],
) -> tuple[str, str, bool]:
    found = False

    file_name = bug_location.get("file")
    method_name = bug_location.get("method")
    class_name = bug_location.get("class")

    assert method_name or class_name, f"Invalid bug location: {bug_location}"

    call_result = None

    def call_function(func_name: str, kwargs: dict[str, str]) -> None:
        nonlocal found, call_result

        intent = FunctionCallIntent(func_name, kwargs, None)
        call_result = api_manager.dispatch_intent(intent, msg_thread)
        _, _, call_is_ok = call_result
        found |= call_is_ok

    if (not found) and method_name and class_name:
        kwargs = {"method_name": method_name, "class_name": class_name}
        call_function("search_method_in_class", kwargs)

    if (not found) and method_name and file_name:
        kwargs = {"method_name": method_name, "file_name": file_name}
        call_function("search_method_in_file", kwargs)

    if (not found) and class_name and file_name:
        kwargs = {"class_name": class_name, "file_name": file_name}
        call_function("search_class_in_file", kwargs)

    if (not found) and class_name:
        kwargs = {"class_name": class_name}
        call_function("get_class_full_snippet", kwargs)

    if (not found) and method_name:
        kwargs = {"method_name": method_name}
        call_function("search_method", kwargs)

    assert call_result

    return call_result


def dump_tool_call_layers_to_file(
    tool_call_layers: list[dict], output_dir: str
) -> None:
    """Dump the layers of tool calls to a file."""
    tool_call_file = pjoin(output_dir, "tool_call_layers.json")
    with open(tool_call_file, "w") as f:
        json.dump(tool_call_layers, f, indent=4)


def start_conversation_round_state_machine(
    output_dir: str,
    msg_thread: MessageThread,
    api_manager: ProjectApiManager,
    start_round_no: int = 0,
) -> bool:
    """
    Start the actual rounds of conversations with model.

    Args:
        output_dir (str): Path to the output directory.
        msg_thread (MessageThread): The message thread to be used.
        api_manager (ProjectApiManager): The API manager to be used.
        start_round_no (int): The round number to start with.
    """
    round_no = start_round_no
    for round_no in range(start_round_no, globals.conv_round_limit + 1):
        conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
        # save current state before starting a new round
        msg_thread.save_to_file(conversation_file)
        log_and_cprint(
            f"\n========== Conversation Round {round_no} ==========", style="red bold"
        )
        log_and_print(f"{colored('Current message thread:', 'green')}\n{msg_thread}")

        allowed_tools = api_manager.next_tools()
        # TODO: configure the list of tools based on state machine
        tools = ProjectApiManager.get_full_funcs_for_openai(allowed_tools)

        log_and_cprint(f"Current tool state: {api_manager.curr_tool}", style="yellow")
        log_and_cprint(f"Allowed next tool states: {allowed_tools}", style="yellow")

        # create a new iteration of conversation
        res_text, raw_tool_calls, func_call_intents, *_ = common.SELECTED_MODEL.call(
            msg_thread.to_msg(), tools=tools
        )
        log_and_print(
            f"{colored('This roud model response (text):', 'blue')} {res_text}"
        )
        # model can decide whether to create a function call
        if len(func_call_intents) == 1:
            # good case in which we can check function call
            func_call_intent: FunctionCallIntent = func_call_intents[0]
            log_and_print(
                f"{colored('This round model response (function call):', 'blue')} {func_call_intent}"
            )
            # dispatch this function call
            this_model_response = res_text
            this_model_tools = raw_tool_calls
            # add previous call information to user message
            tool_output, summary, _ = api_manager.dispatch_intent(
                func_call_intent, msg_thread
            )
        else:
            # no function call, let's force the model to make one
            this_model_tools = []
            this_model_response = res_text
            tool_output = ""
            summary = "There is no function call in your previous response. Make sure you include one function call. "

        next_user_message = add_step_trigger(summary)

        # form message thread for next round. should include what the model said as well
        msg_thread.add_model(this_model_response, this_model_tools)
        if this_model_tools:
            tool_call_id = this_model_tools[0].id
            msg_thread.add_tool(tool_output, tool_call_id)
            msg_thread.add_user(next_user_message)
        else:
            msg_thread.add_user(next_user_message)

        if len(func_call_intents) == 1:
            func_call_name = func_call_intents[0].func_name
            if func_call_name == "write_patch":
                log_and_print("Ending workflow. write_patch has been invoked.")
                break

        log_and_print("Going to next round ..........")
    else:
        log_and_print("Too many rounds. Try writing patch anyway.")
        write_patch_intent = FunctionCallIntent("write_patch", {}, None)
        api_manager.dispatch_intent(write_patch_intent, msg_thread)

    round_no += 1

    # if we end the workflow normally, there is one more round of conversation to store
    conversation_file = pjoin(output_dir, f"conversation_round_{round_no}.json")
    msg_thread.save_to_file(conversation_file)
    return True


def run_one_task(
    output_dir: str,
    api_manager: ProjectApiManager,
    problem_stmt: str,
    test_patch: str,
    fix_patch: str, 
    repo_name: str,
    print_callback: Callable[[dict], None] | None = None,
) -> bool:
    """
    Main entry point to run inference on one task.
    Args:
        output_dir (str): Path to the output directory.
        api_manager (ProjectApiManager): The already-initialized API manager.
        problem_stmt (str): The original problem statement submitted to the task issue.
    """
    print_banner("Starting AutoCodeRover on the following issue")
    msg_thread = MessageThread()

    system_prompt = SYSTEM_PROMPT
    if (not globals.enable_layered) and common.SELECTED_MODEL.parallel_tool_call:
        # these models support parallel tool calls, let's try to make them not do it
        system_prompt += " In your response, DO NOT make more than one tool call."

    msg_thread.add_system(system_prompt)
    # ZZ: add test_patch info here
    original_prompt = prepare_issue_prompt(problem_stmt, test_patch)
    msg_thread.add_user(original_prompt)
    print_issue(original_prompt)

    # Add another user message about fault localization
    if globals.enable_sbfl:
        localization_result, _, _ = api_manager.fault_localization()
        localization_prompt = "An external analysis tool has been deployed to identify the suspicious code to be fixed. You can choose to use the results from this tool, if you think they are useful."
        localization_prompt += "The tool output is as follows:\n"
        localization_prompt += localization_result
        msg_thread.add_user(localization_prompt)

    if globals.enable_layered:
        return start_conversation_round_stratified(
            output_dir, msg_thread, api_manager, fix_patch, repo_name, print_callback=print_callback
        )
    else:
        return start_conversation_round_state_machine(
            output_dir, msg_thread, api_manager
        )


# NOTE: deprecated
def continue_task_from_cache(
    cache_path: str, output_dir: str, api_manager: ProjectApiManager
) -> bool:
    """
    Run inference on one task, but load conversation history from cache.
    Args:
        cache_path (str): Path to the old conversation history file.
        output_dir (str): Path to the output directory.
        api_manager (ProjectApiManager): The already-initialized API manager.
    """
    # (1) load the existing message thread
    msg_thread = MessageThread.load_from_file(cache_path)
    completed_round_no = msg_thread.get_round_number()

    # (2) start the actual workflow
    return start_conversation_round_state_machine(
        output_dir, msg_thread, api_manager, start_round_no=completed_round_no
    )
