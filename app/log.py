import time
from os import get_terminal_size

from loguru import logger
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


def terminal_width():
    return get_terminal_size().columns


WIDTH = min(120, terminal_width() - 10)

console = Console()

print_stdout = True


def log_exception(exception):
    logger.exception(exception)


def print_banner(msg: str) -> None:
    if not print_stdout:
        return

    banner = f" {msg} ".center(WIDTH, "=")
    console.print()
    console.print(banner, style="bold")
    console.print()


def print_acr(msg: str, desc="") -> None:
    if not print_stdout:
        return

    markdown = Markdown(msg)

    name = "AutoCodeRover"
    if desc:
        title = f"{name} ({desc})"
    else:
        title = name

    panel = Panel(
        markdown,
        title=title,
        title_align="left",
        border_style="white",
        width=WIDTH,
    )
    console.print(panel)


def print_retrieval(msg: str, desc="") -> None:
    if not print_stdout:
        return

    markdown = Markdown(msg)

    name = "Context Retrieval Agent"
    if desc:
        title = f"{name} ({desc})"
    else:
        title = name

    panel = Panel(
        markdown,
        title=title,
        title_align="left",
        border_style="blue",
        width=WIDTH,
    )
    console.print(panel)


def print_patch_generation(msg: str, desc="") -> None:
    if not print_stdout:
        return

    markdown = Markdown(msg)

    name = "Patch Generation"
    if desc:
        title = f"{name} ({desc})"
    else:
        title = name

    panel = Panel(
        markdown,
        title=title,
        title_align="left",
        border_style="yellow",
        width=WIDTH,
    )
    console.print(panel)


def log_and_print(msg):
    logger.info(msg)
    if print_stdout:
        console.print(msg)


def log_and_cprint(msg, **kwargs):
    logger.info(msg)
    if print_stdout:
        console.print(msg, **kwargs)


def log_and_always_print(msg):
    """
    A mode which always print to stdout, no matter what.
    Useful when running multiple tasks and we just want to see the important information.
    """
    logger.info(msg)
    # always include time for important messages
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    console.print(f"\n[{t}] {msg}")


def print_with_time(msg):
    """
    Print a msg to console with timestamp.
    """
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    console.print(f"\n[{t}] {msg}")
