# AutoCodeRover Replay

`replay.py` is used to replay an AutoCodeRover session.

## Setup

```
pip install -r scripts/replay/requirements.txt
```

## Usage

```
> python scripts/replay/replay.py
usage: replay.py [-h] [-r REPLAY] [-m MAKE_HISTORY]

Console Inference of LLM models. Works with any OpenAI compatible server.

options:
  -h, --help            show this help message and exit
  -r REPLAY, --replay REPLAY
                        json file of conversation history
  -m MAKE_HISTORY, --make-history MAKE_HISTORY
                        make history from individual expr directory
```

Example:

```
> python scripts/replay/replay.py -m results/acr-run-1/applicable_patch/django__django-11001_2024-04-06_13-25-06/
Using main conversation: results/acr-run-1/applicable_patch/django__django-11001_2024-04-06_13-25-06/conversation_round_4.json
Using patch agent conversation results/acr-run-1/applicable_patch/django__django-11001_2024-04-06_13-25-06/debug_agent_write_patch_1.json

History extracted successfully: results/acr-run-1/applicable_patch/django__django-11001_2024-04-06_13-25-06/history.json

> python scripts/replay/replay.py -r results/acr-run-1/applicable_patch/django__django-11001_2024-04-06_13-25-06/history.json

```
