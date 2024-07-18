"""
A global store, for values that can be mutated in multiprocessing, along with their related values.
"""

import multiprocessing

# to be set at beginning
total_num_tasks = 0
num_completed_tasks = multiprocessing.Value("i", 0)


# to be set at beginning
total_num_task_groups = 0
num_completed_task_groups = multiprocessing.Value("i", 0)


def init_total_num_tasks(n: int):
    global total_num_tasks
    total_num_tasks = n


def init_total_num_task_groups(n: int):
    global total_num_task_groups
    total_num_task_groups = n


def incre_completed_tasks() -> int:
    with num_completed_tasks.get_lock():
        num_completed_tasks.value += 1
    return num_completed_tasks.value


def incre_completed_task_groups() -> int:
    with num_completed_task_groups.get_lock():
        num_completed_task_groups.value += 1
    return num_completed_task_groups.value


def incre_task_return_msg() -> str:
    completed = incre_completed_tasks()
    completed_groups = num_completed_task_groups.value
    return f">>> Completed {completed}/{total_num_tasks} tasks. For groups, completed {completed_groups}/{total_num_task_groups} so far."


def incre_task_group_return_msg() -> str:
    completed = incre_completed_task_groups()
    return f">>>>>> Completed {completed}/{total_num_task_groups} task groups."
