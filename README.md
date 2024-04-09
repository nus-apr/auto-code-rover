# AutoCodeRover: Autonomous Program Improvement

![overall-workflow](https://github.com/nus-apr/auto-code-rover/assets/48704330/0b8da9ad-588c-4f7d-9c99-53f33d723d35)

## 👋 Overview

AutoCodeRover is a fully automated approach for resolving GitHub issues (bug fixing and feature addition) where LLMs are combined with analysis and debugging capabilities to prioritize patch locations ultimately leading to a patch.

On [SWE-bench lite](https://www.swebench.com/lite.html), which consists of 300 real-world GitHub issues, AutoCodeRover resolves ~**22%** of issues, improving over the current state-of-the-art efficacy of AI software engineers.

<p align="center">
<img src=https://github.com/nus-apr/auto-code-rover/assets/48704330/28e26111-5f15-4ee4-acd1-fa6e2e6e0593 width=330/>
</p>

AutoCodeRover works in two stages:

- 🔎 Context retrieval: The LLM is provided with code search APIs to navigate the codebase and collect relevant context.
- 💊 Patch generation: The LLM tries to write a patch, based on retrieved context.

### ✨ Highlights

AutoCodeRover has two unique features:

- Code search APIs are *Program Structure Aware*. Instead of searching over files by plain string matching, AutoCodeRover searches for relevant code context (methods/classes) in the abstract syntax tree.
- When a test suite is available, AutoCodeRover can take advantage of test cases to achieve an even higher repair rate, by performing *statistical fault localization*.

## 🗎 Paper

For referring to our work, please cite and mention our [arXiv paper](https://arxiv.org/abs/2404.05427):

AutoCodeRover: Autonomous Program Improvement

Authors: Yuntong Zhang, Haifeng Ruan, Zhiyu Fan, Abhik Roychoudhury

ArXiv pre-print, released in public domain on 8 April 2024.

## ✔️ Example: Django Issue #32347

As an example, AutoCodeRover successfully fixed issue [#32347](https://code.djangoproject.com/ticket/32347) of Django. See the demo video for the full process:

https://github.com/nus-apr/auto-code-rover/assets/48704330/719c7a56-40b8-4f3d-a90e-0069e37baad3


## ⚙️ Setup

First, install Conda:

```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

Then set up Conda environment:

```
conda env create -f environment.yml
conda activate auto-code-rover
```

Also set up SWE-bench:

```
cd ..
git clone https://github.com/princeton-nlp/SWE-bench.git
conda env create -f environment.yml
```

Finally, specify your [OpenAI key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key) in the `OPENAI_KEY` environment variable:

```
export OPENAI_KEY=xx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

And we are good to go!

## 🚀 Running

### Run a single task

To run a single task, build and start the docker image:

```
docker build -f Dockerfile.one_task -t acr-one-task .
docker run -it acr-one-task /bin/bash
```

In the started docker container, run

```
conda activate auto-code-rover
export OPENAI_KEY=xx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PYTHONPATH=. python app/main.py --enable-layered --model gpt-4-0125-preview --setup-map ../SWE-bench/setup_result/setup_map.json --tasks-map ../SWE-bench/setup_result/tasks_map.json --output-dir output --task django__django-11133
```

The output can then be found in `output/`.

### Run multiple tasks

First, put the id's of all tasks to run in a file, one per line. Suppose this file is `tasks.txt`, the tasks can be run with

```
PYTHONPATH=. python app/main.py --enable-layered --setup-map ../SWE-bench/setup_result/setup_map.json --tasks-map ../SWE-bench/setup_result/tasks_map.json --output-dir output --task-list-file tasks.txt
```

#### Using a config file

Alternatively, a config file can be used to specify all parameters and tasks to run. See `conf/vanilla-lite.conf` for an example. A config file can be used by:

```
python scripts/run.py conf/vanilla-lite.conf
```

## Experiment Replication

Please refer to [EXPERIMENT.md](EXPERIMENT.md) for information on experiment replication.

## ✉️ Contacts

For any queries, you are welcome to open an issue.

Alternatively, contact us at: {yuntong,hruan,zhiyufan}@comp.nus.edu.sg.

## Acknowledgements

This work was partially supported by a Singapore Ministry of Education (MoE) Tier 3 grant "Automated Program Repair", MOE-MOET32021-0001.
