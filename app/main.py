"""
The main driver.
"""

import argparse
import json
import subprocess
from datetime import datetime
from itertools import chain
from multiprocessing import Pool
from os.path import join as pjoin
from subprocess import CalledProcessError

from loguru import logger

from app import globals, globals_mut, inference, log
from app import utils as apputils
from app.api.manage import ProjectApiManager
from app.post_process import (
    extract_organize_and_form_input,
    get_final_patch_path,
    organize_and_form_input,
    reextract_organize_and_form_inputs,
)
from app.raw_tasks import RawGithubTask, RawSweTask
from app.task import Task


def get_current_commit_hash() -> str:
    command = ["git", "rev-parse", "HEAD"]
    cp = subprocess.run(command, text=True, capture_output=True)
    try:
        cp.check_returncode()
        return cp.stdout.strip()
    except CalledProcessError as e:
        raise RuntimeError(f"Failed to get SHA-1 of HEAD: {cp.stderr}") from e


def main():
    parser = argparse.ArgumentParser()
    ## Common options
    # where to store run results
    parser.add_argument(
        "--mode",
        default="swe_bench",
        choices=["swe_bench", "fresh_issue"],
        help="Choose to run tasks in SWE-bench, or a fresh issue from the internet.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Path to the directory that stores the run results.",
    )
    parser.add_argument(
        "--num-processes",
        type=str,
        default=1,
        help="Number of processes to run the tasks in parallel.",
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        default=False,
        help="Do not print most messages to stdout.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-3.5-turbo-0125",
        choices=globals.MODELS,
        help="The model to use. Currently only OpenAI models are supported.",
    )
    parser.add_argument(
        "--model-temperature",
        type=float,
        default=0.0,
        help="The model temperature to use, for OpenAI models.",
    )
    parser.add_argument(
        "--conv-round-limit",
        type=int,
        default=15,
        help="Conversation round limit for the main agent.",
    )
    parser.add_argument(
        "--extract-patches",
        type=str,
        help="Only extract patches from the raw results dir. Voids all other arguments if this is used.",
    )
    parser.add_argument(
        "--re-extract-patches",
        type=str,
        help="same as --extract-patches, except that individual dirs are moved out of their categories first",
    )
    parser.add_argument(
        "--enable-layered",
        action="store_true",
        default=False,
        help="Enable layered code search.",
    )

    swe_group = parser.add_argument_group(
        "swe_bench", description="Arguments for running on SWE-bench tasks."
    )
    ## task info when running instances in SWE-bench
    swe_group.add_argument(
        "--setup-map",
        type=str,
        help="Path to json file that contains the setup information of the projects.",
    )
    swe_group.add_argument(
        "--tasks-map",
        type=str,
        help="Path to json file that contains the tasks information.",
    )
    swe_group.add_argument(
        "--task-list-file",
        type=str,
        help="Path to the file that contains all tasks ids to be run.",
    )
    swe_group.add_argument("--task", type=str, help="Task id to be run.")
    ## Only support test-based options for SWE-bench tasks for now
    swe_group.add_argument(
        "--enable-sbfl", action="store_true", default=False, help="Enable SBFL."
    )
    swe_group.add_argument(
        "--enable-validation",
        action="store_true",
        default=False,
        help="Enable validation in our workflow.",
    )
    swe_group.add_argument(
        "--enable-angelic",
        action="store_true",
        default=False,
        help="(Experimental) Enable angelic debugging",
    )
    swe_group.add_argument(
        "--enable-perfect-angelic",
        action="store_true",
        default=False,
        help="(Experimental) Enable perfect angelic debugging; overrides --enable-angelic",
    )
    swe_group.add_argument(
        "--save-sbfl-result",
        action="store_true",
        default=False,
        help="Special mode to only save SBFL results for future runs.",
    )

    fresh_group = parser.add_argument_group(
        "fresh_issue",
        description="Arguments for running on fresh issues from the internet.",
    )
    ## task info when running on new issues from GitHub
    fresh_group.add_argument(
        "--fresh-task-id",
        type=str,
        help="Assign an id to the current fresh issue task.",
    )
    fresh_group.add_argument(
        "--clone-link",
        type=str,
        help="[Fresh issue] The link to the repository to clone.",
    )
    fresh_group.add_argument(
        "--commit-hash", type=str, help="[Fresh issue] The commit hash to checkout."
    )
    fresh_group.add_argument(
        "--issue-link", type=str, help="[Fresh issue] The link to the issue."
    )
    fresh_group.add_argument(
        "--setup-dir",
        type=str,
        help="[Fresh issue] The directory where repositories should be cloned to.",
    )

    args = parser.parse_args()
    ## common options
    mode = args.mode
    globals.output_dir = args.output_dir
    if globals.output_dir is not None:
        globals.output_dir = apputils.convert_dir_to_absolute(globals.output_dir)
    num_processes: int = int(args.num_processes)
    # set whether brief or verbose log
    print_stdout: bool = not args.no_print
    log.print_stdout = print_stdout
    globals.model = args.model
    globals.model_temperature = args.model_temperature
    globals.conv_round_limit = args.conv_round_limit
    extract_patches: str | None = args.extract_patches
    re_extract_patches: str | None = args.re_extract_patches
    globals.enable_layered = args.enable_layered

    ## options for swe-bench mode
    setup_map_file = args.setup_map
    tasks_map_file = args.tasks_map
    task_list_file: str | None = args.task_list_file
    task_id: str | None = args.task
    globals.enable_sbfl = args.enable_sbfl
    globals.enable_validation = args.enable_validation
    globals.enable_angelic = args.enable_angelic
    globals.enable_perfect_angelic = args.enable_perfect_angelic
    globals.only_save_sbfl_result = args.save_sbfl_result

    ## options for fresh_issue mode
    fresh_task_id = args.fresh_task_id
    clone_link = args.clone_link
    commit_hash = args.commit_hash
    issue_link = args.issue_link
    setup_dir = args.setup_dir
    if setup_dir is not None:
        setup_dir = apputils.convert_dir_to_absolute(setup_dir)

    ## Firstly deal with special modes
    if globals.only_save_sbfl_result and extract_patches is not None:
        raise ValueError(
            "Cannot save SBFL result and extract patches at the same time."
        )

    # special mode 1: extract patch, for this we can early exit
    if re_extract_patches is not None:
        extract_patches = apputils.convert_dir_to_absolute(re_extract_patches)
        reextract_organize_and_form_inputs(re_extract_patches)
        return

    if extract_patches is not None:
        extract_patches = apputils.convert_dir_to_absolute(extract_patches)
        extract_organize_and_form_input(extract_patches)
        return

    if mode == "swe_bench":
        tasks = make_swe_tasks(task_id, task_list_file, setup_map_file, tasks_map_file)
        groups = group_swe_tasks_by_env(tasks)
    else:
        task = RawGithubTask(
            fresh_task_id, clone_link, commit_hash, issue_link, setup_dir
        )
        groups = {"github": [task]}
    run_task_groups(groups, num_processes)


