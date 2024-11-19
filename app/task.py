from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from shutil import copy2
from subprocess import DEVNULL, CompletedProcess
from tempfile import NamedTemporaryFile, TemporaryDirectory, mkstemp

from loguru import logger

try:
    from swebench.metrics.constants import TestStatus
    from swebench.metrics.getters import APPLY_PATCH_PASS

    # from swebench.metrics import log_parsers
    from swebench.metrics.log_parsers import MAP_REPO_TO_PARSER
except ImportError:
    pass

import app.utils as apputils
from app import config, log
from app import utils as app_utils
from app.api.eval_helper import (
    ResolvedStatus,
    get_eval_report,
    get_logs_eval,
    get_resolution_status,
)

try:
    from app.api.swe_bench_docker_validation import run_pre_existing_tests
except ImportError:
    pass

from app.data_structures import ReproResult
from app.log import log_and_print
from app.utils import run_script_in_conda


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
    def validate(self, patch_content: str) -> tuple[bool, str, str, str]:
        """
        Returns:
            - Whether this patch has made the test suite pass.
            - Error message when running the test suite.
            - Path of written log file
        """
        raise NotImplementedError

    @contextmanager
    def apply_patch(self, patch_content: str) -> Generator[None, None, None]:
        try:
            with NamedTemporaryFile(buffering=0, suffix=".diff") as f:
                f.write(patch_content.encode())
                apply_cmd = ["git", "apply", f.name]
                subprocess.run(
                    apply_cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.project_path,
                    check=True,
                )

            yield
        finally:
            with apputils.cd(self.project_path):
                apputils.repo_clean_changes()

    # TODO: remove this
    def clean_active_project_changes(self) -> None:
        with apputils.cd(self.project_path):
            apputils.repo_clean_changes()

    def execute_reproducer(
        self, test_content: str, patch_content: str | None = None
    ) -> ReproResult:
        raise NotImplementedError


