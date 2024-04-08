import os
from os.path import join as pjoin
from pprint import pprint

from check_vanilla import get_resolved_tasks
from check_vanilla import main as main_vanilla
from check_vanilla import print_one_run


def main():
    vanilla_resolved_all = main_vanilla()

    print("\n\n======================== SBFL analysis ========================")

    script_dir = os.path.dirname(os.path.realpath(__file__))
    root_dir = os.path.dirname(script_dir)
    result_dir = pjoin(root_dir, "results")

    val_only_dir = pjoin(result_dir, "acr-val-only")
    val_sbfl_dir = pjoin(result_dir, "acr-val-sbfl")

    val_only_resolved = get_resolved_tasks(val_only_dir)
    val_sbfl_resolved = get_resolved_tasks(val_sbfl_dir)

    total_tasks = 300
    val_only_ratio = len(val_only_resolved) / total_tasks
    val_sbfl_ratio = len(val_sbfl_resolved) / total_tasks

    print_one_run("Val-Only", val_only_ratio, len(val_only_resolved), val_only_dir)
    print_one_run("Val-SBFL", val_sbfl_ratio, len(val_sbfl_resolved), val_sbfl_dir)

    val_only_extra = set(val_only_resolved) - set(val_sbfl_resolved)
    val_sbfl_extra = set(val_sbfl_resolved) - set(val_only_resolved)

    print(f"Val-Only extra: {len(val_only_extra)}")
    print(f"Val-SBFL extra: {len(val_sbfl_extra)}")

    print("\n")

    val_sbfl_extra_compared_to_all = val_sbfl_extra - set(vanilla_resolved_all)
    print(f"Val-SBFL extra compared to all: {len(val_sbfl_extra_compared_to_all)}")
    val_sbfl_extra_compared_to_all = sorted(list(val_sbfl_extra_compared_to_all))
    pprint(val_sbfl_extra_compared_to_all)


if __name__ == "__main__":
    main()