def make_swe_tasks(
    task_id: str | None,
    task_list_file: str | None,
    setup_map_file: str,
    tasks_map_file: str,
) -> list[RawSweTask]:
    if task_id is not None and task_list_file is not None:
        raise ValueError("Cannot specify both task and task-list.")

    all_task_ids = []
    if task_list_file is not None:
        all_task_ids = parse_task_list_file(task_list_file)
    if task_id is not None:
        all_task_ids = [task_id]
    if len(all_task_ids) == 0:
        raise ValueError("No task ids to run.")

    with open(setup_map_file) as f:
        setup_map = json.load(f)
    with open(tasks_map_file) as f:
        tasks_map = json.load(f)

    # for each task in the list to run, create a Task instance
    all_tasks = []
    all_task_ids = sorted(all_task_ids)
    for task_id in all_task_ids:
        setup_info = setup_map[task_id]
        task_info = tasks_map[task_id]
        task = RawSweTask(task_id, setup_info, task_info)
        all_tasks.append(task)
    return all_tasks


def parse_task_list_file(task_list_file: str) -> list[str]:
    """
    Parse the task list file.
    The file should contain one task/instance id per line, without other characters.
    """
    with open(task_list_file) as f:
        task_ids = f.readlines()
    return [x.strip() for x in task_ids]


def group_swe_tasks_by_env(tasks: list[RawSweTask]) -> dict[str, list[RawSweTask]]:
    groups = {}
    for task in tasks:
        key = task.setup_info["env_name"]
        if key not in groups:
            groups[key] = []
        groups[key].append(task)
    return groups


def run_task_groups(
    task_groups: dict[str, list[RawSweTask]] | dict[str, list[RawGithubTask]],
    num_processes: int,
):
    """
    Main entry for swe-bench mode.
    """
    all_tasks = list(chain.from_iterable(task_groups.values()))
    num_tasks = len(all_tasks)

    globals_mut.init_total_num_tasks(num_tasks)

    # print some info about task
    log.print_with_time(f"Total number of tasks: {num_tasks}")
    log.print_with_time(f"Total number of processes: {num_processes}")
    log.print_with_time(f"Task group info: (number of groups: {len(task_groups)})")
    for key, tasks in task_groups.items():
        log.print_with_time(f"\t{key}: {len(tasks)} tasks")

    # single process mode
    if num_processes == 1:
        log.print_with_time("Running in single process mode.")
        run_tasks_serial(all_tasks)
        log.print_with_time("Finished all tasks sequentially.")
    else:
        run_task_groups_parallel(task_groups, num_processes)

    if globals.only_save_sbfl_result:
        log.print_with_time("Only saving SBFL results. Exiting.")
        return

    # post-process completed experiments to get input file to SWE-bench
    log.print_with_time("Post-processing completed experiment results.")
    swe_input_file = organize_and_form_input(globals.output_dir)
    log.print_with_time(f"SWE-Bench input file created: {swe_input_file}")


