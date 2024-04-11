import argparse
import json
import os
import random
import re
import time
from glob import glob
from os.path import basename, join
from pathlib import Path

import tiktoken
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

ENCODING = tiktoken.get_encoding("cl100k_base")


def terminal_width():
    terminal_size = os.get_terminal_size()
    return terminal_size.columns


def remove_lines_console(num_lines):
    for _ in range(num_lines):
        # print("\x1b[A" + " " * terminal_width(), end="\r", flush=True)
        print("\x1b[A", end="\r", flush=True)


def estimate_lines(text):
    columns, _ = os.get_terminal_size()
    line_count = 1
    text_lines = text.split("\n")
    for text_line in text_lines:
        lines_needed = (len(text_line) // columns) + 1

        line_count += lines_needed

    return line_count


class conchat:
    def __init__(self, history) -> None:
        self.console = Console()
        self.history = history

    def tokenize_and_yield(self, s):
        enc = ENCODING.encode(s)
        tokens = [ENCODING.decode([token]) for token in enc]
        n = len(tokens)
        idx = 0
        while idx < n:
            # for idx in range(n - 1):
            k = random.randint(1, 8)
            end_idx = idx + k
            yield "".join(tokens[idx:end_idx]), end_idx >= n
            idx += k
            time.sleep(random.random() * 0.00)
        # yield tokens[n - 1], True

    def handle_streaming(self, content, title, color):
        stream = self.tokenize_and_yield(content)
        text = ""
        block = "█ "
        with Live(console=self.console, refresh_per_second=1000) as live:
            for token, is_last in stream:
                text = text + token
                if is_last:
                    block = ""
                markdown = Markdown(text + block)
                panel = Panel(
                    markdown,
                    title=title,
                    title_align="left",
                    border_style=color,
                    width=terminal_width() * 2 // 3,
                )
                unit = terminal_width() * 1 // 6 - 5
                if "rover" in title.lower():
                    level = 0
                elif "context" in title.lower():
                    level = 1
                else:
                    level = 2

                columns = Columns([" " * unit * level, panel], column_first=True)
                live.update(
                    columns,
                    refresh=True,
                )

    def chat(self):
        for msg in self.history:
            try:
                self.handle_streaming(
                    content=msg["content"].strip(),
                    title=msg["title"],
                    color=msg["color"],
                )
                if msg.get("stop", None):
                    input()
            # NOTE: Ctrl + c (keyboard) or Ctrl + d (eof) to exit
            # Adding EOFError prevents an exception and gracefully exits.
            except (KeyboardInterrupt, EOFError):
                exit()


def replay(history_file):
    with open(history_file) as f:
        history = json.load(f)

    chat = conchat(history=history)
    chat.chat()


def make_history(dir):
    main_conv_file = sorted(
        glob(
            join(dir, "conversation_round_*.json"),
        ),
        key=lambda s: int(
            basename(s).removeprefix("conversation_round_").removesuffix(".json")
        ),
    )[-1]

    agent_patch_file = sorted(
        glob(
            join(dir, "debug_agent_write_patch_*.json"),
        ),
        key=lambda s: int(
            basename(s).removeprefix("debug_agent_write_patch_").removesuffix(".json")
        ),
    )[-1]

    print("Using main conversation:", main_conv_file)
    print("Using patch agent conversation", agent_patch_file)
    print()

    retrieval_data = json.loads(Path(main_conv_file).read_text())
    patch_data = json.loads(Path(agent_patch_file).read_text())

    history = []

    name_main = "💻 AutoCodeRover"
    name_context_retriever = "🔎 Context Retrieval Agent"
    name_patch_generator = "💊 Patch Generation Agent"

    for msg in retrieval_data:
        if msg["role"] == "user":
            content = re.sub(
                r"(search result \d+:)", r"\n\1\n\n", msg["content"], flags=re.I
            )
            if content.startswith("Based on your analysis, answer below questions:"):
                content = (
                    "Based on your analysis, answer below questions:\n"
                    "    - do we need more context: construct search API calls to get more context of the project. (leave it empty if you don't need more context)\n"
                    "    - where are bug locations: buggy files and methods. (leave it empty if you don't have enough information)"
                )
            if content.startswith("Based on the files"):
                content = """Based on the files, classes, methods, code statements from the issue that related to the bug, you can use below search APIs to get more context of the project.
            

        - search_class(class_name: str): Search for a class in the codebase.

        - search_method_in_file(method_name: str, file_path: str): Search for a method in a given file.
        
        - search_method_in_class(method_name: str, class_name: str): Search for a method in a given class.

        - search_method(method_name: str): Search for a method in the entire codebase.

        - search_code(code_str: str): Search for a code snippet in the entire codebase.

        - search_code_in_file(code_str: str, file_path: str): Search for a code snippet in a given file file.

Note that you can use multiple search APIs in one round.

Now analyze the issue and select necessary APIs to get more context of the project, each API call must have concrete arguments as inputs.
        """

            content = (
                content.replace(r"<file>", "&lt;file&gt;")
                .replace(r"<class>", "&lt;class&gt;")
                .replace(r"<func>", "&lt;func&gt;")
                .replace(r"<code>", "&lt;code&gt;\n```")
                .replace(r"</file>", "&lt;/file&gt;\n\n")
                .replace(r"</class>", "&lt;/class&gt;\n\n")
                .replace(r"</func>", "&lt;/func&gt;\n\n")
                .replace(r"</code>", "\n```\n&lt;/code&gt;\n\n")
            )

            content = re.sub(r"Other results are in these files:\s+\n", "", content)

            if content.startswith("Based on your analysis, answer below questions:"):
                content = content.replace("- do we need", "\n  - do we need").replace(
                    "- where are", "\n  - where are"
                )

            history.append(dict(title=name_main, content=content, color="white"))
        elif msg["role"] == "assistant":
            history.append(
                dict(
                    title=name_context_retriever,
                    content=msg["content"],
                    color="blue",
                )
            )

    start = False
    for msg in patch_data:
        if msg["content"].startswith("Write a patch for the issue"):
            start = True
        if not start:
            continue

        if msg["role"] == "user":
            content = msg["content"]
            content = (
                content.replace(r"<file>", "&lt;file&gt;")
                .replace(r"<class>", "&lt;class&gt;")
                .replace(r"<func>", "&lt;method&gt;")
                .replace(r"<code>", "&lt;code&gt;\n```")
                .replace(r"</file>", "&lt;/file&gt;\n\n")
                .replace(r"</class>", "&lt;/class&gt;\n\n")
                .replace(r"</func>", "&lt;/func&gt;\n\n")
                .replace(r"</code>", "\n```\n&lt;/code&gt;\n\n")
            )
            history.append(dict(title=name_main, content=content, color="white"))
        elif msg["role"] == "assistant":
            history.append(
                dict(
                    title=name_patch_generator,
                    content=msg["content"],
                    color="yellow",
                )
            )

    out_file = Path(dir, "history.json")
    with open(out_file, "w") as f:
        json.dump(history, f, indent=4)

    print("History extracted successfully:", out_file)


def main():
    parser = argparse.ArgumentParser(
        description="Console Inference of LLM models. Works with any OpenAI compatible server."
    )
    parser.add_argument(
        "-r",
        "--replay",
        help="json file of conversation history",
        type=str,
    )
    parser.add_argument(
        "-m", "--make-history", help="make history from individual expr directory"
    )

    args = parser.parse_args()

    if args.replay:
        replay(args.replay)
        return

    if args.make_history:
        make_history(args.make_history)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
