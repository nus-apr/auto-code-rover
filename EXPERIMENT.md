# Replicating results on SWE-bench-lite

## Setup

### Docker

> [!IMPORTANT]
> There can be minor improvements to the Docker image from time to time. Please pull the latest version of the image.

> [!NOTE]
> The experiments were conducted on Ubuntu 20.04. Since SWE-bench evaluation may have different behavior
> under different host systems, it is recommened to run the provided docker on Ubuntu 20.04.

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
source activate base
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

This command runs auto-code-rover on the 300 instances in SWE-bench-lite, and consolidates all the generated
patches in a single file named `predictions_for_swebench.json`. For evaluating the correctness of the generated
patch, please copy this file out and evaluate it with either:

1. The [Containerized Evaluation Harness](https://github.com/princeton-nlp/SWE-bench/tree/main/docs/20240627_docker) by the SWE-bench team.
2. The [Moatless EvalTools](https://github.com/aorwall/SWE-bench-docker).


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

- model: the model to be used by auto-code-rover
- temperature: model temperature
- conv_round_limit: rounds limit for the conversation with context retrieval agent
- selected_tasks_file: a file containing ids of all tasks to be run
- print: whether to the print more info to console
- num_processes: number of parallel processes when running auto-code-rover. Should not be too large, otherwise parallelly running multiple task instances can exceed OpenAI token limit and cause the task instance to fail.

### Contacts

> [!NOTE]
> If you encounter any issue in the replication experiment, you can open an GitHub issue or contact us at {yuntong,hruan,zhiyufan}@comp.nus.edu.sg.
