import json
from collections import Counter

from tenacity import retry, stop_after_attempt

from app.data_structures import MessageThread
from app.model import common

SYSTEM_PROMPT = (
    "You are a pull request reviewer. You need to choose the one PR from multiple that"
    " actually will resolve the given issue."
)


@retry(stop=stop_after_attempt(3))
def run(
    issue_statement: str, patch_contents: list[str]
) -> tuple[int, str, MessageThread]:
    model = common.MODEL_HUB["gpt-4-0125-preview"]
    model.setup()

    prefix_thread = MessageThread()
    prefix_thread.add_system(SYSTEM_PROMPT)

    issue_prompt = f"Here is the issue: <issue>{issue_statement}</issue>.\n"
    prefix_thread.add_user(issue_prompt)

    prefix_thread.add_user("First, please analyze the root cause of the issue.")

    response, *_ = model.call(prefix_thread.to_msg(), temperature=1.0)
    prefix_thread.add_model(response)

    prefix_thread.add_user("Analyze how to resolve the issue.")

    response, *_ = model.call(prefix_thread.to_msg())
    prefix_thread.add_model(response)

    prefix_thread.add_user("Here are some patches:")

    for idx, content in enumerate(patch_contents, start=1):
        prefix_thread.add_user(f"Patch {idx}:\n{content}")

    question = (
        "Based on your analysis, "
        "think about which patch best resolves the issue. Tell me the number of"
        " the patch as well as the reason you choose it. Provide your answer in"
        " the following json format:\n"
        "\n"
        "```\n"
        "{\n"
        '    "patch_number": ...,\n'
        '    "reason": "..."'
        "}\n"
        "```\n"
        "where `patch_number` is one of the patch numbers, and reason is a string"
        " stating the reason to your choice."
    )
    prefix_thread.add_user(question)

    prefix_thread.add_user(
        "NOTE: the patch should only do what is necessary to address the issue. If multiple"
        " patches look reasonable, choose the one that makes the least changes."
    )

    indices = Counter()

    reason = ""
    responses = []
    for _ in range(3):
        response, *_ = model.call(
            prefix_thread.to_msg(), response_format="json_object", n=3
        )
        responses.append(response)

        try:
            data = json.loads(response)
            index = int(data["patch_number"]) - 1
            reason = data["reason"]
        except Exception:
            index = 0

        indices[index] += 1

    for r in responses:
        prefix_thread.add_model(r)

    index = indices.most_common(1)[0][0]

    if index >= len(patch_contents):
        raise RuntimeError("out-of-bound patch selection by LLM")

    return index, reason, prefix_thread
