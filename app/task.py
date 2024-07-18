from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
from abc import ABC, abstractmethod
from asyncio.subprocess import Process
from configparser import ConfigParser
from dataclasses import dataclass
from os import PathLike, chmod, scandir
from os.path import join
from os.path import join as pjoin
from pathlib import Path
from subprocess import PIPE
from tempfile import mkdtemp, mkstemp

from icecream import ic
from swebench.metrics.constants import TestStatus
from swebench.metrics.getters import APPLY_PATCH_PASS
from swebench.metrics.log_parsers import MAP_REPO_TO_PARSER
from swebench_docker.constants import MAP_REPO_TO_TEST_FRAMEWORK, MAP_VERSION_TO_INSTALL
from swebench_docker.utils import get_test_directives

import app.utils as apputils
from app import globals, log
from app import utils as app_utils
from app.api.eval_helper import (
    ResolvedStatus,
    get_eval_report,
    get_logs_eval,
    get_resolution_status,
)
from app.data_structures import NoCoverageData
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
    repo_version: str
    pre_install_cmds: list[str]
    install_cmd: str
    test_cmd: str
    test_patch: str
    testcases_passing: list[str]
    testcases_failing: list[str]

    NOOP_TEST_PATCH = (
        "diff --git a/empty.file.test_patch.ignore b/empty.file.test_patch.ignore\n"
        "new file mode 100644\n"
        "index 0000000..e69de29\n"
    )

    NOOP_PROGRAM_PATCH = (
        "diff --git a/empty.file.program_patch.ignore b/empty.file.program_patch.ignore\n"
        "new file mode 100644\n"
        "index 0000000..e69de29\n"
    )

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
        _, log_file = asyncio.run(
            SweDocker.run_regression_docker(
                self, patch_file, self.test_patch, collect_coverage=False
            )
        )

        log_content = Path(log_file).read_text()
        results = SweDocker.parse_eval_log(self.repo_name, log_content)
        tests_passed = all(
            result == TestStatus.PASSED.value for result in results.values()
        )

        if tests_passed:
            msg = ""
        else:
            msg = "Some tests have failed."

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


