import ast
import contextlib
import glob
import os
import subprocess
from logging import Logger
from os.path import dirname as pdirname
from os.path import join as pjoin
from pathlib import Path
from typing import List, Optional

from app.log import log_and_print


@contextlib.contextmanager
def cd(newdir):
    """
    Context manager for changing the current working directory
    :param newdir: path to the new directory
    :return: None
    """
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def run_command(logger, cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    """
    Run a command in the shell.
    Args:
        - logger: logger to use. If is None, do not write logs.
        - cmd: command to run
    """
    try:
        cp = subprocess.run(cmd, check=True, **kwargs)
    except subprocess.CalledProcessError as e:
        if logger is not None:
            log_and_print(logger, f"Error running command: {cmd}, {e}")
        raise e
    return cp


def repo_commit_current_changes(logger=None):
    """
    Commit the current active changes so that it's safer to do git reset later on.
    Use case: for storing the changes made in pre_install and test_patch in a commit.
    """
    add_all_cmd = ["git", "add", "."]
    commit_cmd = ["git", "commit", "-m", "Temporary commit for storing changes"]
    run_command(logger, add_all_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run_command(logger, commit_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def repo_clean_changes(logger=None) -> None:
    """
    Reset repo to HEAD. Basically clean active changes and untracked files on top of HEAD.

    A lightweight version of `repo_reset_and_clean_checkout`. This is also used in different scenarios.
    """
    reset_cmd = ["git", "reset", "--hard"]
    clean_cmd = ["git", "clean", "-fd"]
    run_command(logger, reset_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run_command(logger, clean_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def repo_reset_and_clean_checkout(commit_hash: str, logger=None) -> None:
    """
    Run commands to reset repo to the original commit state.
    Cleans both the uncommited changes and the untracked files, and submodule changes.
    Assumption: The current directory is the git repository.
    Args:
        - logger: logger to use. If is None, do not write logs.
    """
    # NOTE: do these before `git reset`. This is because some of the removed files below
    # may actually be in version control. So even if we deleted such files here, they
    # will be brought back by `git reset`.
    # Clean files that might be in .gitignore, but could have been created by previous runs
    if os.path.exists(".coverage"):
        os.remove(".coverage")
    if os.path.exists("tests/.coveragerc"):
        os.remove("tests/.coveragerc")
    other_cov_files = glob.glob(".coverage.TSS.*", recursive=True)
    for f in other_cov_files:
        os.remove(f)

    reset_cmd = ["git", "reset", "--hard", commit_hash]
    clean_cmd = ["git", "clean", "-fd"]
    checkout_cmd = ["git", "checkout", commit_hash]
    run_command(logger, reset_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run_command(logger, clean_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # need to checkout before submodule init. Otherwise submodule may init to another version
    run_command(logger, checkout_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # this is a fail-safe combo to reset any changes to the submodule: first unbind all submodules
    # and then make a fresh checkout of them.
    # Reference: https://stackoverflow.com/questions/10906554/how-do-i-revert-my-changes-to-a-git-submodule
    submodule_unbind_cmd = ["git", "submodule", "deinit", "-f", "."]
    submodule_init_cmd = ["git", "submodule", "update", "--init"]
    run_command(
        logger,
        submodule_unbind_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    run_command(logger, submodule_init_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_script_in_conda(args: list[str], env_name: str, **kwargs) -> subprocess.CompletedProcess:
    """
    Run a python command in a given conda environment.
    """
    cmd = ["conda", "run", "-n", env_name, "python", *args]
    return subprocess.run(cmd, **kwargs)


def run_string_cmd_in_conda(
    logger, command: str, env_name: str, **kwargs
) -> subprocess.CompletedProcess:
    """
    Run a complete command in a given conda environment, where the command is a string.

    This is useful when the command to be run contains &&, etc.

    NOTE: use `conda activate` instead of `conda run` in this verison, so that we can
          run commands that contain `&&`, etc.
    """
    conda_bin_path = os.getenv("CONDA_EXE")  # for calling conda
    if conda_bin_path is None:
        raise RuntimeError("Env variable CONDA_EXE is not set")
    conda_root_dir = pdirname(pdirname(conda_bin_path))
    conda_script_path = pjoin(conda_root_dir, "etc", "profile.d", "conda.sh")
    conda_cmd = (
        f"source {conda_script_path} ; conda activate {env_name} ; {command} ; conda deactivate"
    )
    log_and_print(logger, f"Running command: {conda_cmd}")
    return subprocess.run(conda_cmd, shell=True, **kwargs)


def create_dir_if_not_exists(dir_path: str):
    """
    Create a directory if it does not exist.
    Args:
        dir_path (str): Path to the directory.
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def convert_dir_to_absolute(dir_path: str) -> str:
    """
    Convert a (potentially) relative path to an absolute path.
    Args:
        dir_path (str): Path to the directory. Can be relative or absolute.
    Returns:
        str: Absolute path to the directory.
    """
    return os.path.abspath(dir_path)


def to_relative_path(file_path: str, project_root: str) -> str:
    """Convert an absolute path to a path relative to the project root.

    Args:
        - file_path (str): The absolute path.
        - project_root (str): Absolute path of the project root dir.

    Returns:
        The relative path.
    """
    if Path(file_path).is_absolute():
        return str(Path(file_path).relative_to(project_root))
    else:
        return file_path


def to_absolute_path(file_path: str, project_root: str) -> str:
    """Convert a relative path to an absolute path.

    Args:
        - file_path (str): The relative path.
        - project_root (str): Absolute path of a root dir.
    """
    return pjoin(project_root, file_path)


def find_file(directory, filename) -> Optional[str]:
    """
    Find a file in a directory. filename can be short name, relative path to the
    directory, or an incomplete relative path to the directory.
    Returns:
        - the relative path to the file if found; None otherwise.
    """

    # Helper method one
    def find_file_exact_relative(directory, filename) -> Optional[str]:
        if os.path.isfile(os.path.join(directory, filename)):
            return filename
        return None

    # Helper method two
    def find_file_shortname(directory, filename) -> Optional[str]:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file == filename:
                    return os.path.relpath(os.path.join(root, file), directory)
        return None

    # if the filename is exactly the relative path.
    found = find_file_exact_relative(directory, filename)
    if found is not None:
        return found

    # if the filename is a short name without any directory
    found = find_file_shortname(directory, filename)
    if found is not None:
        return found

    # if the filename has some directory, but is not a relative path to
    # the directory
    parts = filename.split(os.path.sep)
    shortname = parts[-1]
    found = find_file_shortname(directory, shortname)
    if found is None:
        # really cannot find this file
        return None
    # can find this shortname, but we also need to check whether the intermediate
    # directories match
    if filename in found:
        return found
    else:
        return None


def parse_function_invocation(invocation_str: str, logger: Logger | None=None) -> tuple[str, list[str]]:
    try:
        tree = ast.parse(invocation_str)
        expr = tree.body[0]
        assert isinstance(expr, ast.Expr)
        call = expr.value
        assert isinstance(call, ast.Call)
        func = call.func
        assert isinstance(func, ast.Name)
        function_name = func.id
        arguments = [ast.unparse(arg) for arg in call.args]
        # clean up spaces or quotes, just in case
        arguments = [arg.strip().strip("'").strip('"') for arg in arguments]

        # candidate refactoring
        if logger is not None:
            try:
                new_arguments = [ast.literal_eval(x) for x in arguments]
                if new_arguments != arguments:
                    log_and_print(
                        logger,
                        f"Refactored invocation argument parsing gives different result on "
                        f"{invocation_str!r}: old result is {arguments!r}, new result "
                        f" is {new_arguments!r}",
                    )
            except Exception as e:
                log_and_print(
                    logger,
                    f"Refactored invocation argument parsing failed on {invocation_str!r}: {e!s}",
                )
    except Exception as e:
        raise ValueError(f"Invalid function invocation: {invocation_str}") from e

    return function_name, arguments
