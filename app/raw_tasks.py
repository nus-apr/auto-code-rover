import json
from os.path import join as pjoin

import requests

from app.task import GithubTask, SweTask


class RawSweTask:
    """
    Encapsulate everything required to run one task.
    """

    def __init__(self, task_id: str, setup_info: dict, task_info: dict):
        # a counter str, format "1/150", which means first task out of 150
        # id from the benchmark
        self.task_id = task_id
        # setup_info (Dict): keys: ['repo_path', 'env_name', 'pre_install', 'install','test_cmd']
        self.setup_info = setup_info
        # task_info (Dict): keys: ['base_commit', 'hints_text', 'created_at',
        # 'test_patch', 'repo', 'problem_statement', 'version', 'instance_id',
        # 'FAIL_TO_PASS', 'PASS_TO_PASS', 'environment_setup_commit']
        self.task_info = task_info

    def to_task(self) -> SweTask:
        task_id = self.task_id
        setup_info = self.setup_info
        task_info = self.task_info
        return SweTask(
            task_id=task_id,
            problem_statement=task_info["problem_statement"],
            repo_path=setup_info["repo_path"],
            env_name=setup_info["env_name"],
            pre_install_cmds=setup_info["pre_install"],
            install_cmd=setup_info["install"],
            # command to run the relevant tests,
            test_cmd=setup_info["test_cmd"],
            commit=task_info["base_commit"],
            repo_name=task_info["repo"],
            # modifications to the test suite for this task instance,
            test_patch=task_info["test_patch"],
            testcases_passing=task_info["PASS_TO_PASS"],
            testcases_failing=task_info["FAIL_TO_PASS"],
        )

    def dump_meta_data(self, task_output_dir: str):
        meta = {
            "task_id": self.task_id,
            "setup_info": self.setup_info,
            "task_info": self.task_info,
        }
        with open(pjoin(task_output_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=4)
        with open(pjoin(task_output_dir, "problem_statement.txt"), "w") as f:
            f.write(self.task_info["problem_statement"])
        with open(pjoin(task_output_dir, "developer_patch.diff"), "w") as f:
            f.write(self.task_info["patch"])


class RawGithubTask:
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
    ):
        self.task_id = task_id
        self.clone_link = clone_link
        self.commit_hash = commit_hash
        self.issue_link = issue_link
        self.setup_dir = setup_dir
        self.clone_path = pjoin(self.setup_dir, self.task_id)
        self.problem_statement, self.created_at = self.fetch_issue()

    def dump_meta_data(self, task_output_dir: str):
        meta = {
            "task_info": {
                "base_commit": self.commit_hash,
                "created_at": self.created_at,
                "problem_statement": self.problem_statement,
                "instance_id": self.task_id,
            },
            "setup_info": {
                "repo_path": self.clone_path,
            },
        }

        meta_file = pjoin(task_output_dir, "meta.json")

        with open(meta_file, "w") as f:
            json.dump(meta, f, indent=4)

    def fetch_issue(self):
        if "github.com" not in self.issue_link:
            raise NotImplementedError("Only GitHub issues are supported for now.")

        retrieved_issue = self.fetch_github_issue(self.issue_link)

        if retrieved_issue is None:
            raise RuntimeError(
                f"Failed to retrieve issue information from {self.issue_link}"
            )

        title, body, created_at = retrieved_issue

        problem_statement = title + "\n" + body

        return problem_statement, created_at

    @classmethod
    def fetch_github_issue(cls, issue_url: str) -> tuple[str, str, str]:
        """Extract owner, repo, and issue number from the URL"""

        # Example issue URL: https://github.com/owner/repo/issues/123

        _, owner, repo, _, issue_number = issue_url.rsplit("/", 4)

        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        response = requests.get(api_url)

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch issue information: {response.status_code}"
            )

        issue_info = response.json()

        title = issue_info["title"]
        body = issue_info["body"]
        created_at = issue_info["created_at"]

        return title, body, created_at

    def to_task(self) -> GithubTask:
        return GithubTask(
            clone_link=self.clone_link,
            commit_hash=self.commit_hash,
            clone_path=self.clone_path,
            problem_statement=self.problem_statement,
        )
