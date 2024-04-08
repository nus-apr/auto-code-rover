"""
Modified from pinpoint:
https://github.com/Generalized-SBFL/pytest-pinpoint/blob/master/pytest_pinpoint.py

For the purpose of SWE-bench, since each task instance has its own conda env, the test
execution (with coverage run) should be done in the task instance's conda env.
Afterwards, the analysis of coverage data should be done in this project's conda env.

This file mainly analyzes the coverage data for SBFL analysis.
"""

import ast
import math
import os
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Mapping, Tuple

from coverage.sqldata import CoverageData


def canonicalize_testname_sympy_bin_test(testname: str) -> Tuple[str, str]:
    """
    The sympy version, who excutes tests with bin/test

    All tests in sympy are just function names, like `test_is_superset`
    """
    return "", testname


def canonicalize_testname_django_runner(testname: str) -> Tuple[str, str]:
    """
    Same as canonicalize_testname_pytest, but for django test runner.
    Need to deal with them separately because the test name formats are diff.
    """
    identifier_pattern = r"[a-zA-Z_][a-zA-Z0-9_]*"
    pattern = r"^{0} \({0}(.{0})*\)".format(identifier_pattern)
    if not re.search(pattern, testname):
        # special case like: A reference in a local scope can't be serialized.
        return "", ""

    func, path = testname.split(" (")
    path = path[:-1]  # remove the trailing )
    full_name = path + "." + func
    # path can contain both module or class name
    # module are snake case, class are camel case
    # we only want module name to form the file name
    path_parts = path.split(".")
    modules = []
    for part in path_parts:
        if part.islower():
            modules.append(part)
    file_name = "/".join(modules) + ".py"
    return file_name, full_name


def canonicalize_testname_pytest(testname: str) -> Tuple[str, str]:
    """
    Unify the test names in tasks_map.json and pytest-cov.

    pytest-cov format is FILE::METHOD[PARAMETRIZATION]|PHASE, where PHASE is "setup", "run", or "teardown"
    see https://pytest-cov.readthedocs.io/en/latest/contexts.html#
    example:
        astropy/coordinates/tests/test_angles.py::test_latitude_limits[value2-expected_value2-None-float32-1]|run

    tasks_map.json format does not have the "|PHASE" suffix

    Returns:
        - (file_name, full name of the test)
    """
    file_name = testname.split("::")[0]
    return file_name, testname


def canonicalize_testname(task_id: str, testname: str) -> Tuple[str, str]:
    if "django" in task_id:
        return canonicalize_testname_django_runner(testname)
    elif "sympy" in task_id:
        return canonicalize_testname_sympy_bin_test(testname)
    else:
        return canonicalize_testname_pytest(testname)


class FileExecStats(object):
    def __init__(self, filename: str):
        self.filename = filename
        # line number -> (pass_count, fail_count)
        self.line_stats: Dict[int, Tuple[int, int]] = dict()

    def incre_pass_count(self, line_no: int):
        if line_no in self.line_stats:
            old_pass, old_fail = self.line_stats[line_no]
            self.line_stats[line_no] = (old_pass + 1, old_fail)
        else:
            self.line_stats[line_no] = (1, 0)

    def incre_fail_count(self, line_no: int):
        if line_no in self.line_stats:
            old_pass, old_fail = self.line_stats[line_no]
            self.line_stats[line_no] = (old_pass, old_fail + 1)
        else:
            self.line_stats[line_no] = (0, 1)

    def __str__(self):
        res = self.filename + "\n"
        res += pformat(self.line_stats)
        return res

    def __repr__(self) -> str:
        return self.__str__()


class ExecStats(object):
    def __init__(self):
        # file name -> FileExecStats
        self.file_stats: Dict[str, FileExecStats] = dict()

    def add_file(self, file_exec_stats: FileExecStats):
        self.file_stats[file_exec_stats.filename] = file_exec_stats

    def __str__(self) -> str:
        return pformat(self.file_stats)

    """
    Formula from:
    https://homes.cs.washington.edu/~rjust/publ/fault_localization_effectiveness_icse_2017.pdf
    """

    @staticmethod
    def ochiai(failed, passed, total_fail, total_pass):
        top = failed
        bottom = math.sqrt(total_fail * (failed + passed))
        if bottom == 0:
            return 0
        return top / bottom

    @staticmethod
    def tarantula(failed, passed, total_fail, total_pass):
        top = failed / total_fail
        bottom = failed / total_fail + passed / total_pass
        if bottom == 0:
            return 0
        return top / bottom

    @staticmethod
    def op2(failed, passed, total_fail, total_pass):
        top = passed
        bottom = total_pass + 1
        if bottom == 0:
            return failed
        return failed - top / bottom

    @staticmethod
    def barinel(failed, passed, total_fail, total_pass):
        top = passed
        bottom = passed + failed
        if bottom == 0:
            return 0
        return 1 - top / bottom

    @staticmethod
    def dstar(failed, passed, total_fail, total_pass):
        top = failed**2
        bottom = passed + (total_fail - failed)
        if bottom == 0:
            return 0
        return top / bottom

    def rank_lines(
        self, fl_algo, total_fail, total_pass
    ) -> list[tuple[str, int, float]]:
        lines_with_scores = []  # filename, line_no, score
        for file, file_exec_stats in self.file_stats.items():
            for line_no, (passed, failed) in file_exec_stats.line_stats.items():
                # invoke the fl algorithm to compute score
                score = fl_algo(failed, passed, total_fail, total_pass)
                lines_with_scores.append((file, line_no, score))
        # sort by score (descending), then by file name, then by line number
        lines_with_scores.sort(key=lambda x: (-x[2], x[0], x[1]))
        return lines_with_scores


