import json
import os
import shutil
from os.path import join as pjoin

from app import utils as apputils
from app.fresh_issue import github


class FreshTask:
    """
    Encapsulate everything required to run ACR on a fresh issue from the internet.
    """

    def __init__(self, task_id: str, task_output_dir: str):
        self.task_id = task_id
        self.task_output_dir = task_output_dir
        # should be set up later on
        self.project_dir = None
        self.problem_stmt = None
        self.created_at = None
        self.commit_hash = None

    @classmethod
    def construct_from_online(
        cls,
        task_id: str,
        task_output_dir: str,
        clone_link: str,
        commit_hash: str,
        issue_link: str,
        setup_dir: str,
    ):
        task = cls(task_id, task_output_dir)
        task.commit_hash = commit_hash
        task.project_dir = cls.online_task_setup_local(
            clone_link, commit_hash, task_id, setup_dir
        )
        task.problem_stmt, task.created_at = cls.online_task_prepare_issue(
            issue_link, task_output_dir
        )
        task.write_meta_file()
        return task

    @classmethod
    def construct_from_local(
        cls, task_id: str, task_output_dir: str, project_dir: str, issue_file: str
    ):
        task = cls(task_id, task_output_dir)
        task.project_dir = project_dir
        task.problem_stmt = cls.read_issue_file(issue_file)
        # for local issue, we also want a commit hash for it for compatibility
        with apputils.cd(project_dir):
            if not apputils.is_git_repo():
                # non git repo - let's make it a git repo first
                apputils.initialize_git_repo_and_commit()
            task.commit_hash = apputils.get_current_commit_hash()
        task.write_meta_file()
        return task

    @staticmethod
    def read_issue_file(issue_file: str):
        with open(issue_file) as f:
            issue = f.read()
        return issue

    @staticmethod
    def online_task_setup_local(
        clone_link: str, commit_hash: str, task_id: str, setup_dir: str
    ):
        """
        Clone and check out the target project locally.
        """
        # we are going to clone to this path - make sure it is not there yet
        cloned_path = pjoin(setup_dir, task_id)
        if os.path.isdir(cloned_path):
            print(
                f"Path {cloned_path} already exists. Removing it to get a fresh clone."
            )
            shutil.rmtree(cloned_path)
        # really clone the repo
        cloned_path = apputils.clone_repo_and_checkout(
            clone_link, commit_hash, setup_dir, task_id
        )
        print(f"Cloned source code to {cloned_path}.")
        return cloned_path

    @staticmethod
    def online_task_prepare_issue(issue_link: str, task_output_dir: str):
        """
        Prepare problem statement from the online issue report.
        """
        if "github.com" in issue_link:
            retrieved_issue = github.get_github_issue_info(issue_link)
            if retrieved_issue is None:
                raise Exception(
                    f"Failed to retrieve issue information from {issue_link}"
                )
            else:
                title, body, created_at = retrieved_issue
                problem_stmt = f"{title}\n{body}"
                # save this issue into a file for reference
                problem_stmt_file = pjoin(task_output_dir, "problem_statement.txt")
                with open(problem_stmt_file, "w") as f:
                    f.write(problem_stmt)
                return problem_stmt, created_at
        else:
            raise NotImplementedError("Only GitHub issues are supported for now.")

    def write_meta_file(self):
        """
        Write a meta file for compatibility reasons with the swe-bench mode.
        """
        meta_file = pjoin(self.task_output_dir, "meta.json")
        meta = {
            "task_info": {
                "base_commit": self.commit_hash,
                "created_at": self.created_at,
                "problem_statement": self.problem_stmt,
                "instance_id": self.task_id,
            },
            "setup_info": {
                "repo_path": self.project_dir,
            },
        }
        with open(meta_file, "w") as f:
            json.dump(meta, f, indent=4)
