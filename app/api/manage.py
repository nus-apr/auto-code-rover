import configparser
import json
import os
from collections.abc import Mapping
from copy import deepcopy
from os import PathLike
from os.path import join as pjoin
from pathlib import Path
from subprocess import PIPE, STDOUT, TimeoutExpired

from docstring_parser import parse

import app.utils as apputils
from app import globals, log
from app.analysis import sbfl
from app.api import agent_proxy, agent_write_patch
from app.data_structures import FunctionCallIntent, MessageThread
from app.log import log_and_print, log_exception
from app.search.search_manage import SearchManager


class ProjectApiManager:
    ################# State machine specific ################
    # NOTE: this section is for state machine; APIs in stratified mode are specified
    # in agent_api_selector.py
    api_functions = [
        "search_class",
        "search_class_in_file",
        "search_method",
        "search_method_in_class",
        "search_method_in_file",
        "search_code",
        "search_code_in_file",
        "write_patch",
    ]

    def next_tools(self) -> list[str]:
        """
        Return the list of tools that should be used in the next round.
        """
        search_tools = [
            "search_class",
            "search_class_in_file",
            "search_method",
            "search_method_in_class",
            "search_method_in_file",
            "search_code",
            "search_code_in_file",
        ]
        all_tools = search_tools + ["write_patch"]
        if not self.curr_tool:
            # this means we are at the beginning of the conversation
            # you have to start from doing some search
            return search_tools

        state_machine = {
            "search_class": search_tools,
            "search_class_in_file": search_tools,
            "search_method": all_tools,
            "search_method_in_class": all_tools,
            "search_method_in_file": all_tools,
            "search_code": all_tools,
            "search_code_in_file": all_tools,
            "write_patch": [],
        }
        return state_machine[self.curr_tool]

    def __init__(
        self,
        task_id: str,
        project_path: str,
        commit: str,
        output_dir: str,
        env_name: Optional[str] = None,
        repo_name: Optional[str] = None,
        pre_install_cmds: List[str] = [],
        install_cmd: Optional[str] = None,
        test_cmd: Optional[str] = None,
        test_patch: Optional[str] = None,
        testcases_passing: List[str] = [],
        testcases_failing: List[str] = [],
        do_install: bool = False,
        import_root: str = "src",
    ):
        # for logging of this task instance
        self.logger = log.get_logger(task_id)
        self.task_id = task_id
        self.project_path = project_path
        self.commit = commit
        self.env_name = env_name
        self.repo_name = repo_name
        # additional installation commands after setup was done
        self.pre_install_cmds: list[str] = pre_install_cmds
        self.install_cmd: str = install_cmd
        # command to run tests
        self.test_cmd: str = test_cmd
        # the patch to testcases
        self.test_patch: str = test_patch
        # names of the passing testcases for this issue
        self.testcases_passing: list[str] = testcases_passing
        # names of the failing testcases for this issue
        self.testcases_failing: list[str] = testcases_failing
        # where to write our output
        self.output_dir = os.path.abspath(output_dir)

        # directory starting from where modules are imported (in the test files);
        # relative to project_path
        self.import_root = import_root

        self.num_tests = 0

        # get the correct version of the project and commit-specific pip install
        with apputils.cd(self.project_path):
            apputils.repo_reset_and_clean_checkout(self.commit, self.logger)

        # Install task-specific dependencies
        if do_install:
            self.do_install()

        # apply the test modifications to this task
        if self.test_patch is not None:
            self.apply_test_patch()

        # commit the current changes, so that resetting later do not erase them
        if do_install or self.test_patch is not None:
            # this means we have applied some changes to the repo before
            # starting the actual workflow
            with apputils.cd(self.project_path):
                apputils.repo_commit_current_changes(self.logger)

        # build search manager
        self.search_manager = SearchManager(self.project_path)

        # keeps track which tools is currently being used
        self.curr_tool: str | None = None

        # record the sequence of tools used, and their return status
        self.tool_call_sequence: list[Mapping] = []

        # record layered API calls
        self.tool_call_layers: list[list[Mapping]] = []

        # record cost and token information
        self.cost: float = 0.0
        self.input_tokens: int = 0
        self.output_tokens: int = 0

    @classmethod
    def get_short_func_summary_for_openai(cls) -> str:
        """
        Get a short summary of all tool functions.
        Intended to be used for constructing the initial system prompt.
        """
        summary = ""
        for fname in cls.api_functions:
            if not hasattr(cls, fname):
                continue
            func_obj = getattr(cls, fname)
            doc = parse(func_obj.__doc__)
            short_desc = (
                doc.short_description if doc.short_description is not None else ""
            )
            summary += f"\n- {fname}: {short_desc}"
        return summary

    @classmethod
    def get_full_funcs_for_openai(cls, tool_list: list[str]):
        """
        Return a list of function objects which can be sent to OpenAI for
        the function calling feature.

        Args:
            tool_list (List[str]): The available tools to generate doc for.
        """
        tool_template = {
            "type": "function",
            "function": {
                "name": "",
                "description": "",
                "parameters": {
                    "type": "object",
                    "properties": {},  # mapping from para name to type+description
                    "required": [],  # name of required parameters
                },
            },
        }
        all_tool_objs = []

        for fname in tool_list:
            if not hasattr(cls, fname):
                continue
            tool_obj = deepcopy(tool_template)
            tool_obj["function"]["name"] = fname
            func_obj = getattr(cls, fname)
            # UPDATE: we only parse docstring now
            # there are two sources of information:
            # 1. the docstring
            # 2. the function signature
            # Docstring is where we get most of the textual descriptions; for accurate
            # info about parameters (whether optional), we check signature.

            ## parse docstring
            doc = parse(func_obj.__doc__)
            short_desc = (
                doc.short_description if doc.short_description is not None else ""
            )
            long_desc = doc.long_description if doc.long_description is not None else ""
            description = short_desc + "\n" + long_desc
            tool_obj["function"]["description"] = description
            doc_params = doc.params
            for doc_param in doc_params:
                param_name = doc_param.arg_name
                if param_name == "self":
                    continue
                typ = doc_param.type_name
                desc = doc_param.description
                is_optional = doc_param.is_optional
                # now add this param to the tool object
                tool_obj["function"]["parameters"]["properties"][param_name] = {
                    "type": typ,
                    "description": desc,
                }
                if not is_optional:
                    tool_obj["function"]["parameters"]["required"].append(param_name)

            all_tool_objs.append(tool_obj)

        return all_tool_objs

    def dispatch_intent(
        self, intent: FunctionCallIntent, message_thread: MessageThread
    ) -> tuple[str, str, bool]:
        """Dispatch a function call intent to actually perform its action.

        Args:
            intent (FunctionCallIntent): The intent to dispatch.
            message_thread (MessageThread): the current message thread,
                since some tools require it.
        Returns:
            The result of the action.
            Also a summary that should be communicated to the model.
        """
        if (intent.func_name not in self.api_functions) and (
            intent.func_name != "get_class_full_snippet"
        ):
            error = f"Unknown function name {intent.func_name}."
            summary = "You called a tool that does not exist. Please only use the tools provided."
            return error, summary, False
        func_obj = getattr(self, intent.func_name)
        try:
            # ready to call a function
            self.curr_tool = intent.func_name
            if intent.func_name in ["write_patch"]:
                # these two functions require the message thread
                call_res = func_obj(message_thread)
            else:
                call_res = func_obj(**intent.arg_values)
        except Exception as e:
            # TypeError can happen when the function is called with wrong parameters
            # we just return the error message as the call result
            log_exception(self.logger, e)
            error = str(e)
            summary = "The tool returned error message."
            call_res = (error, summary, False)

        log_and_print(self.logger, f"Result of dispatch_intent: {call_res}")

        # record this call and its result separately
        _, _, call_is_ok = call_res
        self.tool_call_sequence.append(intent.to_dict_with_result(call_is_ok))

        if not self.tool_call_layers:
            self.tool_call_layers.append([])
        self.tool_call_layers[-1].append(intent.to_dict_with_result(call_is_ok))

        return call_res

    def do_install(self):
        """Do left-over install commands after setting up.
        The commands being run here are 'pre_install' and 'install' defined in
        harness/constants.py file in SWE-bench.
        """
        if not self.pre_install_cmds and not self.install_cmd:
            # no command for installation, skip
            return
        with apputils.cd(self.project_path):
            # (0) For matplotlib, qhull tarball download
            # just fails, so we need to pre-install the system version and use it
            if "matplotlib" in self.task_id:
                with open("mplsetup.cfg", "w") as f:
                    f.write("[libs]\nsystem_qhull = true")
            # (1) pre-install
            for cmd in self.pre_install_cmds:
                cp = apputils.run_string_cmd_in_conda(
                    self.logger, cmd, self.env_name, capture_output=True, text=True
                )
                if cp.returncode != 0:
                    log_and_print(self.logger, cp.stderr)
                    raise RuntimeError(f"Command {cmd} failed.")

            # (2) install
            cp = apputils.run_string_cmd_in_conda(
                self.logger,
                self.install_cmd,
                self.env_name,
                capture_output=True,
                text=True,
            )
            if cp.returncode != 0:
                log_and_print(self.logger, cp.stderr)
                raise RuntimeError(f"Command {self.install_cmd} failed.")
            # (3) xmlrunner for our custom run_test; coverage required for fault localization
            other_install_cmd = (
                "python -m pip install xmlrunner coverage pytest pytest-cov"
            )
            cp = apputils.run_string_cmd_in_conda(
                self.logger,
                other_install_cmd,
                self.env_name,
                capture_output=True,
                text=True,
            )
            if cp.returncode != 0:
                log_and_print(self.logger, cp.stderr)
                raise RuntimeError(f"Command {other_install_cmd} failed.")

    def start_new_tool_call_layer(self):
        self.tool_call_layers.append([])

    def dump_tool_call_sequence_to_file(self):
        """Dump the sequence of tool calls to a file."""
        tool_call_file = pjoin(self.output_dir, "tool_call_sequence.json")
        with open(tool_call_file, "w") as f:
            json.dump(self.tool_call_sequence, f, indent=4)

    def dump_tool_call_layers_to_file(self):
        """Dump the layers of tool calls to a file."""
        tool_call_file = pjoin(self.output_dir, "tool_call_layers.json")
        with open(tool_call_file, "w") as f:
            json.dump(self.tool_call_layers, f, indent=4)

    def accumulate_cost_and_tokens(
        self, cost: float, input_tokens: int, output_tokens: int
    ):
        self.cost += cost
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def apply_test_patch(self):
        """
        Apply the patch to testcases, as supplied by the benchmark.
        This step brings in all the new tests and testcase modifications.
        """
        if not self.test_patch:
            # no patches to tests are found
            return
        with apputils.cd(self.project_path):
            # (1) write test_patch to a temp file
            test_patch_path = pjoin(self.project_path, "swe_bench_tests.patch")
            with open(test_patch_path, "w") as f:
                f.write(self.test_patch)
            # (2) apply these patches
            # FIXME: check for failure here
            apply_cmd = ["git", "apply", test_patch_path]
            cp = apputils.run_command(
                self.logger, apply_cmd, capture_output=True, text=True
            )
            if cp.returncode != 0:
                log_and_print(self.logger, cp.stderr)
                raise RuntimeError(f"Command {apply_cmd} failed.")
            # (3) remove the temp file, which is not so important
            os.remove(test_patch_path)

    def specify_dynamic_context(self, coveragerc: str | PathLike) -> None:
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

    def omit_coverage_in_file(
        self, coveragerc: str | PathLike, omitted: list[str]
    ) -> None:
        value = "".join(f"\n{file}" for file in omitted)
        value = "\n# added by auto-code-rover" + value

        config = configparser.ConfigParser()

        if os.path.exists(coveragerc):
            config.read(coveragerc)

        if not config.has_section("run"):
            config.add_section("run")

        config["run"]["omit"] = value + config["run"].get("omit", "")

        with open(coveragerc, "w") as f:
            config.write(f)

    def add_pytest_cov_to_tox(self, tox_ini: str | PathLike):
        assert os.path.exists(tox_ini)

        config = configparser.ConfigParser()
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

    def run_developer_test_suite(self) -> str:
        """
        Run the relevant parts of developer test suite.
        Record coverage information for each test while running them.

        Returns:
            The produced coverage file for the test suite. Empty string if no coverage file is produced.
        """
        with apputils.cd(self.project_path):
            # (1) run the tests to produce coverage output
            if self.test_cmd.startswith("pytest"):
                # Use pytest-cov to properly get parametrized test names
                args = self.test_cmd.removeprefix("pytest")
                test_cmd = f"python -m pytest --cov --cov-context=test {args}"
            elif "bin/test" in self.test_cmd:
                assert self.task_id.startswith("sympy__")

                # Sympy tests are compatible with PyTest. Only issue is that more tests
                # can berun by PyTest than if Sympy testing is used. However, we match
                # context names with PASS_TO_PASS and FAIL_TO_PASS later, so it's fine.

                test_files = [x for x in self.test_cmd.split() if x.endswith(".py")]
                assert (
                    test_files
                ), f"Failed to find test files in command: {self.test_cmd}"

                cov_config = pjoin(self.project_path, ".coveragerc")
                self.omit_coverage_in_file(cov_config, test_files)

                test_cmd = (
                    "python -m pytest --cov --cov-context=test --no-header"
                    f" -rA --tb=no -p no:cacheprovider {' '.join(test_files)}"
                )
            elif self.test_cmd.startswith("tox "):
                tox_ini = pjoin(self.project_path, "tox.ini")
                assert os.path.exists(
                    tox_ini
                ), f"tox.ini not found in {self.project_path}"

                self.add_pytest_cov_to_tox(tox_ini)

                test_cmd = f"python -m {self.test_cmd}"
            else:
                cov_config = pjoin(self.project_path, ".coveragerc")
                self.specify_dynamic_context(cov_config)
                test_cmd = f"python -m coverage run {self.test_cmd}"

            try:
                cp = apputils.run_string_cmd_in_conda(
                    self.logger,
                    test_cmd,
                    self.env_name,
                    stdout=PIPE,
                    stderr=STDOUT,
                    text=True,
                    timeout=globals.test_exec_timeout,
                )
                Path(self.output_dir, "run_developer_tests.log").write_text(cp.stdout)
            except TimeoutExpired:
                log.log_and_print(
                    self.logger,
                    "Timeout expired while running the test suite.",
                )
                return ""

            # (2) check whether the coverage file is there
            cov_file = pjoin(self.project_path, ".coverage")
            if not os.path.exists(cov_file):
                # sometimes cov_file can have extensions such as:
                # .coverage.TSS.852665.XmCvBpdx
                # we need to find the correct file
                all_files = os.listdir(self.project_path)
                for f in all_files:
                    if f.startswith(".coverage.TSS"):
                        cov_file = pjoin(self.project_path, f)
                        break
                # now check again
                if not os.path.exists(cov_file):
                    log.log_and_print(
                        self.logger,
                        "Coverage file is not produced after running the test suite.",
                    )
                    return ""
            return cov_file

    def run_developer_test_suite_django(self) -> str:
        """
        Since django does not use pytest as the testing framework, we use another procedure.

        Returns:
            - The produced coverage file for the test suite. Empty string if the file is not produced.
        """
        tests_dir = pjoin(self.project_path, "tests")
        assert os.path.isdir(tests_dir)

        execution_dir = tests_dir
        with apputils.cd(execution_dir):
            # (1) since we want to use coverage.py with dynamic context, create config first
            cov_config = pjoin(execution_dir, ".coveragerc")
            self.specify_dynamic_context(cov_config)

            # (2) actually run the tests to produce coverage output
            orig_cmd_parts = self.test_cmd.split(" ")
            assert (
                orig_cmd_parts[0] == "./tests/runtests.py"
            ), f"Test command does not start with ./tests/runtests.py: {self.test_cmd}"
            test_cmd = (
                "python -m coverage run "
                + os.path.basename(orig_cmd_parts[0])
                + " --parallel 1 "
                + " ".join(orig_cmd_parts[1:])
            )
            try:
                cp = apputils.run_string_cmd_in_conda(
                    self.logger,
                    test_cmd,
                    self.env_name,
                    stdout=PIPE,
                    stderr=STDOUT,
                    text=True,
                    timeout=globals.test_exec_timeout,
                )
                Path(self.output_dir, "run_developer_tests.log").write_text(cp.stdout)
            except TimeoutExpired:
                log.log_and_print(
                    self.logger,
                    "Timeout expired while running the test suite.",
                )
                return ""

            # (3) check whether the coverage file is there
            cov_file = pjoin(execution_dir, ".coverage")
            if not os.path.exists(cov_file):
                log.log_and_print(
                    self.logger,
                    "Coverage file is not produced after running the test suite.",
                )
                return ""
            return cov_file

    ###################################################################
    ########################## API functions ##########################
    ###################################################################

    def fault_localization(self) -> tuple[str, str, bool]:
        """Localize the faulty code snippets by executing test cases.

        Perform fault localization by running the passing and failing test-cases.
        Returns a list of code snippets that are likely to be related to the issue.
        """
        sbfl_result_file = pjoin(self.output_dir, "sbfl_result.json")  # for logging
        if "django" in self.task_id:
            cov_file = self.run_developer_test_suite_django()
        else:
            cov_file = self.run_developer_test_suite()
        if not cov_file:
            # fail to run the test suite with coverage
            with open(sbfl_result_file, "w") as f:
                f.write("")
            tool_output = "Error in running localization tool"
            summary = tool_output
            return tool_output, summary, False

        test_file_names, ranked_lines = sbfl.run(
            self.testcases_passing, self.testcases_failing, cov_file, self.task_id
        )
        ranked_ranges_abs = sbfl.collate_results(ranked_lines, test_file_names)
        ranked_methods_abs = sbfl.map_collated_results_to_methods(ranked_ranges_abs)

        def relativize_filename(tup: tuple) -> tuple:
            file = tup[0]
            relative_file = os.path.relpath(file, self.project_path)
            return (relative_file,) + tup[1:]

        ranked_ranges = [relativize_filename(t) for t in ranked_ranges_abs]
        ranked_methods = [relativize_filename(t) for t in ranked_methods_abs]

        with open(sbfl_result_file, "w") as f:
            json.dump(ranked_ranges, f, indent=4)

        sbfl_method_result_file = Path(self.output_dir, "sbfl_result_method.json")
        with open(sbfl_method_result_file, "w") as f:
            json.dump(ranked_methods, f, indent=4)

        log.log_and_print(self.logger, f"SBFL result (lines): {ranked_ranges}")
        log.log_and_print(self.logger, f"SBFL result (methods): {ranked_methods}")

        if not ranked_ranges and not ranked_methods:
            # empty sbfl results
            tool_output = "Localization could not produce any output."
            summary = tool_output
            return tool_output, summary, False

        # TODO: make this a separate method in sbfl
        # form sbfl result into a response - this is for method level
        if len(ranked_methods) > 5:
            ranked_methods = ranked_methods[:5]
        tool_output = f"Top-{len(ranked_methods)} suspicious methods:\n"
        summary = f"Returned top-{len(ranked_methods)} suspicious methods."
        for idx, (file, class_name, method_name, _) in enumerate(ranked_methods):
            res_str = f"<file>{file}</file>"
            if class_name:
                res_str += f" <class>{class_name}</class>"
            if method_name:
                res_str += f" <func>{method_name}</func>"
            tool_output += f"Suspicious method #{idx + 1}:\n{res_str}\n\n"
        return tool_output, summary, True

    # not a search API - just to get full class definition when bug_location only specifies a class
    def get_class_full_snippet(self, class_name: str):
        return self.search_manager.get_class_full_snippet(class_name)

    def search_class(self, class_name: str) -> tuple[str, str, bool]:
        """Search for a class in the codebase.

        Only the signature of the class is returned. The class signature
        includes class name, base classes, and signatures for all of its methods/properties.

        Args:
            class_name (string): Name of the class to search for.

        Returns:
            string: the class signature in string if success;
                    an error message if the class cannot be found.
            string: a message summarizing the method.
        """
        return self.search_manager.search_class(class_name)

    def search_class_in_file(
        self, class_name: str, file_name: str
    ) -> tuple[str, str, bool]:
        """Search for a class in a given file.

        Returns the actual code of the entire class definition.

        Args:
            class_name (string): Name of the class to search for.
            file_name (string): The file to search in. Must be a valid python file name.

        Returns:
            part 1 - the searched class code or error message.
            part 2 - summary of the tool call.
        """
        return self.search_manager.search_class_in_file(class_name, file_name)

    def search_method_in_file(
        self, method_name: str, file_name: str
    ) -> tuple[str, str, bool]:
        """Search for a method in a given file.

        Returns the actual code of the method.

        Args:
            method_name (string): Name of the method to search for.
            file_name (string): The file to search in. Must be a valid python file name.

        Returns:
            part 1 - the searched code or error message.
            part 2 - summary of the tool call.
        """
        return self.search_manager.search_method_in_file(method_name, file_name)

    def search_method_in_class(
        self, method_name: str, class_name: str
    ) -> tuple[str, str, bool]:
        """Search for a method in a given class.

        Returns the actual code of the method.

        Args:
            method_name (string): Name of the method to search for.
            class_name (string): Consider only methods in this class.

        Returns:
            part 1 - the searched code or error message.
            part 2 - summary of the tool call.
        """
        return self.search_manager.search_method_in_class(method_name, class_name)

    def search_method(self, method_name: str) -> tuple[str, str, bool]:
        """Search for a method in the entire codebase.

        Returns the actual code of the method.

        Args:
            method_name (string): Name of the method to search for.

        Returns:
            part 1 - the searched code or error message.
            part 2 - summary of the tool call.
        """
        return self.search_manager.search_method(method_name)

    def search_code(self, code_str: str) -> tuple[str, str, bool]:
        """Search for a code snippet in the entire codebase.

        Returns the method that contains the code snippet, if it is found inside a file.
        Otherwise, returns the region of code surrounding it.

        Args:
            code_str (string): The code snippet to search for.

        Returns:
            The region of code containing the searched code string.
        """
        return self.search_manager.search_code(code_str)

    def search_code_in_file(
        self, code_str: str, file_name: str
    ) -> tuple[str, str, bool]:
        """Search for a code snippet in a given file file.

        Returns the entire method that contains the code snippet.

        Args:
            code_str (string): The code snippet to search for.
            file_name (string): The file to search in. Must be a valid python file name in the project.

        Returns:
            The method code that contains the searched code string.
        """
        return self.search_manager.search_code_in_file(code_str, file_name)

    def write_patch(self, message_thread: MessageThread) -> tuple[str, str, bool]:
        """Based on the current context, ask another agent to write a patch.

        When you think the current information is sufficient to write a patch, invoke this tool.

        The tool returns a patch based on the current available information.
        """
        (
            tool_output,
            cost,
            input_tokens,
            output_tokens,
        ) = agent_write_patch.run_with_retries(
            self.logger,
            message_thread,
            self.output_dir,
            self.project_path,
            self.test_cmd,
            self.repo_name,
            self.env_name,
            self.task_id,
            self.testcases_passing,
            self.testcases_failing,
        )
        summary = "The tool returned the patch written by another agent."
        self.accumulate_cost_and_tokens(cost, input_tokens, output_tokens)
        # The return status of write_patch does not really matter, so we just use True here
        return tool_output, summary, True

    def proxy_apis(self, text: str) -> tuple[str | None, str, list[MessageThread]]:
        """Proxy APIs to another agent."""
        (
            tool_output,
            new_thread,
            cost,
            input_tokens,
            output_tokens,
        ) = agent_proxy.run_with_retries(
            self.logger, text
        )  # FIXME: type of `text`
        if tool_output is None:
            summary = "The tool returned nothing. The main agent probably did not provide enough clues."
        else:
            summary = "The tool returned the selected search APIs in json format generaetd by another agent."
        self.accumulate_cost_and_tokens(cost, input_tokens, output_tokens)
        return tool_output, summary, new_thread