def helper_remove_dup_and_empty(lst: List[str]) -> List[str]:
    """
    Remove duplicates and empty strings from the list.
    """
    return list(filter(lambda x: x != "", list(set(lst))))


def helper_two_tests_match(test_one: str, test_two: str) -> bool:
    """
    Check if two tests are referring to the same test function.
    For example:
        - matplotlib.tests.test_figure.test_savefig_pixel_ratio
        - lib.matplotlib.tests.test_figure.test_savefig_pixel_ratio
    Should be the same.
    """
    # make sure suffix are the same, since the actual function name
    # appears the last
    return test_one.endswith(test_two) or test_two.endswith(test_one)


def helper_test_match_any(test: str, candidates: List[str]) -> bool:
    """
    Check if the test matches any of the candidates.
    """
    return any([helper_two_tests_match(test, c) for c in candidates])


"""
Main entry to the SBFL analysis.
"""


def run(
    pass_tests: List[str], fail_tests: List[str], cov_file: str, task_id: str
) -> tuple[list[str], list[Tuple[str, int, float]]]:
    """
    Run SBFL analysis on the given coverage data file.
    At the same time, collect the test file names.

    Args:
        - pass_tests: list of test names that passed
        - fail_tests: list of test names that failed
        - cov_file: path to the coverage data file, generated by python coverage.py
        - task_id: task id to identify which project we are on.

    Returns:
        - list of test file names, list of ranked lines (file, line_no, score)
    """
    pass_tests_names = []
    fail_tests_names = []
    test_file_names = []
    for test in pass_tests:
        file_name, test_name = canonicalize_testname(task_id, test)
        pass_tests_names.append(test_name)
        test_file_names.append(file_name)
    for test in fail_tests:
        file_name, test_name = canonicalize_testname(task_id, test)
        fail_tests_names.append(test_name)
        test_file_names.append(file_name)

    # compute total before removing wierd test names
    total_fail = len(fail_tests_names)
    total_pass = len(pass_tests_names)

    pass_tests_names = helper_remove_dup_and_empty(pass_tests_names)
    fail_tests_names = helper_remove_dup_and_empty(fail_tests_names)
    test_file_names = helper_remove_dup_and_empty(test_file_names)

    if not os.path.isfile(cov_file):
        raise RuntimeError(f"Coverage data file {cov_file} does not exist.")

    covdb = CoverageData(basename=cov_file)
    covdb.read()

    exec_stats = ExecStats()

    # Collect measured_files
    measured_files = covdb.measured_files()
    for measured_f in measured_files:
        file_exec_stats = FileExecStats(measured_f)
        current_context = covdb.contexts_by_lineno(measured_f)
        # not consider files which are not tested
        if current_context is [] or current_context is None:
            measured_files.remove(measured_f)
            continue
        # store pass/fail stats associated with context and line number
        for line_no, context_names in current_context.items():
            for test_name in context_names:
                if not test_name:  # ''
                    continue

                # remove pytest-cov phase name
                # see https://pytest-cov.readthedocs.io/en/latest/contexts.html#
                test_name = re.sub(r"\|((setup)|(run)|(teardown))$", "", test_name)

                if helper_test_match_any(test_name, pass_tests_names):
                    file_exec_stats.incre_pass_count(line_no)
                elif helper_test_match_any(test_name, fail_tests_names):
                    file_exec_stats.incre_fail_count(line_no)
        exec_stats.add_file(file_exec_stats)

    # NOTE: swap algorithm here
    ranked_lines = exec_stats.rank_lines(ExecStats.ochiai, total_fail, total_pass)
    return test_file_names, ranked_lines


