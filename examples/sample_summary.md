# Evaluation Summary

Source file: `examples\sample_results.csv`

## Overview

| Metric | Value |
| --- | --- |
| Total runs | 1 |
| Average success score | 1.00 |
| Workspace tests passed | 1/1 |
| Trace-level test verification | 0/1 |
| Final answers produced | 1/1 |
| Finalization step used | 1/1 |
| Average latency seconds | 27.78 |

## Task Types

| Task type | Count |
| --- | --- |
| code_debugging | 1 |

## Failure and Observation Types

| Failure type | Count |
| --- | --- |
| `workspace_passed_but_not_tool_verified` | 1 |

## Run-Level Results

| task_id | run_id | model | success_score | workspace_tests_passed | tests_passed_in_trace | finalization_used | failure_type |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bugfix_001 | bugfix_001_sample | deepseek-v4-flash | 1.0 | True | False | True | workspace_passed_but_not_tool_verified |

## Interpretation

The summary combines workspace-level checks and trace-level checks.

A workspace-level pass means the final task workspace passed its tests after the agent run.

A trace-level verification pass means the raw trace contains an explicit successful post-fix test result from the agent's own tool calls.

These two signals are intentionally tracked separately because a task can be solved in the final workspace while still lacking a complete verification record in the trace.
