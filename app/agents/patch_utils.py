"""
Utility functions for parsing and applying the patch.

Inspired by:
https://github.com/gpt-engineer-org/gpt-engineer/blob/main/gpt_engineer/core/chat_to_files.py
"""

import re
from dataclasses import dataclass
from pprint import pformat
from tempfile import NamedTemporaryFile
from typing import TextIO

from pylint.lint import Run
from pylint.reporters.text import TextReporter


@dataclass
class Edit:
    filename: str
    before: str
    after: str

    def __str__(self):
        return f"{self.filename}\nBefore:\n{pformat(self.before)}\nAfter:\n{pformat(self.after)}\n"

    def __repr__(self):
        return str(self)


def parse_edits(chat_string: str) -> list[Edit]:
    """
    Parse edits from a chat string.

    This function extracts code edits from a chat string and returns them as a list
    of Edit objects.

    Args:
        chat_string (str): The chat content containing code edits.

    Returns:
        List[Edit]: A list of Edit objects representing the parsed code edits.
    """

    def parse_in_fence(lines: list[str]):
        """
        New version of parsing multiple edits within one fence.
        """
        # remove obviously suspicious lines
        sus_contents = ["# Rest of the code..."]
        lines = [line for line in lines if line.strip() not in sus_contents]

        file_start = "<file>"
        file_end = "</file>"
        original_start = "<original>"
        original_end = "</original>"
        patched_start = "<patched>"
        patched_end = "</patched>"

        all_edits: list[Edit] = []
        content = "\n".join(lines)

        # use regex to find content between <file> and </file>
        file_pattern = re.compile(f"{file_start}(.*?){file_end}", re.DOTALL)
        original_pattern = re.compile(f"{original_start}(.*?){original_end}", re.DOTALL)
        patched_pattern = re.compile(f"{patched_start}(.*?){patched_end}", re.DOTALL)

        file_matches = file_pattern.findall(content)
        original_matches = original_pattern.findall(content)
        patched_matches = patched_pattern.findall(content)

        for file, original, patched in zip(
            file_matches, original_matches, patched_matches
        ):
            # for file, we strip all spaces
            file = file.strip()
            # for original and patched, keep the spaces, since removing spaces at beginning or end
            # may mess up indentation level on some of the lines.
            # However, we should remove the new lines at start and end. These new lines may be
            # inserted by the model, but if in the original code there are no such new lines before
            # the actual code, this can result in non-match
            original = original.strip("\n")
            patched = patched.strip("\n")
            all_edits.append(Edit(file, original, patched))

        return all_edits

    edits = []
    current_edit = []
    in_fence = False

    for line in chat_string.split("\n"):
        if line.startswith("```") and in_fence:
            edits.extend(parse_in_fence(current_edit))
            current_edit = []
            in_fence = False
            continue
        elif line.startswith("```") and not in_fence:
            in_fence = True
            continue
        if in_fence:
            current_edit.append(line)

    return edits


def apply_edit(edit: Edit, file_path: str) -> str | None:
    """
    Apply one Edit to a file. This function reads the file, tries to match
    the before string (after stripping spaces in the original program and the
    before string improve the chance of matching), and then replaces the matched region with the after string.
    Returns:
        - Path to the file containing updated content if successful;
          None otherwise.
    """
    with open(file_path) as f:
        orig_prog_lines = f.readlines()

    before = edit.before
    after = edit.after

    # check whether before is in the original program
    before_lines = before.split("\n")
    # NOTE: These are just for matching; do not use to form back the program
    cleaned_before_lines = [line.strip() for line in before_lines]
    cleaned_orig_lines = [line.strip() for line in orig_prog_lines]
    # match before in the original program
    match_start = -1
    match_end = -1
    for i in range(len(cleaned_orig_lines) - len(cleaned_before_lines) + 1):
        # check all possible starting positions in the orig program
        if (
            cleaned_orig_lines[i : i + len(cleaned_before_lines)]
            == cleaned_before_lines
        ):
            match_start = i
            match_end = i + len(cleaned_before_lines)
            break
    if match_start == -1:
        # cound not find a match
        return None

    # found a match, replace the matched region with after

    # First guess: in the patch, the indentation difference between the first line and
    # subsequent lines are correct. In this case, first calculate the indentation difference
    # between the first line of patch & original file; subsequent lines are all prepended with
    # this difference.
    matched_orig_region = orig_prog_lines[match_start:match_end]
    after_lines = after.split("\n")

    if before_lines[0] in matched_orig_region[0]:
        abs_indent_of_first_line = matched_orig_region[0].index(before_lines[0])
        fixed_after_lines = [
            " " * abs_indent_of_first_line + line for line in after_lines
        ]
    else:
        # will raise if cannot find
        abs_indent_of_first_line = before_lines[0].index(
            matched_orig_region[0].rstrip("\n")
        )
        fixed_after_lines = [line[abs_indent_of_first_line:] for line in after_lines]

    # form the new program
    prefix = "".join(orig_prog_lines[:match_start])
    suffix = "".join(orig_prog_lines[match_end:])

    new_prog_1 = prefix + "\n".join(fixed_after_lines) + "\n" + suffix

    # Second guess: the absolute indentation of the second to last lines are correct. In this case,
    # simply fix the indentation of the first line.
    fixed_after_lines[1:] = after_lines[1:]
    new_prog_2 = prefix + "\n".join(fixed_after_lines) + "\n" + suffix

    if lint_python_content(new_prog_1):
        new_prog = new_prog_1
    elif lint_python_content(new_prog_2):
        new_prog = new_prog_2
    else:
        return None

    with open(file_path, "w") as f:
        f.write(new_prog)

    return file_path


class Writable(TextIO):
    "dummy output stream for pylint"

    def __init__(self) -> None:
        self.content: list[str] = []

    def write(self, s: str) -> int:
        self.content.append(s)
        return len(s)

    def read(self, n: int = 0) -> str:
        return "\n".join(self.content)


def lint_python_content(content: str) -> bool:
    """Check if python content lints OK.

    Args:
        content: python file content

    Returns: True if the contents passes linting, False otherwise.

    """
    pylint_out = Writable()
    reporter = TextReporter(pylint_out)

    with NamedTemporaryFile(buffering=0) as f:
        f.write(content.encode())

        _ = Run(["--errors-only", f.name], reporter=reporter, exit=False)

    return not any(error.endswith("(syntax-error)") for error in pylint_out.content)
