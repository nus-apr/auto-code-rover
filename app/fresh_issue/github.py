import requests


def get_github_issue_info(issue_url: str) -> tuple[str, str, str] | None:
    # Extract owner, repo, and issue number from the URL
    # Example issue URL: https://github.com/owner/repo/issues/123
    _, owner, repo, _, issue_number = issue_url.rsplit("/", 4)

    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    response = requests.get(api_url)

    if response.status_code == 200:
        issue_info = response.json()
        # Extract relevant information from the issue
        title = issue_info["title"]
        body = issue_info["body"]
        created_at = issue_info["created_at"]

        return title, body, created_at
    else:
        print(f"Failed to fetch issue information: {response.status_code}")
        return None
