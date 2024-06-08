from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os.path import join as pjoin
from tempfile import mkstemp

import app.utils as apputils
from app import globals, log
from app import utils as app_utils
from app.api.eval_helper import (
    ResolvedStatus,
    get_eval_report,
    get_logs_eval,
    get_resolution_status,
)
from app.log import log_and_print


class Task(ABC):
    @property
    @abstractmethod
    def project_path(self) -> str:
        raise NotImplementedError("abstract method")

    @abstractmethod
    def get_issue_statement(self) -> str:
        raise NotImplementedError("abstract method")

    @abstractmethod
    def setup_project(self) -> None:
        """Set up the project before starting to resolve the task."""
        raise NotImplementedError("abstract method")

    @abstractmethod
    def reset_project(self) -> None:
        """Reset project to initial state."""
        raise NotImplementedError("abstract method")

    @abstractmethod
    def validate(self, patch_file: str) -> tuple[bool, str, str]:
        """
        Returns:
            - Whether this patch has made the test suite pass.
            - Error message when running the test suite.
            - Path of written log file
        """
        raise NotImplementedError


@dataclass(kw_only=True)
class SweTask(Task):
    task_id: str
    problem_statement: str
    repo_path: str
    commit: str
    env_name: str
    repo_name: str
    pre_install_cmds: list[str]
    install_cmd: str
    test_cmd: str
    test_patch: str
    testcases_passing: list[str]
    testcases_failing: list[str]

    @property
    def project_path(self) -> str:
        return self.repo_path

    @project_path.setter
    def project_path(self, value: str) -> None:
        self.repo_path = value

    def get_issue_statement(self) -> str:
        return self.problem_statement

    def setup_project(self) -> None:
        # get the correct version of the project and commit-specific pip install
        task = self
        with apputils.cd(task.project_path):
            apputils.repo_reset_and_clean_checkout(task.commit)

        # Install task-specific dependencies
        do_install = (
            globals.enable_sbfl
            or globals.enable_validation
            or globals.only_save_sbfl_result
        )
        if do_install:
            self._do_install()

        # apply the test modifications to this task
        self._apply_test_patch()

        # commit the current changes, so that resetting later do not erase them
        with apputils.cd(task.project_path):
            apputils.repo_commit_current_changes()

    def reset_project(self) -> None:
        with apputils.cd(self.repo_path):
            apputils.repo_reset_and_clean_checkout(self.commit)

    def _do_install(self):
        """Do left-over install commands after setting up.
        The commands being run here are 'pre_install' and 'install' defined in
        harness/constants.py file in SWE-bench.
        """
        task = self
        if not task.pre_install_cmds and not task.install_cmd:
            # no command for installation, skip
            return
        with apputils.cd(task.project_path):
            # (0) For matplotlib, qhull tarball download
            # just fails, so we need to pre-install the system version and use it
            if "matplotlib" in task.task_id:
                with open("mplsetup.cfg", "w") as f:
                    f.write("[libs]\nsystem_qhull = true")
            # (1) pre-install
            for cmd in task.pre_install_cmds:
                cp = apputils.run_string_cmd_in_conda(
                    cmd, task.env_name, capture_output=True, text=True
                )
                if cp.returncode != 0:
                    log_and_print(cp.stderr)
                    raise RuntimeError(f"Command {cmd} failed.")

            # (2) install
            cp = apputils.run_string_cmd_in_conda(
                task.install_cmd, task.env_name, capture_output=True, text=True
            )
            if cp.returncode != 0:
                log_and_print(cp.stderr)
                raise RuntimeError(f"Command {task.install_cmd} failed.")
            # (3) xmlrunner for our custom run_test; coverage required for fault localization
            other_install_cmd = (
                "python -m pip install xmlrunner coverage pytest pytest-cov"
            )
            cp = apputils.run_string_cmd_in_conda(
                other_install_cmd, task.env_name, capture_output=True, text=True
            )
            if cp.returncode != 0:
                log_and_print(cp.stderr)
                raise RuntimeError(f"Command {other_install_cmd} failed.")

    def _apply_test_patch(self) -> None:
        """
        Apply the patch to testcases, as supplied by the benchmark.
        This step brings in all the new tests and testcase modifications.
        """
        task = self

        if not task.test_patch:
            # no patches to tests are found
            return
        with apputils.cd(task.project_path):
            # (1) write test_patch to a temp file
            test_patch_path = pjoin(task.project_path, "swe_bench_tests.patch")
            with open(test_patch_path, "w") as f:
                f.write(task.test_patch)
            # (2) apply these patches
            # FIXME: check for failure here
            apply_cmd = ["git", "apply", test_patch_path]
            cp = apputils.run_command(apply_cmd, capture_output=True, text=True)
            if cp.returncode != 0:
                log_and_print(cp.stderr)
                raise RuntimeError(f"Command {apply_cmd} failed.")
            # (3) remove the temp file, which is not so important
            os.remove(test_patch_path)

    def validate(self, patch_file: str) -> tuple[bool, str, str]:
        # (1) apply the patch to source code
        with app_utils.cd(self.project_path):
            apply_cmd = ["git", "apply", patch_file]
            cp = app_utils.run_command(apply_cmd, capture_output=False, text=True)
            if cp.returncode != 0:
                # patch application failed
                raise RuntimeError(f"Error applying patch: {cp.stderr}")

        # (2) run the modified program against the test suite
        log_and_print("[Validation] Applied patch. Going to run test suite.")

        _, log_file = mkstemp(suffix=".log", prefix="pyval-", text=True)
        tests_passed, msg = self._run_test_suite_for_correctness(log_file)

        # (3) revert the patch to source code
        with app_utils.cd(self.project_path):
            app_utils.repo_clean_changes()

        log_and_print(
            f"[Validation] Finishing. Result is {tests_passed}. Message: {msg}."
        )
        return tests_passed, msg, log_file

    def _run_test_suite_for_correctness(self, log_file: str) -> tuple[bool, str]:
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

        error_message = ""

        # Run test suite and check whether passing tests still pass and
        # failing tests become passing.
        # This part is heavily referenced from SWE-bench code
        with app_utils.cd(self.project_path):
            try:
                cp = app_utils.run_string_cmd_in_conda(
                    self.test_cmd,
                    self.env_name,
                    timeout=globals.test_exec_timeout,
                    capture_output=True,
                    text=True,
                )
                with open(log_file, "w") as f:
                    f.write("Output:\n")
                    f.write(cp.stdout)
                    f.write(cp.stderr)
                    if cp.returncode != 0:
                        f.write(f"\n{TESTS_FAILED}\n")
                    else:
                        f.write(f"\n{TESTS_PASSED}\n")
            except subprocess.TimeoutExpired:
                with open(log_file, "a") as f:
                    f.write(
                        f"{TESTS_TIMEOUT} after {globals.test_exec_timeout} seconds\n"
                    )
            except Exception as e:

                # Test command run failed. This does not necessarily mean that tests
                # failed. However, we regard this as failure in execution.

                with open(log_file, "a") as f:
                    f.write(f"{TESTS_ERROR}: {e}")

        # Now test log has been written; process it
        eval_status, parse_ok = get_logs_eval(self.repo_name, log_file)
        log.log_and_print(f"[Run test-suite] Result of parsing test log: {parse_ok}")
        log.log_and_print(f"[Run test-suite] Eval status: {eval_status}")

        if not parse_ok:
            # log file says test execution has error
            with open(log_file) as f:
                error_message = f.read()
            return False, error_message

        eval_ref = {
            "FAIL_TO_PASS": self.testcases_failing,
            "PASS_TO_PASS": self.testcases_passing,
        }
        eval_result = get_eval_report(eval_status, eval_ref)
        log.log_and_print(f"[Run test-suite] Eval result: {eval_result}")

        resolution_status = get_resolution_status(eval_result)
        log.log_and_print(f"[Run test-suite] Resolution status: {resolution_status}")
        if resolution_status == ResolvedStatus.FULL:
            log.log_and_print("[Run test-suite] Returning True since all resolved.")
            return True, ""

        else:
            # FIXME: The current failure message is simple; maybe can add failure reasons to it
            log.log_and_print(
                "[Run test-suite] Returning False since some tests failed."
            )
            error_message = "Some tests have failed."
            return False, error_message


@dataclass(kw_only=True)
class PlainTask(Task):
    """
    Tasks that only contain a codebase and an issue descripion (no test suite).
    """

    commit_hash: str
    local_path: str
    problem_statement: str

    @property
    def project_path(self) -> str:
        return self.local_path

    def setup_project(self) -> None:
        with apputils.cd(self.project_path):
            apputils.repo_reset_and_clean_checkout(self.commit_hash)

    def reset_project(self) -> None:
        with apputils.cd(self.project_path):
            apputils.repo_reset_and_clean_checkout(self.commit_hash)

    def get_issue_statement(self) -> str:
        return self.problem_statement

    def validate(self, patch_file: str) -> tuple[bool, str, str]:
        raise NotImplementedError("Cannot do validation for live issues for now")
