# AutoCodeRover-v2

## Set up and running the tool

### Setup: Docker mode

Set the `OPENAI_KEY` env var to your OpenAI key:

```
export OPENAI_KEY=sk-YOUR-OPENAI-API-KEY-HERE
```

For Anthropic model, Set the `ANTHROPIC_API_KEY` env var:

```
export ANTHROPIC_API_KEY=sk-ant-api...
```

Build and start the docker image:

```
docker build -f Dockerfile -t acr .
docker run -it -e OPENAI_KEY="${OPENAI_KEY:-OPENAI_API_KEY}" acr
```

### Setup: local mode

Alternatively, you can have a local copy of AutoCodeRover and manage python dependencies with `environment.yml`.
This is the recommended setup for running SWE-bench experiments with AutoCodeRover.
With a working conda installation, do `conda env create -f environment.yml`.
Similarly, set `OPENAI_KEY` or `ANTHROPIC_API_KEY` in your shell before running AutoCodeRover.

## Running AutoCodeRover

You can run AutoCodeRover in three modes:

1. GitHub issue mode: Run ACR on a live GitHub issue by providing a link to the issue page.
2. Local issue mode: Run ACR on a local repository and a file containing the issue description.
3. SWE-bench mode: Run ACR on SWE-bench task instances. (local setup of ACR recommend.)

### [GitHub issue mode] Set up and run on new GitHub issues

If you want to use AutoCodeRover for new GitHub issues in a project, prepare the following:

- Link to clone the project (used for `git clone ...`).
- Commit hash of the project version for AutoCodeRover to work on (used for `git checkout ...`).
- Link to the GitHub issue page.

Then, in the docker container (or your local copy of AutoCodeRover), run the following commands to set up the target project
and generate patch:

```
cd /opt/auto-code-rover
conda activate auto-code-rover
PYTHONPATH=. python app/main.py github-issue --output-dir output --setup-dir setup --model gpt-4o-2024-05-13 --model-temperature 0.2 --task-id <task id> --clone-link <link for cloning the project> --commit-hash <any version that has the issue> --issue-link <link to issue page>
```

Here is an example command for running ACR on an issue from the langchain GitHub issue tracker:

```
PYTHONPATH=. python app/main.py github-issue --output-dir output --setup-dir setup --model gpt-4o-2024-05-13 --model-temperature 0.2 --task-id langchain-20453 --clone-link https://github.com/langchain-ai/langchain.git --commit-hash cb6e5e5 --issue-link https://github.com/langchain-ai/langchain/issues/20453
```

The `<task id>` can be any string used to identify this issue.

If patch generation is successful, the path to the generated patch will be written to a file named `selected_patch.json` in the output directory.

### [Local issue mode] Set up and run on local repositories and local issues

Instead of cloning a remote project and run ACR on an online issue, you can also prepare the local repository and issue beforehand,
if that suits the use case.

For running ACR on a local issue and local codebase, prepare a local codebase and write an issue description into a file,
and run the following commands:

```
cd /opt/auto-code-rover
conda activate auto-code-rover
PYTHONPATH=. python app/main.py local-issue --output-dir output --model gpt-4o-2024-05-13 --model-temperature 0.2 --task-id <task id> --local-repo <path to the local project repository> --issue-file <path to the file containing issue description>
```

If patch generation is successful, the path to the generated patch will be written to a file named `selected_patch.json` in the output directory.

### [SWE-bench mode] Set up and run on SWE-bench tasks

This mode is for running ACR on existing issue tasks contained in SWE-bench.

#### Set up

For SWE-bench mode, we recommend setting up ACR on a host machine, instead of running it in docker mode.

Firstly, set up the SWE-bench task instances locally.

1. Clone [this SWE-bench fork](https://github.com/yuntongzhang/SWE-bench) and follow the [installation instruction](https://github.com/yuntongzhang/SWE-bench?tab=readme-ov-file#to-install) to install dependencies.

2. Put the tasks to be run into a file, one per line:

```
cd <SWE-bench-path>
echo django__django-11133 > tasks.txt
```

3. Set up these tasks in the file by running:

```
cd <SWE-bench-path>
conda activate swe-bench
python harness/run_setup.py --log_dir logs --testbed testbed --result_dir setup_result --subset_file tasks.txt
```

Once the setup for this task is completed, the following two lines will be printed:

```
setup_map is saved to setup_result/setup_map.json
tasks_map is saved to setup_result/tasks_map.json
```

The `testbed` directory will now contain the cloned source code of the target project.
A conda environment will also be created for this task instance.

_If you want to set up multiple tasks together, put multiple ids in `tasks.txt` and follow the same steps._

#### Run a single task in SWE-bench

```
cd <AutoCodeRover-path>
conda activate auto-code-rover
PYTHONPATH=. python app/main.py swe-bench --model gpt-4o-2024-05-13 --setup-map <SWE-bench-path>/setup_result/setup_map.json --tasks-map <SWE-bench-path>/setup_result/tasks_map.json --output-dir output --task django__django-11133
```

The output for a run (e.g. for `django__django-11133`) can be found at a location like this: `applicable_patch/django__django-11133_yyyy-MM-dd_HH-mm-ss/` (the date-time field in the directory name will be different depending on when the experiment was run).

Path to the final generated patch is written in a file named `selected_patch.json` in the output directory.

#### Run multiple tasks in SWE-bench

First, put the id's of all tasks to run in a file, one per line. Suppose this file is `tasks.txt`, the tasks can be run with

```
cd <AutoCodeRover-path>
conda activate auto-code-rover
PYTHONPATH=. python app/main.py swe-bench --model gpt-4o-2024-05-13 --setup-map <SWE-bench-path>/setup_result/setup_map.json --tasks-map <SWE-bench-path>/setup_result/tasks_map.json --output-dir output --task-list-file <SWE-bench-path>/tasks.txt
```

**NOTE**: make sure that the tasks in `tasks.txt` have all been set up in SWE-bench, before running inference on them.

#### Using a config file

Alternatively, a config file can be used to specify all parameters and tasks to run. See `conf/example.conf` for an example.
Also see [EXPERIMENT.md](EXPERIMENT.md) for the details of the items in a conf file.
A config file can be used by:

```
python scripts/run.py conf/example.conf
```

## Contacts

> [!NOTE]
> If you encounter any issue in the tool or experiment, you can contact us via email at info@autocoderover.dev, or through our [discord server](https://discord.com/invite/ScXsdE49JY).
