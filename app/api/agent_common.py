"""
Common stuff for task agents.
"""

from app.data_structures import MessageThread


def replace_system_prompt(msg_thread: MessageThread, prompt: str) -> MessageThread:
    """
    Replace the system prompt in the message thread.
    This is because the main agent system prompt main invole tool_calls info, which
    should not be known to task agents.
    """
    msg_thread.messages[0]["content"] = prompt
    return msg_thread
