import json
import os
from os.path import join as pjoin
from pprint import pprint


def get_resolved_tasks(expr_dir):
    final_report = pjoin(expr_dir, "new_eval_results", "report.json")
    with open(final_report) as f:
        final_report = json.load(f)
    resolved_tasks = final_report["resolved"]
    return resolved_tasks


def print_one_run(name, resolved_ratio, num_resolved, expr_dir):
    stats_file = pjoin(expr_dir, "stats.json")
    with open(stats_file) as f:
        stats = json.load(f)
    average_time = stats["inference_avg_elapsed_secs_serial"]
    average_token = stats["avg_tokens"]
    average_cost = stats["avg_cost"]
    print(
        f"{name} - Resolved: {resolved_ratio*100:.2f}% ({num_resolved}), Average Time: {average_time:.0f}s, Average Tokens: {average_token:.0f}, Average Cost: {average_cost:.3f}"
    )
    return average_time, average_token, average_cost


def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    root_dir = os.path.dirname(script_dir)
    result_dir = pjoin(root_dir, "results")

    run_one_dir = pjoin(result_dir, "acr-run-1")
    run_two_dir = pjoin(result_dir, "acr-run-2")
    run_three_dir = pjoin(result_dir, "acr-run-3")

    run_one_resolved = get_resolved_tasks(run_one_dir)
    run_two_resolved = get_resolved_tasks(run_two_dir)
    run_three_resolved = get_resolved_tasks(run_three_dir)

    # average_resolved = (run_one_resolved + run_two_resolved + run_three_resolved) / 3
    total_tasks = 300

    acr_one_ratio = len(run_one_resolved) / total_tasks
    acr_two_ratio = len(run_two_resolved) / total_tasks
    acr_three_ratio = len(run_three_resolved) / total_tasks

    one_time, one_token, one_cost = print_one_run(
        "ACR-1", acr_one_ratio, len(run_one_resolved), run_one_dir
    )
    two_time, two_token, two_cost = print_one_run(
        "ACR-2", acr_two_ratio, len(run_two_resolved), run_two_dir
    )
    three_time, three_token, three_cost = print_one_run(
        "ACR-3", acr_three_ratio, len(run_three_resolved), run_three_dir
    )

    # compute average
    average_num_resolved = (
        len(run_one_resolved) + len(run_two_resolved) + len(run_three_resolved)
    ) / 3
    average_ratio = (
        len(run_one_resolved) + len(run_two_resolved) + len(run_three_resolved)
    ) / (3 * total_tasks)
    average_time = (one_time + two_time + three_time) / 3
    average_token = (one_token + two_token + three_token) / 3
    average_cost = (one_cost + two_cost + three_cost) / 3

    print(
        f"Average: {average_ratio*100:.2f}% ({average_num_resolved:.1f}) Average Time: {average_time:.0f}s, Average Tokens: {average_token:.0f}, Average Cost: {average_cost:.3f}"
    )

    # total
    total_time = one_time + two_time + three_time
    total_token = one_token + two_token + three_token
    total_cost = one_cost + two_cost + three_cost

    all_resolved = set(run_one_resolved + run_two_resolved + run_three_resolved)
    union_ratio = len(all_resolved) / total_tasks
    print(
        f"Total: {union_ratio*100:.2f}% ({len(all_resolved)}) Total Time: {total_time:.0f}s, Total Tokens: {total_token:.0f}, Total Cost: {total_cost:.3f}"
    )

    print("All resolved tasks in union:")
    all_resolved = sorted(all_resolved)
    pprint(all_resolved)

    return all_resolved


if __name__ == "__main__":
    main()
