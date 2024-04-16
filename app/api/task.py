from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from configparser import ConfigParser
from dataclasses import dataclass
from os import PathLike
from os.path import join as pjoin
from pathlib import Path
from subprocess import PIPE, STDOUT, TimeoutExpired
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
    def setup_project(self) -> None:
        """Set up the project before starting to resolve the task."""
        raise NotImplementedError("abstract method")

    @abstractmethod
    def run_developer_test_suite(self) -> tuple[str, str]:
        """
        Run the relevant parts of developer test suite.
        Record coverage information for each test while running them.

        Returns:
            - The produced coverage file for the test suite.
              Empty string if no coverage file is produced.
            - Log file.
        """
        raise NotImplementedError

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
class PythonTask(Task):
    task_id: str
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
                "python -m pip install xmlrunner coverage pytest pytest-cov"
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

    @classmethod
    def _specify_dynamic_context(cls, coveragerc: str | PathLike) -> None:
        # check whether there is already a .coveragerc file
        if not os.path.exists(coveragerc):
            with open(coveragerc, "w") as f:
                f.write("[run]\ndynamic_context = test_function")
        else:
            # add the dynamic context setting to it
            with open(coveragerc) as f:
                lines = f.readlines()
            updated_lines = []
            added_context_line = False
            for line in lines:
                updated_lines.append(line)
                if line.startswith("[run]"):
                    added_context_line = True
                    updated_lines.append("dynamic_context = test_function\n")
            # if there is no [run] section in old file, our line
            # has not been added yet
            if not added_context_line:
                updated_lines.append("[run]\n")
                updated_lines.append("dynamic_context = test_function\n")
            with open(coveragerc, "w") as f:
                f.writelines(updated_lines)

    @classmethod
    def _omit_coverage_in_file(
        cls, coveragerc: str | PathLike, omitted: list[str]
    ) -> None:
        value = "".join(f"\n{file}" for file in omitted)
        value = "\n# added by auto-code-rover" + value

        config = ConfigParser()

        if os.path.exists(coveragerc):
            config.read(coveragerc)

        if not config.has_section("run"):
            config.add_section("run")

        config["run"]["omit"] = value + config["run"].get("omit", "")

        with open(coveragerc, "w") as f:
            config.write(f)

    @classmethod
    def _add_pytest_cov_to_tox(cls, tox_ini: str | PathLike):
        assert os.path.exists(tox_ini)

        config = ConfigParser()
        config.read(tox_ini)

        assert config.has_section("testenv")
        config["testenv"]["deps"] = (
            config["testenv"].get("deps", "") + "\npytest\npytest-cov"
        )

        assert config.has_option("testenv", "commands")
        config["testenv"]["commands"] = config["testenv"]["commands"].replace(
            "pytest", "pytest --cov --cov-context=test"
        )

        with open(tox_ini, "w") as f:
            config.write(f)

    def run_developer_test_suite(self) -> tuple[str, str]:
        if "django" in self.task_id:
            return self._run_developer_test_suite_django()
        else:
            return self._run_developer_test_suite_others()

    def _run_developer_test_suite_django(self) -> tuple[str, str]:
        """
        Since django does not use pytest as the testing framework, we use another procedure.

        Returns:
            - The produced coverage file for the test suite. Empty string if the file is not produced.
        """
        task = self

        tests_dir = pjoin(task.project_path, "tests")
        assert os.path.isdir(tests_dir)

        execution_dir = tests_dir
        with apputils.cd(execution_dir):
            # (1) since we want to use coverage.py with dynamic context, create config first
            cov_config = pjoin(execution_dir, ".coveragerc")
            PythonTask._specify_dynamic_context(cov_config)

            # (2) actually run the tests to produce coverage output
            orig_cmd_parts = task.test_cmd.split(" ")
            assert (
                orig_cmd_parts[0] == "./tests/runtests.py"
            ), f"Test command does not start with ./tests/runtests.py: {task.test_cmd}"
            test_cmd = (
                "python -m coverage run "
                + os.path.basename(orig_cmd_parts[0])
                + " --parallel 1 "
                + " ".join(orig_cmd_parts[1:])
            )

            _, log_file = mkstemp(suffix=".log", prefix="run_developer_tests")

            try:
                cp = apputils.run_string_cmd_in_conda(
                    test_cmd,
                    task.env_name,
                    stdout=PIPE,
                    stderr=STDOUT,
                    text=True,
                    timeout=globals.test_exec_timeout,
                )
                Path(log_file).write_text(cp.stdout)
            except TimeoutExpired:
                log.log_and_print(
                    "Timeout expired while running the test suite.",
                )
                return "", log_file

            # (3) check whether the coverage file is there
            cov_file = pjoin(execution_dir, ".coverage")
            if not os.path.exists(cov_file):
                log.log_and_print(
                    "Coverage file is not produced after running the test suite.",
                )
                return "", log_file
            return cov_file, log_file

    def _run_developer_test_suite_others(self) -> tuple[str, str]:
        """
        Run the relevant parts of developer test suite.
        Record coverage information for each test while running them.

        Returns:
            - The produced coverage file for the test suite. Empty string if no coverage file is produced.
            - Log file.
        """
        task = self

        with apputils.cd(task.project_path):
            # (1) run the tests to produce coverage output
            if task.test_cmd.startswith("pytest"):
                # Use pytest-cov to properly get parametrized test names
                args = task.test_cmd.removeprefix("pytest")
                test_cmd = f"python -m pytest --cov --cov-context=test {args}"
            elif "bin/test" in task.test_cmd:
                assert task.task_id.startswith("sympy__")

                # Sympy tests are compatible with PyTest. Only issue is that more tests
                # can berun by PyTest than if Sympy testing is used. However, we match
                # context names with PASS_TO_PASS and FAIL_TO_PASS later, so it's fine.

                test_files = [x for x in task.test_cmd.split() if x.endswith(".py")]
                assert (
                    test_files
                ), f"Failed to find test files in command: {task.test_cmd}"

                cov_config = pjoin(task.project_path, ".coveragerc")

                PythonTask._omit_coverage_in_file(cov_config, test_files)

                test_cmd = (
                    "python -m pytest --cov --cov-context=test --no-header"
                    f" -rA --tb=no -p no:cacheprovider {' '.join(test_files)}"
                )
            elif task.test_cmd.startswith("tox "):
                tox_ini = pjoin(task.project_path, "tox.ini")
                assert os.path.exists(
                    tox_ini
                ), f"tox.ini not found in {task.project_path}"

                PythonTask._add_pytest_cov_to_tox(tox_ini)

                test_cmd = f"python -m {task.test_cmd}"
            else:
                cov_config = pjoin(task.project_path, ".coveragerc")
                PythonTask._specify_dynamic_context(cov_config)
                test_cmd = f"python -m coverage run {task.test_cmd}"

            _, log_file = mkstemp(suffix=".log", prefix="run_developer_tests")
            try:
                cp = apputils.run_string_cmd_in_conda(
                    test_cmd,
                    task.env_name,
                    stdout=PIPE,
                    stderr=STDOUT,
                    text=True,
                    timeout=globals.test_exec_timeout,
                )
                Path(log_file).write_text(cp.stdout)
                # Path(self.output_dir, "run_developer_tests.log").write_text(cp.stdout)
            except TimeoutExpired:
                log.log_and_print(
                    "Timeout expired while running the test suite.",
                )
                return "", log_file

            # (2) check whether the coverage file is there
            cov_file = pjoin(task.project_path, ".coverage")
            if not os.path.exists(cov_file):
                # sometimes cov_file can have extensions such as:
                # .coverage.TSS.852665.XmCvBpdx
                # we need to find the correct file
                all_files = os.listdir(task.project_path)
                for f in all_files:
                    if f.startswith(".coverage.TSS"):
                        cov_file = pjoin(task.project_path, f)
                        break
                # now check again
                if not os.path.exists(cov_file):
                    log.log_and_print(
                        "Coverage file is not produced after running the test suite.",
                    )
                    return "", log_file
            return cov_file, log_file

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
            f"[Validation] Finishing. Result is {tests_passed}. Message: {msg}.",
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
