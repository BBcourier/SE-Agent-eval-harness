import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

from prompts import load_tasks


PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"


def load_trace(trace_path):
    path = Path(trace_path)

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def collect_tool_events(trace):
    events = []

    for step in trace.get("steps", []):
        for tool_item in step.get("tool_results", []):
            tool_call = tool_item.get("tool_call", {})
            tool_result = tool_item.get("tool_result", {})

            function = tool_call.get("function", {})
            name = function.get("name") or tool_result.get("tool_name")
            arguments_text = function.get("arguments") or "{}"

            try:
                arguments = json.loads(arguments_text)
            except json.JSONDecodeError:
                arguments = tool_result.get("arguments", {})

            events.append(
                {
                    "step": step.get("step"),
                    "tool_name": name,
                    "arguments": arguments,
                    "tool_result": tool_result,
                }
            )

    return events


def run_workspace_tests(workspace_task_dir):
    if not workspace_task_dir:
        return {
            "available": False,
            "tests_passed": False,
            "return_code": None,
            "output": "No workspace task directory recorded in trace.",
        }

    workspace_path = PROJECT_ROOT / workspace_task_dir

    if not workspace_path.exists():
        return {
            "available": False,
            "tests_passed": False,
            "return_code": None,
            "output": f"Workspace does not exist: {workspace_task_dir}",
        }

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", str(workspace_path), "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = completed.stdout

    if completed.stderr:
        output = output + "\n" + completed.stderr

    return {
        "available": True,
        "tests_passed": completed.returncode == 0,
        "return_code": completed.returncode,
        "output": output.strip(),
    }


def find_task_metadata(tasks, task_id):
    for task in tasks:
        if task.get("task_id") == task_id:
            return task

    return {}


def has_successful_patch(tool_events):
    for event in tool_events:
        if event["tool_name"] != "apply_patch_safely":
            continue

        result = event.get("tool_result", {}).get("result", {})

        if result.get("ok") is True:
            return True

    return False


def has_tests_passed_in_trace(tool_events):
    for event in tool_events:
        if event["tool_name"] != "run_tests":
            continue

        result = event.get("tool_result", {}).get("result", {})

        if result.get("tests_passed") is True:
            return True

    return False


def has_run_tests_after_patch(tool_events):
    patch_seen = False

    for event in tool_events:
        if event["tool_name"] == "apply_patch_safely":
            result = event.get("tool_result", {}).get("result", {})

            if result.get("ok") is True:
                patch_seen = True

        if patch_seen and event["tool_name"] == "run_tests":
            return True

    return False


def evaluate_trace(trace_path, tasks):
    trace = load_trace(trace_path)
    task_id = trace.get("task_id")
    task = find_task_metadata(tasks, task_id)

    tool_events = collect_tool_events(trace)
    tool_names = [event["tool_name"] for event in tool_events if event["tool_name"]]

    read_files = [
        event["arguments"].get("path")
        for event in tool_events
        if event["tool_name"] == "read_file"
    ]

    required_files = task.get("required_files", [])
    expected_tools = task.get("expected_tools", [])

    required_files_read = all(file_path in read_files for file_path in required_files)
    expected_tools_called = all(tool_name in tool_names for tool_name in expected_tools)

    patch_applied = has_successful_patch(tool_events)
    tests_passed_in_trace = has_tests_passed_in_trace(tool_events)
    self_check_performed = has_run_tests_after_patch(tool_events)

    workspace_result = run_workspace_tests(trace.get("workspace_task_dir"))
    workspace_tests_passed = workspace_result["tests_passed"]

    final_answer_present = bool((trace.get("final_answer") or "").strip())

    if workspace_tests_passed and required_files_read and final_answer_present:
        success_score = 1.0
    elif workspace_tests_passed and final_answer_present:
        success_score = 0.8
    elif patch_applied:
        success_score = 0.5
    elif tool_events:
        success_score = 0.25
    else:
        success_score = 0.0

    if success_score == 1.0 and tests_passed_in_trace:
        failure_type = "none"
        short_observation = "The agent inspected the required files, applied a correct patch, verified the fix through tools, and produced a final answer."
    elif success_score == 1.0 and not tests_passed_in_trace:
        failure_type = "workspace_passed_but_not_tool_verified"
        short_observation = "The workspace passed tests after the run, but the trace did not contain a successful post-fix test result."
    elif workspace_tests_passed and not final_answer_present:
        failure_type = "fixed_but_no_final_answer"
        short_observation = "The workspace passed tests, but the agent did not produce a final answer."
    elif patch_applied and not workspace_tests_passed:
        failure_type = "patch_applied_but_tests_failed"
        short_observation = "The agent applied a patch, but the workspace did not pass the tests."
    elif not required_files_read:
        failure_type = "missing_context"
        short_observation = "The agent did not inspect all required files."
    else:
        failure_type = "task_not_solved"
        short_observation = "The agent did not solve the task."

    total_latency_sec = sum(
        step.get("latency_sec", 0)
        for step in trace.get("steps", [])
        if isinstance(step.get("latency_sec", 0), (int, float))
    )

    return {
        "task_id": task_id,
        "task_type": trace.get("task_type"),
        "model": trace.get("model"),
        "run_id": trace.get("run_id"),
        "completed": trace.get("completed"),
        "finalization_used": trace.get("finalization_used"),
        "success_score": success_score,
        "final_answer_present": final_answer_present,
        "required_files_read": required_files_read,
        "expected_tools_called": expected_tools_called,
        "self_check_performed": self_check_performed,
        "tests_passed_in_trace": tests_passed_in_trace,
        "workspace_tests_passed": workspace_tests_passed,
        "patch_applied": patch_applied,
        "num_steps": len(trace.get("steps", [])),
        "num_tool_calls": len(tool_events),
        "total_latency_sec": round(total_latency_sec, 4),
        "failure_type": failure_type,
        "short_observation": short_observation,
        "trace_path": str(trace_path),
        "workspace_task_dir": trace.get("workspace_task_dir"),
    }


def write_results(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "task_id",
        "task_type",
        "model",
        "run_id",
        "completed",
        "finalization_used",
        "success_score",
        "final_answer_present",
        "required_files_read",
        "expected_tools_called",
        "self_check_performed",
        "tests_passed_in_trace",
        "workspace_tests_passed",
        "patch_applied",
        "num_steps",
        "num_tool_calls",
        "total_latency_sec",
        "failure_type",
        "short_observation",
        "trace_path",
        "workspace_task_dir",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="tasks/tasks.jsonl")
    parser.add_argument("--trace", default=None)
    parser.add_argument("--traces-dir", default="traces")
    parser.add_argument("--output", default="results/results.csv")
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)

    if args.trace:
        trace_paths = [Path(args.trace)]
    else:
        trace_paths = sorted(Path(args.traces_dir).glob("*_trace.json"))

    if not trace_paths:
        raise ValueError("No trace files found.")

    rows = [
        evaluate_trace(trace_path, tasks)
        for trace_path in trace_paths
    ]

    output_path = Path(args.output)
    write_results(rows, output_path)

    print(f"Evaluated {len(rows)} trace file(s).")
    print(f"Results saved to: {output_path}")

    for row in rows:
        print()
        print(f"Task: {row['task_id']}")
        print(f"Run ID: {row['run_id']}")
        print(f"Success score: {row['success_score']}")
        print(f"Failure type: {row['failure_type']}")
        print(f"Observation: {row['short_observation']}")


if __name__ == "__main__":
    main()