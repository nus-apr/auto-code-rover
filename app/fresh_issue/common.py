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

    def __init__(
        self,
        task_id: str,
        clone_link: str,
        commit_hash: str,
        issue_link: str,
        setup_dir: str,
        task_output_dir: str,
    ):
        self.task_id = task_id
        self.clone_link = clone_link
        self.commit_hash = commit_hash
        self.issue_link = issue_link
        # where to store output of ACR
        self.task_output_dir = task_output_dir
        # where the project source code is located
        self.project_dir = self.setup_task_local(setup_dir)
        self.problem_stmt, self.created_at = self.prepare_issue()
        self.write_meta_file()

    def setup_task_local(self, setup_dir: str):
        """
        Clone and check out the target project locally.
        """
        # we are going to clone to this path - make sure it is not there yet
        cloned_path = pjoin(setup_dir, self.task_id)
        if os.path.isdir(cloned_path):
            print(
                f"Path {cloned_path} already exists. Removing it to get a fresh clone."
            )
            shutil.rmtree(cloned_path)
        # really clone the repo
        cloned_path = apputils.clone_repo_and_checkout(
            self.clone_link, self.commit_hash, setup_dir, self.task_id
        )
        print(f"Cloned source code to {cloned_path}.")
        return cloned_path

    def prepare_issue(self):
        """
        Prepare problem statement from the online issue report.
        """
        if "github.com" in self.issue_link:
            retrieved_issue = github.get_github_issue_info(self.issue_link)
            if retrieved_issue is None:
                raise Exception(
                    f"Failed to retrieve issue information from {self.issue_link}"
                )
            else:
                title, body, created_at = retrieved_issue
                problem_stmt = title + "\n" + body
                # save this issue into a file for reference
                problem_stmt_file = pjoin(self.task_output_dir, "problem_statement.txt")
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