def collate_results(
    ranked_lines: List[Tuple[str, int, float]], test_file_names: List[str]
) -> List[Tuple[str, int, int, float]]:
    """
    From the ranked lines, perform filtering (for lines that are likely to be in the test files),
    as well as merging (since multiple ranked lines can be adjacent to each other).

    Returns:
        - list of (file, start_line_no, end_line_no, score), sorted
    """
    # (1) remove lines with non positive score
    positive_lines = [l for l in ranked_lines if l[2] > 0]
    # (2) remove lines that are in test files
    survived_lines = []
    for file, line_no, score in positive_lines:
        # file is full path, and test_files_names are relative path
        file_is_test = any([file.endswith(test_file) for test_file in test_file_names])
        if not file_is_test:
            survived_lines.append((file, line_no, score))

    # (3) convert survived lines into dict, key is filename, value is list of (line_no, score)
    file_line_score: Mapping[str, List[Tuple[int, float]]] = dict()
    for file, line_no, score in survived_lines:
        if file not in file_line_score:
            file_line_score[file] = []
        file_line_score[file].append((line_no, score))
    # sort the dict value list by line_no
    for file, line_score in file_line_score.items():
        new_line_score = sorted(line_score, key=lambda x: x[0])
        file_line_score[file] = new_line_score

    # (4) merge adjacent lines, the new dict value list is a list of (start_line_no, end_line_no, score)
    # note that end_line_no is inclusive
    merged_file_line_score: Mapping[str, List[Tuple[int, int, float]]] = dict()
    for file, line_score in file_line_score.items():
        merged_line_score = []
        # indexes into the line_score
        start_index = 0
        end_index = 0
        while end_index < len(line_score):
            while (
                end_index < len(line_score)
                and line_score[end_index][0]
                == line_score[start_index][0] + end_index - start_index
            ):
                end_index += 1
            # now we know line_scores between start_index and end_index - 1 are consecutive
            # find the highest score in this consecutive range
            scores = [score for _, score in line_score[start_index:end_index]]
            highest_score = max(scores)
            merged_line_score.append(
                (
                    line_score[start_index][0],
                    line_score[end_index - 1][0],
                    highest_score,
                )
            )
            start_index = end_index
        merged_file_line_score[file] = merged_line_score

    # convert dict back to list of (file, start_line_no, end_line_no, score), and sort by score
    res = []
    for file, line_score in merged_file_line_score.items():
        for start_line, end_line, score in line_score:
            res.append((file, start_line, end_line, score))
    # sort by score (descending), then by file name, then by start line number
    res = sorted(res, key=lambda x: (-x[3], x[0], x[1]))
    return res


@dataclass
class MethodId:
    class_name: str
    method_name: str

    def __str__(self):
        if self.class_name:
            return f"{self.class_name}.{self.method_name}"
        return self.method_name

    def __hash__(self):
        return hash((self.class_name, self.method_name))


@cache
def method_ranges_in_file(file: str) -> dict[MethodId, tuple[int, int]]:
    """
    Find the ranges of all methods in a python file.

    Result key is method name, value is (start_line, end_line), inclusive.
    """

    class MethodRangeFinder(ast.NodeVisitor):
        def __init__(self):
            self.range_map: dict[MethodId, tuple[int, int]] = {}
            self.class_name = ""

        def calc_method_id(self, method_name: str) -> MethodId:
            return MethodId(self.class_name, method_name)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_name = node.name
            super().generic_visit(node)
            self.class_name = ""

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            method_id = self.calc_method_id(node.name)
            assert node.end_lineno
            self.range_map[method_id] = (node.lineno, node.end_lineno)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            method_id = self.calc_method_id(node.name)
            assert node.end_lineno
            self.range_map[method_id] = (node.lineno, node.end_lineno)

    finder = MethodRangeFinder()

    source = Path(file).read_text()

    try:
        tree = ast.parse(source, file)
    except SyntaxError:
        return {}

    finder.visit(tree)

    return finder.range_map


def map_collated_results_to_methods(ranked_ranges) -> list[tuple[str, str, str, float]]:
    """
    Map suspicious lines to methods.

    Return list of (filename, methodname, suspicousness).
    A method is added at most once, when it is first seen in the line list.
    """
    seen = set()

    result = []
    for x in ranked_ranges:
        filename, start, end, suspiciousness = x
        range_map = method_ranges_in_file(filename)

        for method_id, r in range_map.items():
            if r[0] > end or r[1] < start:
                continue

            key = (filename, method_id)
            if key in seen:
                continue

            result.append(
                (filename, method_id.class_name, method_id.method_name, suspiciousness)
            )
            seen.add(key)
    return result