@dataclass(kw_only=True)
class SweTask(Task):
    task_id: str
    problem_statement: str
    repo_path: str
    commit: str
    env_name: str
    repo_name: str
    repo_version: str
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
            config.enable_sbfl
            or config.enable_validation
            or config.only_save_sbfl_result
            or config.reproduce_and_review
        )
        if do_install:
            self._do_install()

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
                task.install_cmd,
                task.env_name,
                capture_output=True,
                text=True,
            )
            if cp.returncode != 0:
                log_and_print(cp.stderr)
                raise RuntimeError(f"Command {task.install_cmd} failed.")
            # (3) xmlrunner for our custom run_test; coverage required for fault localization
            other_install_cmd = (
                "python -m pip install xmlrunner coverage pytest pytest-cov decorator"
            )
            cp = apputils.run_string_cmd_in_conda(
                other_install_cmd,
                task.env_name,
                capture_output=True,
                text=True,
            )
            if cp.returncode != 0:
                log_and_print(cp.stderr)
                raise RuntimeError(f"Command {other_install_cmd} failed.")

    def validate(self, patch_content: str) -> tuple[bool, str, str, str]:
        with self.apply_patch(patch_content):
            # NOTE: when doing validation with SWE-bench-docker, this apply_patch is
            # unnecessary since there is another copy of the project code inside the container.
            # However, we just leave it here since validation may happen on host machine as well.
            log_and_print("[Validation] Applied patch. Going to run test suite.")

            _, log_file = mkstemp(suffix=".log", prefix="pyval-", text=True)
            tests_passed, msg, orig_log_file = (
                self._run_test_suite_for_regression_docker(patch_content, log_file)
            )

        log_and_print(
            f"[Validation] Finishing. Result is {tests_passed}. Message: {msg}",
        )

        return tests_passed, msg, log_file, orig_log_file

    def _run_test_suite_for_regression_docker(
        self, patch_content: str, log_file: str
    ) -> tuple[bool, str, str]:
        # TODO: do not return original log file
        noop_patch = self.make_noop_patch(self.project_path)
        orig_status_map, orig_eval_log_content = self._run_test_suite_docker(noop_patch)
        _, orig_log_file = mkstemp(suffix=".log", prefix="pyval-", text=True)
        Path(orig_log_file).write_text(orig_eval_log_content)

        logger.info("Start running regression tests")

        status_map, eval_log_content = self._run_test_suite_docker(patch_content)
        Path(log_file).write_text(eval_log_content)

        bad_status = (TestStatus.FAILED.value, TestStatus.ERROR.value)
        failures = {test for test, status in status_map.items() if status in bad_status}
        orig_failures = {
            test for test, status in orig_status_map.items() if status in bad_status
        }

        have_additional_failures = bool(failures - orig_failures)

        logger.info(
            "Regression tests {}", "failed" if have_additional_failures else "passed"
        )

        if have_additional_failures:
            msg = "The patch caused some pre-existing tests to fail."
        else:
            msg = "The patch passed pre-existing tests."

        return not have_additional_failures, msg, orig_log_file

    @classmethod
    def make_noop_patch(cls, project_path: str) -> str:
        with TemporaryDirectory() as d:

            def run_command(cmd: list[str]) -> None:
                subprocess.run(cmd, cwd=d, check=True, stdout=DEVNULL, stderr=DEVNULL)

            gitignore_file = Path(project_path, ".gitignore")
            copy2(gitignore_file, d)

            run_command(["git", "init"])

            run_command(["git", "add", "."])
            run_command(["git", "commit", "-m", "first commit"])

            gitignore_content = gitignore_file.read_text()
            new_gitignore_content = f"{gitignore_content}\n"
            Path(d, ".gitignore").write_text(new_gitignore_content)

            run_command(["git", "add", "."])
            run_command(["git", "commit", "-m", "append new line to gitignore"])

            cp = subprocess.run(
                ["git", "diff", "HEAD~", "HEAD"],
                cwd=d,
                check=True,
                text=True,
                capture_output=True,
            )

            return cp.stdout

    def _run_test_suite_docker(self, patch_content) -> tuple[dict, str]:
        cache = getattr(self, "_regression_cache", {})

        if patch_content in cache:
            logger.debug("regression cache hit")
            return cache[patch_content]

        _, eval_log_content = run_pre_existing_tests(
            self.repo_name,
            self.repo_version,
            self.task_id,
            self.commit,
            self.test_patch,
            patch_content,
        )

        result = self.parse_eval_log(self.repo_name, eval_log_content), eval_log_content

        cache[patch_content] = result
        self._regression_cache = cache

        return result

    @classmethod
    def parse_eval_log(cls, repo: str, content: str) -> dict:
        parser = MAP_REPO_TO_PARSER[repo]
        content = content.split(f"{APPLY_PATCH_PASS} (pred)")[-1]
        return parser(content)

    def _run_test_suite_for_correctness_lcoal(self, log_file: str) -> tuple[bool, str]:
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
                    timeout=config.test_exec_timeout,
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
                        f"{TESTS_TIMEOUT} after {config.test_exec_timeout} seconds\n"
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

    def _run_reproducer(self, reproducer_file: str | PathLike) -> CompletedProcess:
        """
        Helper method for running reproducer.
        """
        return run_script_in_conda(
            [str(reproducer_file)],
            self.env_name,
            cwd=self.project_path,
            text=True,
            capture_output=True,
        )

    def _summarize_cp(self, cp: CompletedProcess) -> dict:
        """
        Helper method for running reproducer.
        """
        return {
            "passed": cp.returncode == 0,
            "raised_assertion_error": "AssertionError" in cp.stderr,
        }

    def execute_reproducer(
        self, test_content: str, patch_content: str | None = None
    ) -> ReproResult:
        cm = nullcontext() if patch_content is None else self.apply_patch(patch_content)

        with cm:
            with NamedTemporaryFile(
                buffering=0, prefix="reproducer-", suffix=".py"
            ) as f:
                f.write(test_content.encode())
                try:
                    cp = run_script_in_conda(
                        [f.name],
                        self.env_name,
                        cwd=self.project_path,
                        text=True,
                        capture_output=True,
                        timeout=120,  # 2 min for reproducer should be enough
                    )
                    cp_stdout = cp.stdout
                    cp_stderr = cp.stderr
                    cp_returncode = cp.returncode
                except subprocess.TimeoutExpired:
                    cp_stdout = ""
                    cp_stderr = "Test execution timeout."
                    cp_returncode = -1

        # stderr can be very long; truncate it so we dont exceed model limit
        stderr_result = str(cp_stderr)
        stderr_lines = stderr_result.splitlines()
        if len(stderr_lines) > 100:
            # take first 50 and last 50 lines
            stderr_result = "\n".join(stderr_lines[:50] + ["..."] + stderr_lines[-50:])
        return ReproResult(cp_stdout, stderr_result, cp_returncode)

    def evaluate_reproducer(
        self,
        reproducer_file: str | PathLike,
        developer_patch_file: str | PathLike,
        report_dir: str | PathLike,
    ) -> None:
        """Run the reproducer with and without developer patch and dump reports.

        Assume that the project has already been set up with setup_project().
        """

        buggy_cp = self._run_reproducer(reproducer_file)

        subprocess.run(
            ["git", "apply", developer_patch_file], cwd=self.project_path, check=True
        )
        try:
            fixed_cp = self._run_reproducer(reproducer_file)
        finally:
            subprocess.run(
                ["git", "apply", "-R", developer_patch_file],
                cwd=self.project_path,
                check=True,
            )

        Path(report_dir, "buggy.out").write_text(buggy_cp.stdout)
        Path(report_dir, "buggy.err").write_text(buggy_cp.stderr)
        Path(report_dir, "fixed.out").write_text(fixed_cp.stdout)
        Path(report_dir, "fixed.err").write_text(fixed_cp.stderr)

        buggy_summary = self._summarize_cp(buggy_cp)
        fixed_summary = self._summarize_cp(fixed_cp)
        summary = {
            "buggy_summary": buggy_summary,
            "fixed_summary": fixed_summary,
            "reproduced_by_returncode": (
                buggy_cp.returncode != 0 and fixed_cp.returncode == 0
            ),
            "reproduced_by_assertion_error": (
                buggy_summary["raised_assertion_error"]
                and not fixed_summary["raised_assertion_error"]
            ),
        }
        Path(report_dir, "summary.json").write_text(json.dumps(summary, indent=4))


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

    def validate(self, patch_content: str) -> tuple[bool, str, str, str]:
        raise NotImplementedError("Cannot do validation for live issues for now")
