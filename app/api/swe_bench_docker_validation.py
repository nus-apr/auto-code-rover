"""
Contains all functions that run validation through SWE-bench-docker containers.
See SWE-bench-docker here: https://github.com/aorwall/SWE-bench-docker

Code here are taken from / inspired by https://github.com/paul-gauthier/aider-swe-bench,
and code in this file is distributed under Apache License 2.0.
"""

import asyncio
import os
import random
import shutil
import string
import sys
from pathlib import Path

from app.utils import create_fresh_dir

script_dir = os.path.dirname(__file__)
root_dir = os.path.dirname(os.path.dirname(script_dir))
swe_bench_docker_dir = os.path.join(root_dir, "SWE-bench-docker")
sys.path.append(swe_bench_docker_dir)

from swebench_docker.constants import (  # noqa E402 # type: ignore
    MAP_REPO_TO_TEST_FRAMEWORK,
)
from swebench_docker.run_docker import run_docker_evaluation  # noqa E402 # type: ignore
from swebench_docker.utils import get_test_directives  # noqa E402 # type: ignore

NOOP_PATCH = (
    "diff --git a/empty.file.test_patch.ignore b/empty.file.test_patch.ignore\n"
    "new file mode 100644\n"
    "index 0000000..e69de29\n"
)


def run_pre_existing_tests(
    repo: str,
    version: str,
    instance_id: str,
    base_commit: str,
    developer_test_patch: str,
    generated_prog_patch: str,
) -> tuple[bool, str]:
    """
    Run the pre-existing tests in the project.
    NOTE: the tests executed here do not include the newly written patch by developer.
          (i.e. the tests do not include content in test_patch field from SWE-bench.)

    Args:
        - repo: repo name.
        - version: version of the repo.
        - instance_id: instance id in SWE-bench.
        - base_commit: base commit of the instance.
        - developer_test_patch: Developer added new test for this task. Used here
                to get the test directives.
        - generated_prog_patch: the generated patch to test.

    Returns:
        - passed: True if all tests passed, False otherwise.
        - log_text: log text from the evaluation.
    """

    random_string = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    model_name_or_path = f"autocoderover_intermediate_{random_string}"

    test_type = MAP_REPO_TO_TEST_FRAMEWORK[repo]

    # get_test_directives requires a dict, but only these fields are used
    instance_to_get_test_directive = {
        "repo": repo,
        "test_patch": developer_test_patch,
    }
    test_directives = get_test_directives(instance_to_get_test_directive)
    test_cmd = f"{test_type} {' '.join(test_directives)}"

    # use no-op test_patch, since we are running pre-existing tests
    noop_test_patch = NOOP_PATCH

    instance_for_running_test = {
        "repo": repo,
        "version": version,
        "base_commit": base_commit,
        "instance_id": instance_id,
        "model_name_or_path": model_name_or_path,
        "model_patch": generated_prog_patch,
        "test_patch": noop_test_patch,
        "test_directives": test_directives,
        "test_cmd": test_cmd,
    }

    # arguments related to swe-bench-docker
    namespace = "autocoderover"
    log_dir = Path("/tmp", f"swe_bench_docker_logs_{instance_id}")
    create_fresh_dir(log_dir)
    os.chmod(log_dir, 0o777)  # make sure there is permission issue when writing to it

    timeout = 900
    log_suffix = ""

    coro = asyncio.wait_for(
        run_docker_evaluation(
            instance_for_running_test, namespace, str(log_dir), timeout, log_suffix
        ),
        timeout=timeout + 10,
    )
    asyncio.run(coro)

    log_fname = Path(log_dir) / f"{instance_id}.{model_name_or_path}.eval.log"
    if not log_fname.exists():
        # if there is no evaluation log, something was wrong during docker eval
        # TODO: perhaps this should be a special case instead of error?
        return False, ""

    log_text = log_fname.read_text()
    log_lines = log_text.splitlines()
    log_lines = [line for line in log_lines if line.startswith(">>>>")]

    passed = ">>>>> All Tests Passed" in log_text

    shutil.rmtree(str(log_dir))
    return passed, log_text
