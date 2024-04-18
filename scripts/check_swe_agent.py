import json
import os
from os.path import join as pjoin

from check_vanilla import get_resolved_tasks


def get_intersec(list_one, list_two):
    return list(set(list_one) & set(list_two))


def get_tasks_with_traj(result_dir):
    traj_files = [x for x in os.listdir(pjoin(result_dir)) if x.endswith(".traj")]
    tasks_with_traj = [x.split(".")[0] for x in traj_files]
    return tasks_with_traj


def get_one_instance_cost(traj_file):
    with open(traj_file) as f:
        traj = json.load(f)
    cost = float(traj["info"]["model_stats"]["instance_cost"])
    in_token = int(traj["info"]["model_stats"]["tokens_sent"])
    out_token = int(traj["info"]["model_stats"]["tokens_received"])
    return cost, in_token + out_token


def compute_avg_cost(result_dir, tasks):
    """
    result_dir should have .traj for all tasks in `tasks`.
    """
    traj_files = [f"{t}.traj" for t in tasks]
    traj_files = [pjoin(result_dir, t) for t in traj_files]
    total_cost = 0.0
    total_tokens = 0
    for f in traj_files:
        cost, tokens = get_one_instance_cost(f)
        total_cost += cost
        total_tokens += tokens
    avg_cost = total_cost / len(tasks)
    avg_tokens = total_tokens / len(tasks)
    return avg_cost, avg_tokens


