"""
A script to drive end-to-end experiment workflow.
"""

import argparse
import configparser
import contextlib
import json
import os
import shutil
import subprocess
from glob import glob
from os.path import dirname as pdirname
from os.path import join as pjoin
from pathlib import Path
from statistics import mean

## globals
# whether to force delete existing data directories
force_delete: bool = False
# whether running combined experiment of lite, devin, and swe-25
running_combined: bool = False


# figure out some path to conda executable
conda_bin_path = os.getenv("CONDA_EXE")
conda_bin_dir = pdirname(conda_bin_path)
activate_path = pjoin(conda_bin_dir, "activate")
deactivate_path = pjoin(conda_bin_dir, "deactivate")


@contextlib.contextmanager
def cd(newdir):
    """
    Context manager for changing the current working directory
    :param newdir: path to the new directory
    :return: None
    """
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def create_fresh_dir(dir_name: str):
    """
    A helper method to create a fresh directory.
    """
    if (not force_delete) and os.path.exists(dir_name) and os.listdir(dir_name):
        print(
            f"{dir_name} is not empty. Please clear it or use -f option to force delete it."
        )
        exit(1)

    if os.path.exists(dir_name):
        shutil.rmtree(dir_name)

    os.makedirs(dir_name)


def run_string_cmd_in_conda(
    command: str, env_name: str, **kwargs
) -> subprocess.CompletedProcess:
    """
    Run a complete command in a given conda environment, where the command is a string.

    This is useful when the command to be run contains &&, etc.

    NOTE: use `conda activate` instead of `conda run` in this verison, so that we can
          run commands that contain `&&`, etc.
    NOTE: can find a similar version of this function in app/utils.py
    """
    conda_bin_path = os.getenv("CONDA_EXE")  # for calling conda
    conda_root_dir = pdirname(pdirname(conda_bin_path))
    conda_script_path = pjoin(conda_root_dir, "etc", "profile.d", "conda.sh")
    conda_cmd = f"source {conda_script_path} ; conda activate {env_name} ; {command} ; conda deactivate"
    cp = subprocess.run(conda_cmd, shell=True, **kwargs)
    return cp


def create_expr_dir(
    overall_expr_dir: str, expr_id: str, selected_tasks_file: str
) -> tuple[str, str]:
    """
    Create experiment dir, and copy the selected tasks file inside.

    Returns:
        - The new path of selected tasks file.
        - The experiment output dir
    """
    expr_dir = pjoin(overall_expr_dir, expr_id)
    create_fresh_dir(expr_dir)
    # os.makedirs(expr_dir, exist_ok=True)
    shutil.copy(selected_tasks_file, expr_dir)
    # figure out the name
    base_name = os.path.basename(selected_tasks_file)
    new_path = pjoin(expr_dir, base_name)
    return new_path, expr_dir


def run_agent(
    root_dir: str,
    setup_result_dir: str,
    expr_dir: str,
    task_list_file_path: str,
    model: str,
    temperature: float,
    enbale_sbfl: bool,
    enable_validation: bool,
    enable_angelic: bool,
    enable_perfect_angelic: bool,
    print_more: bool,
    conv_round_limit: int,
    num_processes: int,
):
    """
    Run the agent to perform the experiment.
    Returns:
        - The input file for SWE-bench.
    """
    setup_map_json = pjoin(setup_result_dir, "setup_map.json")
    tasks_map_json = pjoin(setup_result_dir, "tasks_map.json")
    if not os.path.exists(setup_map_json):
        raise FileNotFoundError(f"setup_map.json not found in {setup_result_dir}")
    if not os.path.exists(tasks_map_json):
        raise FileNotFoundError(f"task_map.json not found in {setup_result_dir}")

    added_env = {"PYTHONPATH": root_dir}
    modified_env = {**os.environ, **added_env}

    cmd = "python app/main.py swe-bench "
    cmd += f"--setup-map {setup_map_json} "
    cmd += f"--tasks-map {tasks_map_json} "
    cmd += f"--output-dir {expr_dir} "
    cmd += f"--task-list-file {task_list_file_path} "
    cmd += f"--model {model} "
    cmd += f"--model-temperature {temperature} "
    cmd += f"--conv-round-limit {conv_round_limit} "
    cmd += f"--num-processes {num_processes} "
    if enbale_sbfl:
        cmd += "--enable-sbfl "
    if enable_validation:
        cmd += "--enable-validation "
    if enable_angelic:
        cmd += "--enable-angelic "
    if enable_perfect_angelic:
        cmd += "--enable-perfect-angelic "
    if not print_more:
        cmd += "--no-print "

    print(f"Running agent workflow with cmd: {cmd}")
    with cd(root_dir):
        _ = run_string_cmd_in_conda(cmd, "auto-code-rover", env=modified_env)

    print("Done with running agent workflow.")
    swe_input_file = pjoin(expr_dir, "predictions_for_swebench.json")
    return swe_input_file


