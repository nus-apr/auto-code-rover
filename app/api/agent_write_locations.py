"""
An agent, which is only responsible for the summarize locations tool call.
"""

import json
import re
from collections.abc import Callable
from copy import deepcopy
from os.path import join as pjoin
from pathlib import Path

from loguru import logger

from app.api import agent_common
from app.data_structures import MessageThread
from app.log import print_acr, print_fix_loc_generation
from app.model import common
from app.task import Task

SYSTEM_PROMPT = """You are a software developer maintaining a large project.
You are working on an issue submitted to your project.
The issue contains a description marked between <issue> and </issue>.
You ultimate goal is to write a list of locations that you can give to another developer.
"""


USER_PROMPT_INIT = """Write a list of fix locations, based on the retrieved context.\n\n
Return the list of locations in the format below.\n\nWithin `<file></file>`, replace `...` with actual file path. Within `<class></class>`, replace `...` with a class name if needed. Within `<method></method`, replace `...` with a method name.\n\n
You can write multiple locations if needed.

```
# candidate 1
<file>...</file>
<class>...</class>
<method>...</method>


# candidate 2
<file>...</file>
<class>...</class>
<method>...</method>

# candidate 3
...
```
"""


def run_with_retries(
    message_thread: MessageThread,
    output_dir: str,
    task: Task,
    retries=3,
    print_callback: Callable[[dict], None] | None = None,
) -> tuple[str, float, int, int]:
    """
    Since the agent may not always write a correct list, we allow for retries.
    This is a wrapper around the actual run.
    """
    # (1) replace system prompt
    messages = deepcopy(message_thread.messages)
    new_thread: MessageThread = MessageThread(messages=messages)
    new_thread = agent_common.replace_system_prompt(new_thread, SYSTEM_PROMPT)

    # (2) add the initial user prompt
    new_thread.add_user(USER_PROMPT_INIT)
    print_acr(
        USER_PROMPT_INIT, "fix location generation", print_callback=print_callback
    )

    can_stop = False
    result_msg = ""

    logger.info("Starting the agent to propose fix locations.")

    for i in range(1, retries + 2):
        if i > 1:
            debug_file = pjoin(output_dir, f"debug_agent_propose_locs_{i - 1}.json")
            with open(debug_file, "w") as f:
                json.dump(new_thread.to_msg(), f, indent=4)

        if can_stop or i > retries:
            break

        logger.info(f"Trying to propose fix locations. Try {i} of {retries}.")

        raw_location_file = pjoin(output_dir, f"agent_loc_list_{i}")

        # actually calling model
        res_text, *_ = common.SELECTED_MODEL.call(new_thread.to_msg())

        new_thread.add_model(res_text, [])  # no tools

        logger.info(f"Fix locations produced in try {i}. Writing locations into file.")

        with open(raw_location_file, "w") as f:
            f.write(res_text)

        # print("HI", raw_location_file)

        print_fix_loc_generation(
            res_text, f"try {i} / {retries}", print_callback=print_callback
        )

        fragment_pattern = re.compile(
            r"<file>(.*?)</file>\s*<class>(.*?)</class>\s*<method>(.*?)</method>"
        )

        result_msg = "No fragments found"
        res = []
        for match in fragment_pattern.finditer(res_text):
            res.append(
                {
                    "file": match.group(1),
                    "class": match.group(2),
                    "method": match.group(3),
                }
            )
            result_msg = "Found fragments"

        can_stop = res != []
        Path(output_dir, f"agent_fix_locations_{i}.json").write_text(
            json.dumps(res, indent=4)
        )
    return result_msg
