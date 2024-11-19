from __future__ import annotations

import json
from collections.abc import Generator
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum

from loguru import logger

from app.agents.agent_common import InvalidLLMResponse
from app.data_structures import MessageThread, ReproResult
from app.model import common

# TEMP, for testing

SYSTEM_PROMPT = (
    "You are an experienced software engineer responsible for maintaining a project."
    "An issue has been submitted. "
    "Engineer A has written a reproduction test for the issue. "
    "Engineer B has written a patch for the issue. "
    "Your task is to decide whether the created patch resolves the issue."
    "NOTE: both the test and the patch may be wrong."
)

INITIAL_REQUEST = ()


@dataclass
class Review:
    patch_decision: ReviewDecision
    patch_analysis: str
    patch_advice: str
    test_decision: ReviewDecision
    test_analysis: str
    test_advice: str

    def __str__(self):
        return (
            f"Patch decision: {self.patch_decision.value}\n\n"
            f"Patch analysis: {self.patch_analysis}\n\n"
            f"Patch advice: {self.patch_advice}\n\n"
            f"Test decision: {self.test_decision.value}\n\n"
            f"Test analysis: {self.test_analysis}\n\n"
            f"Test advice: {self.test_advice}"
        )

    def to_json(self):
        return {
            "patch-correct": self.patch_decision.value,
            "patch-analysis": self.patch_analysis,
            "patch-advice": self.patch_advice,
            "test-correct": self.test_decision.value,
            "test-analysis": self.test_analysis,
            "test-advice": self.test_advice,
        }


class ReviewDecision(Enum):
    YES = "yes"
    NO = "no"


def extract_review_result(content: str) -> Review | None:
    try:
        data = json.loads(content)

        review = Review(
            patch_decision=ReviewDecision(data["patch-correct"].lower()),
            patch_analysis=data["patch-analysis"],
            patch_advice=data["patch-advice"],
            test_decision=ReviewDecision(data["test-correct"].lower()),
            test_analysis=data["test-analysis"],
            test_advice=data["test-advice"],
        )

        if (
            (review.patch_decision == ReviewDecision.NO) and not review.patch_advice
        ) and ((review.test_decision == ReviewDecision.NO) and not review.test_advice):
            return None

        return review

    except Exception:
        return None


def run(
    issue_statement: str,
    test_content: str,
    patch_content: str,
    orig_repro: ReproResult,
    patched_repro: ReproResult,
    retries: int = 5,
) -> tuple[Review, MessageThread]:
    review_generator = run_with_retries(
        issue_statement,
        test_content,
        patch_content,
        orig_repro.stdout,
        orig_repro.stderr,
        patched_repro.stdout,
        patched_repro.stderr,
        retries=retries,
    )
    for review, thread in review_generator:
        # TODO: make output dir global, so that the raw responses can be dumped
        if review is not None:
            return review, thread

    raise InvalidLLMResponse(f"failed to review in {retries} attempts")


# TODO: remove this
def run_with_retries(
    issue_statement: str,
    test: str,
    patch: str,
    orig_test_stdout: str,
    orig_test_stderr: str,
    patched_test_stdout: str,
    patched_test_stderr: str,
    retries: int = 5,
) -> Generator[tuple[Review | None, MessageThread], None, None]:
    prefix_thread = MessageThread()
    prefix_thread.add_system(SYSTEM_PROMPT)

    issue_prompt = f"Here is the issue: <issue>{issue_statement}</issue>.\n"
    prefix_thread.add_user(issue_prompt)

    test_prompt = f"Here is the test written by Engineer A: <test>{test}</test>.\n"
    prefix_thread.add_user(test_prompt)

    orig_exec_prompt = (
        "Here is the result of executing the test on the original buggy program:\n"
        f"stdout:\n\n{orig_test_stdout}\n"
        "\n"
        f"stderr:\n\n{orig_test_stderr}\n"
        "\n"
    )

    prefix_thread.add_user(orig_exec_prompt)

    patch_prompt = f"Here is the patch written by Engineer B: <patch>{patch}</patch>.\n"
    prefix_thread.add_user(patch_prompt)

    patched_exec_prompt = (
        "Here is the result of executing the test on the patched program:\n"
        f"stdout:\n\n{patched_test_stdout}\n"
        "\n"
        f"stderr:\n\n{patched_test_stderr}."
    )
    prefix_thread.add_user(patched_exec_prompt)

    question = (
        "Think about (1) whether the test correctly reproduces the issue, and "
        "(2) whether the patch resolves the issue. "
        "Provide your answer in the following json schema:\n"
        "\n"
        "```json\n"
        "{\n"
        '    "patch-correct": "...",\n'
        '    "test-correct": "...",\n'
        '    "patch-analysis": "...",\n'
        '    "test-analysis": "...",\n'
        '    "patch-advice": "...",\n'
        '    "test-advice": "..."\n'
        "}\n"
        "```\n"
        "\n"
        'where "patch-correct"/"test-correct" is "yes" or "no"; '
        '"patch-analysis"/"test-analysis" should explain the reasoning behind your answer.\n'
        'Moreover, if your answer is "no", then give me advice about how to correct'
        ' the patch/test in the "patch-advice"/"test-advice" field.\n'
        'If your answer is "yes", you can leave "patch-advice"/"test-advice"'
        "empty.\n"
        "\n"
        "NOTE: not only the patch, but also the test case, can be wrong."
    )

    prefix_thread.add_user(question)

    for _ in range(1, retries + 1):
        response, *_ = common.SELECTED_MODEL.call(
            prefix_thread.to_msg(), response_format="json_object"
        )

        thread = deepcopy(prefix_thread)
        thread.add_model(response, [])
        # TODO: print

        logger.info(response)

        review = extract_review_result(response)

        if review is None:
            yield None, thread
            continue

        yield review, thread
        break