def run_swe_bench_eval(
    expr_id: str, swe_bench_dir: str, swe_input_file: str, eval_log_dir: str
):
    """
    Run SWE-bench evaluation.
    Returns:
        - The created log directory containing evaluation results.
    """
    expr_eval_log_dir = pjoin(eval_log_dir, expr_id)
    create_fresh_dir(expr_eval_log_dir)
    temp_eval_test_bed_dir = pjoin(swe_bench_dir, "temp_eval_testbed", expr_id)
    create_fresh_dir(temp_eval_test_bed_dir)
    all_tasks_json = pjoin(swe_bench_dir, "data", "swe-bench.json")

    cmd = "python harness/run_evaluation.py "
    cmd += f"--swe_bench_tasks {all_tasks_json} "
    cmd += f"--predictions_path {swe_input_file} "
    cmd += f"--log_dir {expr_eval_log_dir} "
    cmd += f"--testbed {temp_eval_test_bed_dir} "
    cmd += "--verbose "

    print(f"Running SWE-bench evaluation with cmd: {cmd}")
    with cd(swe_bench_dir):
        _ = run_string_cmd_in_conda(cmd, "swe-bench")

    print("Done with running SWE-bench evaluation.")
    return expr_eval_log_dir


def create_separate_reports(expr_dir: str, combined_report_path: str):
    script_dir = pdirname(os.path.realpath(__file__))
    root_dir = pdirname(script_dir)
    devin_task_file = pjoin(root_dir, "processed_data_devin", "tasks.txt")
    lite_task_file = pjoin(root_dir, "processed_data_lite", "test", "tasks.txt")
    swe25_task_file = pjoin(root_dir, "processed_data_swe_25", "tasks.txt")

    def read_tasks_from_file(file):
        with open(file) as f:
            tasks = f.read().splitlines()
        tasks = [t.strip().strip("\n") for t in tasks]
        tasks = [t for t in tasks if t]
        return tasks

    devin_tasks = read_tasks_from_file(devin_task_file)
    lite_tasks = read_tasks_from_file(lite_task_file)
    swe25_tasks = read_tasks_from_file(swe25_task_file)

    with open(combined_report_path) as f:
        combined_report = json.load(f)

    combined_fixed = combined_report["resolved"]

    devin_fixed = [t for t in combined_fixed if t in devin_tasks]
    lite_fixed = [t for t in combined_fixed if t in lite_tasks]
    swe25_fixed = [t for t in combined_fixed if t in swe25_tasks]

    def write_separate_report(resolved_tasks, all_tasks, report_path):
        report = dict()
        report["resolved"] = resolved_tasks
        report["total_num_tasks"] = len(all_tasks)
        report["num_resolved"] = len(resolved_tasks)
        # calculate in percentage, round to 4 decimal places
        resolve_rate = round(100 * len(resolved_tasks) / len(all_tasks), 4)
        report["resolve_rate"] = f"{resolve_rate} %"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=4)

    write_separate_report(
        devin_fixed, devin_tasks, pjoin(expr_dir, "final_report_devin_subset.json")
    )
    write_separate_report(
        lite_fixed, lite_tasks, pjoin(expr_dir, "final_report_lite_subset.json")
    )
    write_separate_report(
        swe25_fixed, swe25_tasks, pjoin(expr_dir, "final_report_swe_25_subset.json")
    )


def generate_report(
    expr_dir: str,
    swe_bench_dir: str,
    swe_input_file: str,
    expr_eval_log_dir: str,
    model: str,
):
    """
    Generate a report for the experiment.
    Returns:
        - Path to the final report json file.
    """
    all_tasks_json = pjoin(swe_bench_dir, "data", "swe-bench.json")

    final_report_path = pjoin(expr_dir, "final_report.json")

    cmd = "python metrics/report.py "
    cmd += f"--task_file {all_tasks_json} "
    cmd += f"--predictions {swe_input_file} "
    cmd += f"--logs {expr_eval_log_dir} "
    cmd += f"--model {model} "
    cmd += f"--out {final_report_path} "

    print(f"Generating final report with cmd: {cmd}")
    with cd(swe_bench_dir):
        _ = run_string_cmd_in_conda(cmd, "swe-bench")

    print("Done with generating final report.")
    return final_report_path


