# Software Engineering Task Agent Evaluation Harness

A lightweight LLM/Agent evaluation harness for software-engineering tasks.

This project evaluates how an LLM-based agent performs on small software-engineering tasks with a restricted set of local tools. It focuses on tool use, context usage, self-checking behavior, task success, trace logging, and failure-mode analysis.

## Overview

The harness is built around local software-engineering tasks. Each task provides an instruction, a task directory, required files, expected tools, success criteria, and possible failure modes.

For each run, the harness:

1. creates an isolated workspace from the original task files;
2. sends the task prompt to an OpenAI-compatible LLM API;
3. allows the model to call a restricted set of local tools;
4. records tool calls, tool results, latency, and final output;
5. evaluates the run using trace-level and workspace-level checks;
6. writes structured results to CSV.

The original benchmark task files remain unchanged during agent execution. Model actions are applied to temporary workspace copies under `runs/workspaces/`.

## Motivation

Software-engineering tasks often require more than producing a final answer. A model may need to inspect source files, examine tests, run verification commands, apply controlled fixes, and summarize the evidence behind its answer.

This project uses a controlled local setting to make these behaviors observable and evaluable.

## Repository Structure

```text
.
├── agent_runner.py
├── config.py
├── evaluator.py
├── prompts.py
├── tools.py
├── requirements.txt
├── .env.example
├── tasks/
│   ├── tasks.jsonl
│   └── bugfix_001/
│       ├── src/
│       │   ├── __init__.py
│       │   └── median.py
│       └── tests/
│           └── test_median.py
├── examples/
│   ├── sample_results.csv
│   ├── sample_trace_summary.json
│   ├── sample_failure_analysis.md
│   └── sample_summary.md
├── results/
├── traces/
└── runs/
```

## Main Components

### Task Set

Tasks are defined in `tasks/tasks.jsonl`.

Each task record contains fields such as:

* `task_id`
* `task_type`
* `task_dir`
* `instruction`
* `required_files`
* `expected_tools`
* `success_criteria`
* `failure_modes`

The first task, `bugfix_001`, asks the agent to inspect and fix a median function that returns an incorrect result for even-length lists.

### Restricted Tool Layer

The local tools are implemented in `tools.py`.

The current tool set includes:

* `list_files`
* `read_file`
* `search_text`
* `run_tests`
* `inspect_csv`
* `apply_patch_safely`

The tool layer uses controlled file access and does not expose arbitrary shell execution to the model.

### Agent Runner

`agent_runner.py` runs the tool-calling loop.

For each task, it:

1. creates an isolated task workspace;
2. sends the task prompt to the model;
3. executes requested tool calls;
4. returns tool results to the model;
5. applies a finalization step when needed;
6. saves a raw trace file under `traces/`.

Trace files are generated with unique run IDs to avoid overwriting previous runs.

### Evaluator

`evaluator.py` converts raw traces into structured evaluation records.

It checks:

* whether required files were read;
* whether expected tools were called;
* whether a patch was applied;
* whether tests passed in the trace;
* whether the final workspace passes tests;
* whether a final answer was produced;
* what failure type or process observation should be assigned.

The evaluator writes results to `results/results.csv`.

## Setup

This project requires Python 3.10 or later. It has been tested with Python 3.11.

Create and activate a Python environment using any environment manager you prefer, such as `venv`, `conda`, or another tool.

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Create a local `.env` file from the example file:

```bash
cp .env.example .env
```

On Windows PowerShell, the equivalent command is:

```powershell
Copy-Item .env.example .env
```

Fill in the local `.env` file:

```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=your_openai_compatible_base_url_here
LLM_MODEL=your_model_name_here
```

The project uses an OpenAI-compatible chat completion interface. The `LLM_BASE_URL` and `LLM_MODEL` values should match the provider or deployment used for the experiment.

The `.env` file is ignored by Git and should not be committed.

## Usage

### 1. Check the task prompt without calling the API

```bash
python agent_runner.py --task-id bugfix_001 --dry-run
```

This prints the system prompt, task prompt, and available tools.

### 2. Run the agent on a task

```bash
python agent_runner.py --task-id bugfix_001 --max-steps 6
```

This creates an isolated workspace, lets the model use tools, and saves a trace file under `traces/`.

### 3. Evaluate generated traces

```bash
python evaluator.py
```

This scans trace files, evaluates each run, and writes the result table to:

```text
results/results.csv
```

### 4. Run the original benchmark tests

```bash
python -m pytest tasks/bugfix_001 -q
```

The original task is expected to fail because it contains the benchmark bug.

### 5. Run the workspace tests

After an agent run, the runner prints the workspace path, for example:

```text
runs/workspaces/bugfix_001_YYYYMMDD_HHMMSS
```

The workspace can be tested with:

```bash
python -m pytest runs/workspaces/bugfix_001_YYYYMMDD_HHMMSS -q
```

A successful agent repair should make the workspace tests pass while leaving the original benchmark task unchanged.

## Example Output

A sample evaluation record is provided in:

```text
examples/sample_results.csv
```

A summarized trace example is provided in:

```text
examples/sample_trace_summary.json
```

A human-readable summary generated from the sample results is provided in:

```text
examples/sample_summary.md
```

The sample outputs were generated from runs using `deepseek-v4-flash` through an OpenAI-compatible chat completion interface.

In the current sample, the agent:

* inspected the source and test files;
* identified the even-length median bug;
* applied a patch in an isolated workspace;
* produced a final answer through the finalization step;
* left the original benchmark task unchanged;
* produced a workspace that passed all tests.

The evaluator also records process-level observations, such as:

```text
workspace_passed_but_not_tool_verified
```

This indicates that the final workspace passed tests, but the raw trace did not contain a successful post-fix test result from the model's own tool calls.

## Evaluation Fields

The evaluator currently records:

* `task_id`
* `task_type`
* `model`
* `run_id`
* `completed`
* `finalization_used`
* `success_score`
* `final_answer_present`
* `required_files_read`
* `expected_tools_called`
* `self_check_performed`
* `tests_passed_in_trace`
* `workspace_tests_passed`
* `patch_applied`
* `num_steps`
* `num_tool_calls`
* `total_latency_sec`
* `failure_type`
* `short_observation`
* `trace_path`
* `workspace_task_dir`

## Design Notes

The project is designed as a small evaluation-oriented prototype for software-engineering agent tasks.

The current implementation emphasizes:

* controlled software-engineering task instances;
* restricted local tool access;
* isolated task workspaces;
* traceable tool-use behavior;
* task-level evaluation records;
* qualitative failure-mode analysis.

Task definitions, tool boundaries, evaluation fields, scoring logic, and failure-mode categories are explicitly represented in the code and documentation so that the evaluation process can be inspected and extended.

## Generated Files and Git Tracking

The following files and directories are generated locally during execution and are not intended to be committed:

```text
.env
traces/
runs/
results/results.csv
results/summary.md
```

The `examples/` directory contains sanitized sample outputs that can be committed for demonstration purposes.

## Next Steps

Possible extensions include:

* adding more software-engineering task types;
* adding data-quality inspection tasks;
* adding issue-analysis tasks;
* improving post-fix verification detection;
* generating aggregate evaluation summaries;
* adding more sample outputs for public demonstration.
