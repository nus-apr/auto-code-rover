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

### Pausing

You can specify where to pause in the replay, by adding a `stop` field to the items in history. Example:

```
[
    {
        "title": "\ud83d\udcbb AutoCodeRover",
        "content": "<issue>Incorrect removal of order_by clause created as multiline RawSQL\nDescription\nHi.\nThe SQLCompiler is ripping off one of my \"order by\" clause, because he \"thinks\" the clause was already \"seen\" (in SQLCompiler.get_order_by()). I'm using expressions written as multiline RawSQLs, which are similar but not the same.\nThe bug is located in SQLCompiler.get_order_by(), somewhere around line computing part of SQL query without ordering:\nwithout_ordering = self.ordering_parts.search(sql).group(1)\nThe sql variable contains multiline sql. As a result, the self.ordering_parts regular expression is returning just a line containing ASC or DESC words. This line is added to seen set, and because my raw queries have identical last lines, only the first clasue is returing from SQLCompiler.get_order_by().\nAs a quick/temporal fix I can suggest making sql variable clean of newline characters, like this:\nsql_oneline = ' '.join(sql.split('\\n'))\nwithout_ordering = self.ordering_parts.search(sql_oneline).group(1)\nNote: beware of unicode (Py2.x u'') and EOL dragons (\\r).\nExample of my query:\nreturn MyModel.objects.all().order_by(\nRawSQL('''\ncase when status in ('accepted', 'verification')\nthen 2 else 1 end''', []).desc(),\nRawSQL('''\ncase when status in ('accepted', 'verification')\nthen (accepted_datetime, preferred_datetime)\nelse null end''', []).asc(),\nRawSQL('''\ncase when status not in ('accepted', 'verification')\nthen (accepted_datetime, preferred_datetime, created_at)\nelse null end''', []).desc())\nThe ordering_parts.search is returing accordingly:\n'\t\t\t\t then 2 else 1 end)'\n'\t\t\t\t else null end'\n'\t\t\t\t else null end'\nSecond RawSQL with a\t\t\t\t else null end part is removed from query.\nThe fun thing is that the issue can be solved by workaround by adding a space or any other char to the last line.\nSo in case of RawSQL I can just say, that current implementation of avoiding duplicates in order by clause works only for special/rare cases (or does not work in all cases).\nThe bug filed here is about wrong identification of duplicates (because it compares only last line of SQL passed to order by clause).\nHope my notes will help you fixing the issue. Sorry for my english.\n</issue>",
        "color": "white"
    },
    {
        "title": "\ud83d\udcbb AutoCodeRover",
        "content": "Based on the files, classes, methods, code statements from the issue that related to the bug, you can use below search APIs to get more context of the project.\n            \n\n        - search_class(class_name: str): Search for a class in the codebase.\n\n        - search_method_in_file(method_name: str, file_path: str): Search for a method in a given file.\n        \n        - search_method_in_class(method_name: str, class_name: str): Search for a method in a given class.\n\n        - search_method(method_name: str): Search for a method in the entire codebase.\n\n        - search_code(code_str: str): Search for a code snippet in the entire codebase.\n\n        - search_code_in_file(code_str: str, file_path: str): Search for a code snippet in a given file file.\n\nNote that you can use multiple search APIs in one round.\n\nNow analyze the issue and select necessary APIs to get more context of the project, each API call must have concrete arguments as inputs.\n        ",
        "color": "white",
        "stop": true
    },
...
```

The replay would stop after the second message is shown. To resume, press Enter.