def generate_stats(expr_dir: str):
    cost_files = glob(pjoin(expr_dir, "**", "*__*", "cost.json"))
    cost_data = [json.loads(Path(file).read_text()) for file in cost_files]

    stats = {}
    stats["num_tasks"] = len(cost_data)

    stats["model"] = cost_data[0]["model"]
    stats["commit"] = cost_data[0]["commit"]
    stats["input_cost_per_token"] = cost_data[0]["input_cost_per_token"]
    stats["output_cost_per_token"] = cost_data[0]["output_cost_per_token"]

    total_cost = sum(x["total_cost"] for x in cost_data)
    stats["total_cost"] = total_cost
    stats["avg_cost"] = total_cost / len(cost_data)

    avg_input_tokens = mean(x["total_input_tokens"] for x in cost_data)
    avg_output_tokens = mean(x["total_output_tokens"] for x in cost_data)
    stats["avg_tokens"] = round(avg_input_tokens + avg_output_tokens, 1)
    stats["avg_input_tokens"] = round(avg_input_tokens, 1)
    stats["avg_output_tokens"] = round(avg_output_tokens, 1)

    inference_start_epoch = min(x["start_epoch"] for x in cost_data)
    inference_end_epoch = max(x["end_epoch"] for x in cost_data)
    inference_elapsed = inference_end_epoch - inference_start_epoch
    stats["inference_start_epoch"] = inference_start_epoch
    stats["inference_end_epoch"] = inference_end_epoch
    stats["inference_elapsed_mins"] = round(inference_elapsed / 60, 2)
    stats["inference_avg_elapsed_secs_parallel"] = round(
        inference_elapsed / len(cost_data), 1
    )
    stats["inference_avg_elapsed_secs_serial"] = round(
        mean(x["elapsed_seconds"] for x in cost_data), 1
    )

    with open(pjoin(expr_dir, "stats.json"), "w") as f:
        json.dump(stats, f, indent=4)


def main():
    global force_delete, running_combined
    parser = argparse.ArgumentParser()
    parser.add_argument("conf_file", help="Configuration file")
    parser.add_argument(
        "--with-eval",
        action="store_true",
        default=False,
        help="Additionally perform SWE-bench evaluation (deprecated)",
    )
    parser.add_argument(
        "-f",
        "--force-delete",
        action="store_true",
        default=False,
        help="Force delete existing data in experiment dir (if any)",
    )
    parser.add_argument(
        "-c",
        "--combined",
        action="store_true",
        default=False,
        help="Run combined Lite, Devin, SWE-25 experiment. Will generate seperate report file for each subset.",
    )
    args = parser.parse_args()

    conf_file = args.conf_file
    force_delete = args.force_delete
    running_combined = args.combined

    # (1) Read configuration file
    if not os.path.exists(conf_file):
        raise FileNotFoundError(f"Configuration file {conf_file} not found")
    config = configparser.ConfigParser()

    # TODO: use a single conf file for all experiments and use different sections
    # for individual experiments
    default_section = "DEFAULT"
    with open(conf_file) as f:
        config.read_string(f"[{default_section}]\n" + f.read())

    config_dict = config["DEFAULT"]
    expr_id = config_dict["id"]
    overall_expr_dir = config_dict["experiment_dir"]
    setup_result_dir = config_dict["setup_result_dir"]
    swe_bench_dir = config_dict.get("swe_bench_dir", fallback="")
    eval_log_dir = config_dict.get("eval_log_dir", fallback="")

    model = config_dict["model"]
    temperature = float(config_dict["temperature"])
    selected_tasks_file = config_dict["selected_tasks_file"]
    enable_sbfl = config.getboolean("DEFAULT", "enable_sbfl", fallback=False)
    enable_validation = config.getboolean(
        "DEFAULT", "enable_validation", fallback=False
    )
    enable_angelic = config.getboolean("DEFAULT", "enable_angelic", fallback=False)
    enable_perfect_angelic = config.getboolean(
        "DEFAULT", "enable_perfect_angelic", fallback=False
    )
    conv_round_limit = config.getint("DEFAULT", "conv_round_limit", fallback=15)

    print_more = config.getboolean("DEFAULT", "print", fallback=False)
    num_processes = int(config_dict["num_processes"])

    expr_dir = pjoin(overall_expr_dir, expr_id)
    task_list_file_path = pjoin(expr_dir, os.path.basename(selected_tasks_file))

    create_fresh_dir(expr_dir)

    shutil.copy(selected_tasks_file, expr_dir)

    script_dir = pdirname(os.path.realpath(__file__))
    root_dir = pdirname(script_dir)  # root of this repo

    swe_input_file = run_agent(
        root_dir,
        setup_result_dir,
        expr_dir,
        task_list_file_path,
        model,
        temperature,
        enable_sbfl,
        enable_validation,
        enable_angelic,
        enable_perfect_angelic,
        print_more,
        conv_round_limit,
        num_processes,
    )

    if args.with_eval:
        expr_eval_log_dir = run_swe_bench_eval(
            expr_id, swe_bench_dir, swe_input_file, eval_log_dir
        )

        final_report_path = generate_report(
            expr_dir, swe_bench_dir, swe_input_file, expr_eval_log_dir, model
        )

    generate_stats(expr_dir)

    print(f"Experiment {expr_id} done. SWE-bench eval input file is at {swe_input_file}.")

    if running_combined:
        create_separate_reports(expr_dir, final_report_path)
        print("Created separate reports for each subset.")


if __name__ == "__main__":
    main()