if __name__ == "__main__":
    pass

#     # setup before test

#     register_all_models()
#     common.set_model("gpt-4-0125-preview")

#     # TEST
#     instance_id = "matplotlib__matplotlib-23299"

#     problem_stmt = "[Bug]: get_backend() clears figures from Gcf.figs if they were created under rc_context\n### Bug summary\r\n\r\ncalling `matplotlib.get_backend()` removes all figures from `Gcf` if the *first* figure in `Gcf.figs` was created in an `rc_context`.\r\n\r\n### Code for reproduction\r\n\r\n```python\r\nimport matplotlib.pyplot as plt\r\nfrom matplotlib import get_backend, rc_context\r\n\r\n# fig1 = plt.figure()  # <- UNCOMMENT THIS LINE AND IT WILL WORK\r\n# plt.ion()            # <- ALTERNATIVELY, UNCOMMENT THIS LINE AND IT WILL ALSO WORK\r\nwith rc_context():\r\n    fig2 = plt.figure()\r\nbefore = f'{id(plt._pylab_helpers.Gcf)} {plt._pylab_helpers.Gcf.figs!r}'\r\nget_backend()\r\nafter = f'{id(plt._pylab_helpers.Gcf)} {plt._pylab_helpers.Gcf.figs!r}'\r\n\r\nassert before == after, '\\n' + before + '\\n' + after\r\n```\r\n\r\n\r\n### Actual outcome\r\n\r\n```\r\n---------------------------------------------------------------------------\r\nAssertionError                            Traceback (most recent call last)\r\n<ipython-input-1-fa4d099aa289> in <cell line: 11>()\r\n      9 after = f'{id(plt._pylab_helpers.Gcf)} {plt._pylab_helpers.Gcf.figs!r}'\r\n     10 \r\n---> 11 assert before == after, '\\n' + before + '\\n' + after\r\n     12 \r\n\r\nAssertionError: \r\n94453354309744 OrderedDict([(1, <matplotlib.backends.backend_qt.FigureManagerQT object at 0x7fb33e26c220>)])\r\n94453354309744 OrderedDict()\r\n```\r\n\r\n### Expected outcome\r\n\r\nThe figure should not be missing from `Gcf`.  Consequences of this are, e.g, `plt.close(fig2)` doesn't work because `Gcf.destroy_fig()` can't find it.\r\n\r\n### Additional information\r\n\r\n_No response_\r\n\r\n### Operating system\r\n\r\nXubuntu\r\n\r\n### Matplotlib Version\r\n\r\n3.5.2\r\n\r\n### Matplotlib Backend\r\n\r\nQtAgg\r\n\r\n### Python version\r\n\r\nPython 3.10.4\r\n\r\n### Jupyter version\r\n\r\nn/a\r\n\r\n### Installation\r\n\r\nconda\n"

#     test = """# reproducer.py
# import matplotlib.pyplot as plt
# from matplotlib import get_backend, rc_context

# def main():
#     # Uncommenting either of the lines below would work around the issue
#     # fig1 = plt.figure()
#     # plt.ion()
#     with rc_context():
#         fig2 = plt.figure()
#     before = f'{id(plt._pylab_helpers.Gcf)} {plt._pylab_helpers.Gcf.figs!r}'
#     get_backend()
#     after = f'{id(plt._pylab_helpers.Gcf)} {plt._pylab_helpers.Gcf.figs!r}'

#     assert before == after, '\n' + before + '\n' + after

# if __name__ == "__main__":
#     main()
# """

#     patch = """diff --git a/lib/matplotlib/__init__.py b/lib/matplotlib/__init__.py
# index c268a56724..b40f1246b9 100644
# --- a/lib/matplotlib/__init__.py
# +++ b/lib/matplotlib/__init__.py
# @@ -1087,7 +1087,9 @@ def rc_context(rc=None, fname=None):
#               plt.plot(x, y)  # uses 'print.rc'

#      \"\"\"
# +    from matplotlib._pylab_helpers import Gcf
#      orig = rcParams.copy()
# +    orig_figs = Gcf.figs.copy()  # Preserve the original figures
#      try:
#          if fname:
#              rc_file(fname)
# @@ -1096,6 +1098,7 @@ def rc_context(rc=None, fname=None):
#          yield
#      finally:
#          dict.update(rcParams, orig)  # Revert to the original rcs.
# +        Gcf.figs.update(orig_figs)  # Restore the original figures


#  def use(backend, *, force=True):"""

#     # run_with_retries(problem_stmt, test, patch)

#     success = False

#     for attempt_idx, (raw_response, thread, review_result) in enumerate(
#         run_with_retries(problem_stmt, test, patch), start=1
#     ):

#         success |= review_result is not None

#         # dump raw results for debugging
#         Path(f"agent_reviewer_raw_{attempt_idx}.json").write_text(
#             json.dumps(thread.to_msg(), indent=4)
#         )

#         if success:
#             print(f"Success at attempt {attempt_idx}. Review result is {review_result}")
#             break

#     if not success:
#         print("Still failing to produce valid review results after 5 attempts")
