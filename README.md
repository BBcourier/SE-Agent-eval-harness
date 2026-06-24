# Software Engineering Task Agent Evaluation Harness

A lightweight LLM/Agent evaluation harness for software engineering tasks.

This project evaluates how an LLM-based agent performs on small software-engineering tasks with a restricted set of local tools. It focuses on tool use, context usage, self-checking behavior, task success, and failure-mode analysis.

## Overview

The harness is designed around small local tasks such as code debugging, issue analysis, test generation, and data-quality inspection.

For each task, the harness records both the final outcome and the intermediate process, including the files inspected, tools called, verification steps performed, and observed failure types.

## Motivation

Software-engineering tasks often require more than generating a final answer. A model may need to inspect relevant files, search for specific evidence, run tests, check data properties, and revise its output based on tool feedback.

This project uses a controlled task setting to make these behaviors easier to observe and evaluate.

## Scope

The first version of this project focuses on a compact local evaluation setup:

* small software-engineering task instances;
* restricted local tool use;
* execution trace logging;
* task-level scoring;
* qualitative failure analysis.

The design emphasizes clarity, reproducibility, and interpretable evaluation records.

## Architecture

The harness contains four main components:

1. **Task Set**
   Small local software-engineering tasks stored under `tasks/`.

2. **Restricted Tools**
   A whitelist of local tools for file reading, text search, CSV inspection, test execution, and controlled patching.

3. **Agent Runner**
   A tool-calling loop that sends the task to the model, executes allowed tools, and records the interaction trace.

4. **Evaluator**
   A lightweight evaluator that records task success, tool-use correctness, context usage, self-checking behavior, and failure types.

## Task Types

The initial task set covers several software-engineering scenarios:

* code debugging;
* small bug fixing;
* issue or requirement analysis;
* CSV data-quality inspection;
* test-case generation;
* model-output reliability comparison.

## Tool Set

The first version uses a restricted local tool set:

* `list_files`
* `read_file`
* `search_text`
* `inspect_csv`
* `run_tests`
* `apply_patch_safely`

The tool set is intentionally small so that each model action can be traced and evaluated under controlled conditions.

## Evaluation Fields

Each task run produces a structured result record with fields such as:

* `task_id`
* `task_type`
* `model`
* `success_score`
* `final_answer_correct`
* `required_files_read`
* `tool_call_correct`
* `self_check_performed`
* `tests_passed`
* `num_steps`
* `num_tool_calls`
* `latency_sec`
* `failure_type`
* `short_observation`

## Planned Outputs

The harness will generate:

* execution traces for individual tasks;
* a task-level result table;
* a summary of observed failure modes;
* sample outputs for demonstration.

## Development Status

This project is under active development.

Current implementation goals:

* define the project structure;
* create a small local software-engineering task set;
* implement restricted local tools;
* connect a DeepSeek API tool-calling loop;
* save execution traces;
* generate task-level evaluation results;
* summarize observed failure modes.

## Agent-Assisted Development Workflow

This prototype may use an agent-assisted coding workflow during development. Codex can support implementation scaffolding, debugging, and test iteration.

The task design, tool boundaries, evaluation fields, scoring protocol, and failure-mode categories are manually reviewed as part of the development process.