def run_tasks_serial(tasks: list[RawSweTask | RawGithubTask]) -> None:
    for task in tasks:
        run_raw_task(task)


def run_task_groups_parallel(
    task_groups: dict[str, list[RawSweTask]] | dict[str, list[RawGithubTask]],
    num_processes: int,
):
    num_task_groups = len(task_groups)
    globals_mut.init_total_num_task_groups(num_task_groups)
    num_processes = min(num_processes, num_task_groups)

    task_group_ids_items = sorted(
        task_groups.items(),
        key=lambda x: len(x[1]),
        reverse=True,
    )
    log.print_with_time(f"Sorted task groups: {[x[0] for x in task_group_ids_items]}")
    try:
        pool = Pool(processes=num_processes)
        pool.starmap(run_task_group, task_group_ids_items)
        pool.close()
        pool.join()
    finally:
        log.print_with_time("Finishing all tasks in the pool.")


def run_task_group(
    task_group_id: str, task_group_items: list[RawSweTask | RawGithubTask]
) -> None:
    """
    Run all tasks in a task group sequentially.
    Main entry to parallel processing.
    """
    log.print_with_time(
        f"Starting process for task group {task_group_id}. Number of tasks: {len(task_group_items)}."
    )
    for task in task_group_items:
        # within a group, the runs are always sequential
        run_raw_task(task)
        log.print_with_time(globals_mut.incre_task_return_msg())

    log.print_with_time(
        f"{globals_mut.incre_task_group_return_msg()} Finished task group {task_group_id}."
    )


def run_raw_task(task: RawSweTask | RawGithubTask) -> bool:
    """
    High-level entry for running one task.

    Args:
        - task: The Task instance to run.

    Returns:
        Whether the task completed successfully.
    """
    task_id = task.task_id

    start_time_s = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    task_output_dir = pjoin(globals.output_dir, f"{task_id}_{start_time_s}")
    apputils.create_dir_if_not_exists(task_output_dir)

    task.dump_meta_data(task_output_dir)

    log.log_and_always_print(
        f"============= Running task {task_id} =============",
    )

    run_ok = False

    try:
        run_ok = do_inference(task.to_task(), task_output_dir)

        if run_ok:
            run_status_message = f"Task {task_id} completed successfully."
        else:
            run_status_message = f"Task {task_id} failed without exception."
    except Exception as e:
        logger.exception(e)
        run_status_message = f"Task {task_id} failed with exception: {e}."

    log.log_and_always_print(run_status_message)

    final_patch_path = get_final_patch_path(task_output_dir)
    if final_patch_path is not None:
        log.log_and_always_print(
            f"Please find the generated patch at: {final_patch_path}"
        )
    else:
        log.log_and_always_print("No patch generated. You can try running ACR again.")

    return run_ok


def do_inference(python_task: Task, task_output_dir: str) -> bool:

    apputils.create_dir_if_not_exists(task_output_dir)

    logger.add(
        pjoin(task_output_dir, "info.log"),
        level="DEBUG",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level>"
            " | <level>{message}</level>"
        ),
    )

    start_time = datetime.now()

    api_manager = ProjectApiManager(python_task, task_output_dir)

    try:
        if globals.only_save_sbfl_result:
            _, _, run_ok = api_manager.fault_localization()
        else:
            run_ok = inference.run_one_task(
                api_manager.output_dir, api_manager, python_task.get_issue_statement()
            )

            api_manager.dump_tool_call_sequence_to_file()
            api_manager.dump_tool_call_layers_to_file()

            end_time = datetime.now()

            dump_cost(api_manager, start_time, end_time, task_output_dir)
    finally:
        python_task.reset_project()

    return run_ok


def dump_cost(
    api_manager: ProjectApiManager,
    start_time: datetime,
    end_time: datetime,
    task_output_dir: str,
):
    input_cost_per_token = globals.MODEL_COST_PER_INPUT[globals.model]
    output_cost_per_token = globals.MODEL_COST_PER_INPUT[globals.model]
    with open(pjoin(task_output_dir, "cost.json"), "w") as f:
        json.dump(
            {
                "model": globals.model,
                "commit": get_current_commit_hash(),
                "input_cost_per_token": input_cost_per_token,
                "output_cost_per_token": output_cost_per_token,
                "total_input_tokens": api_manager.input_tokens,
                "total_output_tokens": api_manager.output_tokens,
                "total_tokens": api_manager.input_tokens + api_manager.output_tokens,
                "total_cost": api_manager.cost,
                "start_epoch": start_time.timestamp(),
                "end_epoch": end_time.timestamp(),
                "elapsed_seconds": (end_time - start_time).total_seconds(),
            },
            f,
            indent=4,
        )


if __name__ == "__main__":
    logger.remove()
    main()
