# Replicating results on SWE-bench-lite

## Setup

### Docker

We have built a docker image with all task instances environment in it (it's a large image ~25GB!).
With this image, you can directly start an experiment run.

```
docker pull yuntongzhang/auto-code-rover:experiment
```

## Experiment preparation

Start a container:

```
docker run -it yuntongzhang/auto-code-rover:experiment
```

Activate the conda environment in it.

```
conda activate auto-code-rover
```

Set some temp git info:

```
git config --global user.email acr@nus.edu.sg
git config --global user.name acr
```

In the container, specify your OpenAI key in the `OPENAI_KEY` environment variable:

```
export OPENAI_KEY=xx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Run!

In the `/opt/auto-code-rover/` directory in the container, issue the following command to start
the experiment run using `gpt-4-0125-preview` on SWE-bench-lite.
(From our experience, one run with `gpt-4-0125-preview` on the 300 instances costs <150 USD on OpenAI API.)

```
python scripts/run.py conf/vanilla-lite.conf
```

This command runs auto-code-rover on the 300 instances in SWE-bench-lite, and runs the SWE-bench
evaluation on the generated patches. The final results of the experiment will be at
`/opt/auto-code-rover/experiment/vanilla-lite/final_report.json`.


### Running experiments multiple times

When running multiple experiments (sequentially), we recommend using a different `id` in the conf
file for each experiment. This is because the outputs for an experiment will be created in a directory
using `id` as the name.

If you want to use the same `id` for multiple experiments and overwrite the previous experiment results,
you can use the `-f` option of `scripts/run.py`. This will remove the previous experiment results with
the same `id`.


### Note on running experiments in parallel

We do not recommend creating multiple processes running the script `scripts/run.py`. This is because
different tasks instances may share the same copy of local code base (e.g. `astropy-6938` and
`astropy-7746` share the same codebase at `setup_astropy__astropy__1.3`).

Instead, we support parallelism of experiments in `scripts/run.py` itself. Please set the value
of `num_processes` in the conf file to control how many tasks can be run in parallel. The scripts
internally handle the parallelism issue mentioned above.


### Changing the conf file

You can modify the `conf/vanilla-lite.conf` file to set parameters such as model temperature etc.
Here are a few useful fields in the conf file:

- id: determines the name of the experiment output folder
- experiment_dir: where output will be stored
- setup_result_dir: must point to the directory where SWE-bench setup writes its results
- eval_log_dir: where the SWE-bench evaluation log is written to

- model: the model to be used by auto-code-rover
- temperature: model temperature
- conv_round_limit: rounds limit for the conversation with context retrieval agent
- selected_tasks_file: a file containing ids of all tasks to be run
- print: whether to the print more info to console
- num_processes: number of parallel processes when running auto-code-rover. Should not be too large, otherwise parallelly running multiple task instances can exceed OpenAI token limit and cause the task instance to fail.