def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    root_dir = os.path.dirname(script_dir)
    result_dir = pjoin(root_dir, "results")

    swe_agent_dir = pjoin(result_dir, "swe-agent-results")

    # STEP (1) get lists of tasks with .traj files and find the overlap of them
    #          This is the final list of tasks in Figure 6

    run_one = "cost_2_1"
    run_two = "cost_2_2"
    run_three = "cost_2_3"
    run_one_dir = pjoin(swe_agent_dir, run_one)
    run_two_dir = pjoin(swe_agent_dir, run_two)
    run_three_dir = pjoin(swe_agent_dir, run_three)

    run_one_tasks = get_tasks_with_traj(run_one_dir)
    run_two_tasks = get_tasks_with_traj(run_two_dir)
    run_three_tasks = get_tasks_with_traj(run_three_dir)

    tasks_fig_6 = set(run_one_tasks) & set(run_two_tasks) & set(run_three_tasks)
    tasks_fig_6 = list(tasks_fig_6)
    print(f"All considered tasks: {len(tasks_fig_6)}")

    print(
        "\n================================= SWE-agent results over 274 instances that could be run by it: ================================="
    )

    # STEP (2) get resolved tasks for each run.
    run_one_resolved = get_resolved_tasks(run_one_dir)
    run_two_resolved = get_resolved_tasks(run_two_dir)
    run_three_resolved = get_resolved_tasks(run_three_dir)
    # Since only 274 overlapped are considered, do a filtering
    run_one_resolved = [x for x in run_one_resolved if x in tasks_fig_6]
    run_two_resolved = [x for x in run_two_resolved if x in tasks_fig_6]
    run_three_resolved = [x for x in run_three_resolved if x in tasks_fig_6]

    run_one_ratio = len(run_one_resolved) / len(tasks_fig_6)
    run_two_ratio = len(run_two_resolved) / len(tasks_fig_6)
    run_three_ratio = len(run_three_resolved) / len(tasks_fig_6)

    print(f"{run_one} - Resolved: {run_one_ratio*100:.2f}% ({len(run_one_resolved)})")
    print(f"{run_two} - Resolved: {run_two_ratio*100:.2f}% ({len(run_two_resolved)})")
    print(
        f"{run_three} - Resolved: {run_three_ratio*100:.2f}% ({len(run_three_resolved)})"
    )

    # STEP (3) compute average
    average_num_resolved = (
        len(run_one_resolved) + len(run_two_resolved) + len(run_three_resolved)
    ) / 3
    average_ratio = average_num_resolved / len(tasks_fig_6)
    print(
        f"Average resolved tasks: {average_ratio*100:.2f}% ({average_num_resolved:.1f})"
    )

    # STEP (4) get union of the resolved tasks
    resolved_union = (
        set(run_one_resolved) | set(run_two_resolved) | set(run_three_resolved)
    )
    resolved_union = list(resolved_union)
    union_ratio = len(resolved_union) / len(tasks_fig_6)
    print(f"Union of resolved tasks: {union_ratio*100:.2f}% ({len(resolved_union)})")

    print(
        "\n================================= ACR results over these 274 instances: ================================="
    )

    # STEP (5) Get resolved from ACR, and filter based on 274 tasks
    # Following is basically repetition of what we computed above
    acr_run_one_dir = pjoin(result_dir, "acr-run-1")
    acr_run_two_dir = pjoin(result_dir, "acr-run-2")
    acr_run_three_dir = pjoin(result_dir, "acr-run-3")
    acr_run_one_resolved = get_resolved_tasks(acr_run_one_dir)
    acr_run_two_resolved = get_resolved_tasks(acr_run_two_dir)
    acr_run_three_resolved = get_resolved_tasks(acr_run_three_dir)
    acr_run_one_resolved = [x for x in acr_run_one_resolved if x in tasks_fig_6]
    acr_run_two_resolved = [x for x in acr_run_two_resolved if x in tasks_fig_6]
    acr_run_three_resolved = [x for x in acr_run_three_resolved if x in tasks_fig_6]

    acr_run_one_ratio = len(acr_run_one_resolved) / len(tasks_fig_6)
    acr_run_two_ratio = len(acr_run_two_resolved) / len(tasks_fig_6)
    acr_run_three_ratio = len(acr_run_three_resolved) / len(tasks_fig_6)

    print(
        f"ACR-1 - Resolved: {acr_run_one_ratio*100:.2f}% ({len(acr_run_one_resolved)})"
    )
    print(
        f"ACR-2 - Resolved: {acr_run_two_ratio*100:.2f}% ({len(acr_run_two_resolved)})"
    )
    print(
        f"ACR-3 - Resolved: {acr_run_three_ratio*100:.2f}% ({len(acr_run_three_resolved)})"
    )

    # STEP (6) compute average
    acr_average_num_resolved = (
        len(acr_run_one_resolved)
        + len(acr_run_two_resolved)
        + len(acr_run_three_resolved)
    ) / 3
    acr_average_ratio = acr_average_num_resolved / len(tasks_fig_6)
    print(
        f"ACR-Average resolved tasks: {acr_average_ratio*100:.2f}% ({acr_average_num_resolved:.1f})"
    )

    # STEP (7) get union of the resolved tasks
    acr_resolved_union = (
        set(acr_run_one_resolved)
        | set(acr_run_two_resolved)
        | set(acr_run_three_resolved)
    )
    acr_resolved_union = list(acr_resolved_union)
    acr_union_ratio = len(acr_resolved_union) / len(tasks_fig_6)
    print(
        f"ACR-Union of resolved tasks: {acr_union_ratio*100:.2f}% ({len(acr_resolved_union)})"
    )

    print(
        "\n================================= Venn for SWE-Agent-all and ACR-all ================================="
    )
    swe_agent_extra = set(resolved_union) - set(acr_resolved_union)
    acr_extra = set(acr_resolved_union) - set(resolved_union)
    insersec = get_intersec(resolved_union, acr_resolved_union)
    print(f"SWE-Agent extra: {len(swe_agent_extra)}")
    print(f"ACR extra: {len(acr_extra)}")
    print(f"Intersection: {len(insersec)}")

    print(
        "\n================================= Compute cost and tokesn for SWE-agent ================================="
    )
    run_one_cost, run_one_tokens = compute_avg_cost(run_one_dir, tasks_fig_6)
    run_two_cost, run_two_tokens = compute_avg_cost(run_two_dir, tasks_fig_6)
    run_three_cost, run_three_tokens = compute_avg_cost(run_three_dir, tasks_fig_6)
    print(f"Run-1: Cost: {run_one_cost:.6f}, Tokens: {run_one_tokens:.2f}")
    print(f"Run-2: Cost: {run_two_cost:.6f}, Tokens: {run_two_tokens:.2f}")
    print(f"Run-3: Cost: {run_three_cost:.6f}, Tokens: {run_three_tokens:.2f}")
    avg_of_avg_cost = (run_one_cost + run_two_cost + run_three_cost) / 3
    avg_of_avg_tokens = (run_one_tokens + run_two_tokens + run_three_tokens) / 3
    print(f"Average of average cost: {avg_of_avg_cost:.6f}")
    print(f"Average of average tokens: {avg_of_avg_tokens:.2f}")


if __name__ == "__main__":

    main()