class SweDocker:
    """
    Contains all functions that run validation through SWE-bench-docker containers.
    See SWE-bench-docker here: https://github.com/aorwall/SWE-bench-docker

    Code here are taken from / inspired by https://github.com/paul-gauthier/aider-swe-bench,
    and code in this file is distributed under Apache License 2.0.
    """

    @classmethod
    async def run_regression_docker(
        cls,
        task: SweTask,
        patch_content: str | None = None,
        test_content: str | None = None,
        collect_coverage: bool = True,
        timeout: int = 900,
        namespace: str = "autocoderover",
        log_suffix: str = "",
    ) -> tuple[str, str]:
        """Run regression tests in SWE-bench docker and get coverage.
        Returns:
            coverage file path, test log file path
        """
        patch_content = patch_content or SweTask.NOOP_PROGRAM_PATCH
        test_content = test_content or SweTask.NOOP_TEST_PATCH
        instance = cls.make_swe_bench_docker_instance(task, patch_content, test_content)

        instance_id = instance["instance_id"]

        log_dir = mkdtemp(prefix=f"swe-bench-docker-log-{instance_id}-")
        chmod(log_dir, 0o777)

        repo = instance["repo"]
        version = instance["version"]
        specifications = MAP_VERSION_TO_INSTALL[repo][version]
        if (
            "packages" in specifications
            and specifications["packages"] == "environment.yml"
        ):
            container_log_dir = "/home/swe-bench/logs"
        else:
            container_log_dir = "/opt/logs"

        docker_opts = [
            "-it",
            "-d",
            # "-u",
            # "root",
            "--entrypoint",
            "/bin/bash",
            "--rm",
            "-e",
            f"LOG_DIR={container_log_dir}",
            "-e",
            f"TIMEOUT={timeout}",
            "-e",
            f"LOG_SUFFIX={log_suffix}",
            "-v",
            f"{log_dir}:{container_log_dir}",
        ]

        swebench_docker_fork_dir = os.environ.get("SWEBENCH_DOCKER_FORK_DIR")
        if swebench_docker_fork_dir:
            raise NotImplementedError(
                "Instance can only be passed via env var right now"
            )

        container_id = await cls.start_swe_bench_docker_container(
            repo,
            version,
            instance_id,
            namespace,
            docker_opts=docker_opts,
        )
        ic(container_id)

        try:
            image_name = cls.get_swe_bench_docker_image_name(
                repo, version, instance_id, namespace
            )
            cmd_s = f"docker image inspect {image_name}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            stdout = await check_process(process)
            image_config = json.loads(stdout)[0]["Config"]
            workdir = image_config["WorkingDir"]
            entrypoint = image_config["Entrypoint"][0]

            image_env = image_config["Env"]
            if "IMAGE_TYPE=conda" in image_env:
                for env in image_env:
                    if env.startswith("TESTBED_NAME="):
                        conda_env = env.partition("=")[-1]
                        container_python = f"conda run -n {conda_env} python"
                        break
                else:
                    raise RuntimeError("Could not find conda env name")
            elif "IMAGE_TYPE=pyenv" in image_env:
                container_python = "python"
            else:
                assert False, f"Unknown image type: {image_env}"
            ic(container_python)

            cmd_s = f"docker exec -w {workdir} {container_id} {container_python} -m pip install coverage pytest pytest-cov"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            stdout = await check_process(process)

            cmd_s = f"docker exec {container_id} printenv REPO_DIR"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            err_msg = f"failed to get REPO_DIR env var in container {container_id} using cmd: {cmd_s}"
            stdout = await check_process(process, err_msg)
            container_repo_dir = stdout.strip()
            ic(container_repo_dir)

            actual_cmd_s = (
                f"git config --global --add safe.directory {container_repo_dir}"
            )
            cmd_s = f"docker exec -w {container_repo_dir} {container_id} {actual_cmd_s}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            await check_process(process, err_msg=cmd_s)

            actual_cmd_s = f"git -c advice.detachedHead=false checkout {task.commit}"
            cmd_s = f"docker exec -w {container_repo_dir} {container_id} {actual_cmd_s}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            await check_process(process, err_msg=cmd_s)

            if pre_test_cmds := specifications.get("pre_test"):
                for cmd_pre_install in pre_test_cmds:
                    actual_cmd_s = f"{container_python} {cmd_pre_install}"
                    cmd_s = f"docker exec -w {container_repo_dir} {container_id} {actual_cmd_s}"
                    process = await asyncio.create_subprocess_shell(
                        cmd_s, stdout=PIPE, stderr=PIPE
                    )
                    await check_process(process, err_msg=cmd_s)

            if task.repo_name == "django/django":
                test_cmd_workdir = f"{container_repo_dir}/tests"
            else:
                test_cmd_workdir = container_repo_dir

            test_cmd = await cls.make_test_cmd_with_cov(
                instance, container_id, test_cmd_workdir, python_path=container_python
            )
            instance["test_cmd"] = test_cmd
            ic(test_cmd)

            if swebench_docker_fork_dir:
                raise NotImplementedError
            else:
                instance_b64 = base64.b64encode(
                    json.dumps(instance).encode("utf-8")
                ).decode("utf-8")

                cmd_s = f"docker exec -e REPO_DIR={test_cmd_workdir} -e INSTANCE={instance_b64} -w {workdir} {container_id} {entrypoint}"
                process = await asyncio.create_subprocess_shell(
                    cmd_s, stdout=PIPE, stderr=PIPE
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout + 10
                )
                ic(stdout, stderr)

            if collect_coverage:
                _, cov_file = mkstemp(prefix="dot_coverage-")
                cmd_s = (
                    f"docker cp {container_id}:{test_cmd_workdir}/.coverage {cov_file}"
                )
                err_msg = f"failed to fetch .coverage from container {container_id} using cmd: {cmd_s}"
                process = await asyncio.create_subprocess_shell(
                    cmd_s, stdout=PIPE, stderr=PIPE
                )
                await check_process(process, err_msg)
            else:
                cov_file = ""

            entries = list(scandir(log_dir))
            assert len(entries) == 1
            log_file = entries[0].path

            ic(cov_file, log_file)

            from coverage import CoverageData

            cov_data = CoverageData(cov_file)
            cov_data.read()
            ic(list(cov_data.measured_files())[:5])
            ic(list(cov_data.measured_contexts())[:5])

            return cov_file, log_file
        except Exception as e:
            from loguru import logger  # TODO

            logger.exception(e)  # TODO

            entries = list(scandir(log_dir))
            if len(entries) == 1:
                log_file = entries[0].path
            else:
                _, log_file = mkstemp(
                    prefix=f"regression-{task.task_id}-", suffix=".log"
                )
            raise NoCoverageData(log_file) from e
        finally:
            cmd_s = f"docker rm -f {container_id}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            await process.communicate()

    @classmethod
    async def make_test_cmd_with_cov(
        cls,
        task_instance: dict,
        container_id: str,
        container_repo_dir: str,
        python_path: str = "python",
    ) -> str:
        repo = task_instance["repo"]

        test_type = MAP_REPO_TO_TEST_FRAMEWORK[repo]

        test_files = task_instance["test_directives"]

        if test_type.startswith("pytest"):
            test_type_cov = test_type.replace(
                "pytest", "pytest --cov --cov-context=test", 1
            )
        elif test_type.startswith("bin/test"):
            assert repo == "sympy/sympy"

            test_type_cov = (
                "pytest --cov --cov-context=test --no-header"
                " -rA --tb=no -p no:cacheprovider"
            )

            container_covrc = join(container_repo_dir, ".coveragerc")
            _, covrc = mkstemp(prefix="coveragerc-")

            cmd_s = f"docker cp {container_id}:{container_covrc} {covrc}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )

            # The container may or may not have .coveragerc,
            # and this is fine. So do not check process exit code.
            await process.communicate()

            CovrcUtils._omit_coverage_in_file(covrc, test_files)

            cmd_s = f"docker cp {covrc} {container_id}:{container_covrc}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            await check_process(process)
        elif test_type.startswith("tox"):
            assert repo == "sphinx-doc/sphinx"

            test_type_cov = test_type

            container_tox_ini = join(container_repo_dir, "tox.ini")
            _, tox_ini = mkstemp(prefix="tox.ini-")

            cmd_s = f"docker cp {container_id}:{container_tox_ini} {tox_ini}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            await check_process(process)

            CovrcUtils._add_pytest_cov_to_tox(tox_ini)

            cmd_s = f"docker cp {tox_ini} {container_id}:{container_tox_ini}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            await check_process(process)
        elif test_type.startswith("./tests/runtests.py"):
            assert repo == "django/django"

            test_type_cov = (
                f"{python_path} -m coverage run runtests.py --parallel 1 --verbosity 2"
            )

            container_covrc = join(container_repo_dir, ".coveragerc")
            _, covrc = mkstemp(prefix="coveragerc-")

            cmd_s = f"docker cp {container_id}:{container_covrc} {covrc}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            await process.communicate()

            CovrcUtils._specify_dynamic_context(covrc)

            cmd_s = f"docker cp {covrc} {container_id}:{container_covrc}"
            process = await asyncio.create_subprocess_shell(
                cmd_s, stdout=PIPE, stderr=PIPE
            )
            await check_process(process)
        else:
            raise NotImplementedError(
                f"Test framework not supported for coverage collection: {test_type}"
            )

        return f"{test_type_cov} {' '.join(test_files)}"

    # Adapted from swe_bench_docker/run_docker.py
    @classmethod
    async def start_swe_bench_docker_container(
        cls,
        repo: str,
        version: str,
        instance_id: str,
        namespace: str,
        docker_opts: list[str] | None = None,
    ):
        docker_image = cls.get_swe_bench_docker_image_name(
            repo, version, instance_id, namespace
        )

        docker_command = ["docker", "run", *(docker_opts or []), docker_image]

        cmd_s = " ".join(docker_command)

        process = await asyncio.create_subprocess_shell(cmd_s, stdout=PIPE, stderr=PIPE)
        err_msg = f"failed to create docker instance using cmd: {cmd_s}"
        stdout = await check_process(process, err_msg)

        container_id = stdout.strip()
        return container_id

    @classmethod
    async def get_container_project_path(cls, task: SweTask) -> str:
        image = cls.get_swe_bench_docker_image_name(
            task.repo_name, task.repo_version, task.task_id
        )
        cmd_s = f"docker image inspect {image}"
        process = await asyncio.create_subprocess_shell(cmd_s, stdout=PIPE, stderr=PIPE)
        stdout = await check_process(process)
        env_settings = json.loads(stdout)[0]["Config"]["Env"]
        for x in env_settings:
            if x.startswith("REPO_DIR="):
                return x.partition("=")[2]
        raise RuntimeError(f"could not find REPO_DIR env var in image: {image}")

    @classmethod
    def get_swe_bench_docker_image_name(
        cls, repo: str, version: str, instance_id: str, namespace: str = "autocoderover"
    ):
        specifications = MAP_VERSION_TO_INSTALL[repo][version]

        image_prefix = "swe-bench"
        repo_name = repo.replace("/", "_")
        if specifications.get("instance_image", False):
            return f"{namespace}/{image_prefix}-{repo_name}-instance:{instance_id}"
        else:
            return f"{namespace}/{image_prefix}-{repo_name}-testbed:{version}"

    @classmethod
    def make_swe_bench_docker_instance(
        cls, task: SweTask, patch_content: str, test_patch: str
    ) -> dict:
        repo = task.repo_name
        version = task.repo_version
        instance_id = task.task_id
        base_commit = task.commit
        developer_test_patch = task.test_patch

        test_type = MAP_REPO_TO_TEST_FRAMEWORK[repo]

        # get_test_directives requires a dict, but only these fields are used
        instance_to_get_test_directive = {
            "repo": repo,
            "test_patch": developer_test_patch,
        }
        test_directives = get_test_directives(instance_to_get_test_directive)
        test_cmd = f"{test_type} {' '.join(test_directives)}"

        # use no-op test_patch, since we are running pre-existing tests

        instance_for_running_test = {
            "repo": repo,
            "version": version,
            "base_commit": base_commit,
            "instance_id": instance_id,
            "model_name_or_path": "autocoderover_intermediate",
            "model_patch": patch_content,
            "test_patch": test_patch,
            "test_directives": test_directives,
            "test_cmd": test_cmd,
        }
        return instance_for_running_test

    @classmethod
    def parse_eval_log(cls, repo: str, content: str) -> dict:
        parser = MAP_REPO_TO_PARSER[repo]
        content = content.split(f"{APPLY_PATCH_PASS} (pred)")[-1]
        return parser(content)


async def check_process(process: Process, err_msg: str | None = None) -> str:
    stdout, stderr = await process.communicate()
    stdout = stdout.decode()
    stderr = stderr.decode()
    assert process.returncode is not None
    if process.returncode != 0:
        err_msg = err_msg or ""
        raise RuntimeError(f"{err_msg.rstrip()} Stderr: {stderr}")
    return stdout


class CovrcUtils:
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
