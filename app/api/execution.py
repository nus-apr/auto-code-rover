"""
Perform validation of a patch, on a given task instance, against the available test-suite.
"""

import os
import shutil
from os import PathLike
from os.path import join as pjoin
from pprint import pprint
from typing import Tuple
import subprocess

from app import log
from app import utils as app_utils
from app.api.eval_helper import (
    ResolvedStatus,
    get_eval_report,
    get_logs_eval,
    get_resolution_status,
)
from app import globals



def run_test_suite_for_correctness(
    repo_name: str,
    output_dir: str,
    project_path: str,
    test_cmd: str,
    env_name: str,
    testcases_passing,
    testcases_failing,
    run_test_suite_log_file,
    logger,
) -> Tuple[bool, str]:
    """
    Run the developer test suite, and record pass/fail results.
    The goal is to check correctness of a patched program, while returning
    the error message from the failed tests.

    Returns:
        - True if all tests passed; False otherwise.
        - A message associated with the failure reason. Empty string if all tests passed.
    """
    TESTS_ERROR = ">>>>> Tests Errored"
    TESTS_FAILED = ">>>>> Some Tests Failed"
    TESTS_PASSED = ">>>>> All Tests Passed"
    TESTS_TIMEOUT = ">>>>> Tests Timed Out"

    if os.path.exists(run_test_suite_log_file):
        os.remove(run_test_suite_log_file)

    error_message = ""

    ### Run test suite and check whether passing tests still pass and failing tests become passing
    ### This part is heavily referenced from SWE-bench code
    with app_utils.cd(project_path):
        try:
            cp = app_utils.run_string_cmd_in_conda(
                logger,
                test_cmd,
                env_name,
                timeout=globals.test_exec_timeout,
                capture_output=True,
                text=True,
            )
            with open(run_test_suite_log_file, "a") as f:
                f.write("Output:\n")
                f.write(cp.stdout)
                f.write(cp.stderr)
                if cp.returncode != 0:
                    f.write(f"\n{TESTS_FAILED}\n")
                else:
                    f.write(f"\n{TESTS_PASSED}\n")
        except subprocess.TimeoutExpired:
            with open(run_test_suite_log_file, "a") as f:
                f.write(f"{TESTS_TIMEOUT} after {globals.test_exec_timeout} seconds\n")
        except Exception as e:
            # test command run failed
            # this does not necessarily mean that tests failed - however, we regard this as failure
            # in execution
            with open(run_test_suite_log_file, "a") as f:
                f.write(f"{TESTS_ERROR}: {e}")

    # Now test log has been written; process it
    eval_status, parse_ok = get_logs_eval(repo_name, run_test_suite_log_file)
    log.log_and_print(
        logger, f"[Run test-suite] Result of parsing test log: {parse_ok}"
    )
    log.log_and_print(logger, f"[Run test-suite] Eval status: {eval_status}")

    if not parse_ok:
        # log file says test execution has error
        with open(run_test_suite_log_file, "r") as f:
            error_message = f.read()
        return False, error_message

    eval_ref = {"FAIL_TO_PASS": testcases_failing, "PASS_TO_PASS": testcases_passing}
    eval_result = get_eval_report(eval_status, eval_ref)
    log.log_and_print(logger, f"[Run test-suite] Eval result: {eval_result}")

    resolution_status = get_resolution_status(eval_result)
    log.log_and_print(
        logger, f"[Run test-suite] Resolution status: {resolution_status}"
    )
    if resolution_status == ResolvedStatus.FULL:
        log.log_and_print(
            logger, f"[Run test-suite] Returning True since all resolved."
        )
        return True, ""

    else:
        # FIXME: The current failure message is simple; maybe can add failure reasons to it
        log.log_and_print(
            logger, f"[Run test-suite] Returning False since some tests failed."
        )
        error_message = "Some tests have failed."
        return False, error_message
