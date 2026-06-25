import argparse
import json
from pathlib import Path


SYSTEM_PROMPT = """
You are an LLM/Agent being evaluated on software-engineering tasks.

You can use the provided local tools to inspect files, search text, run tests, inspect CSV files, and apply controlled patches.

Use tools when task evidence is needed. Do not assume file contents without reading them. Prefer a small number of relevant tool calls over unnecessary exploration.

When you provide the final answer, include:
1. the files or evidence you inspected;
2. the issue you identified;
3. the action or fix you applied or recommend;
4. the verification result;
5. any remaining uncertainty.
""".strip()


def build_task_prompt(task):
    required_files = ", ".join(task.get("required_files", []))
    expected_tools = ", ".join(task.get("expected_tools", []))
    success_criteria = "\n".join(
        f"- {criterion}" for criterion in task.get("success_criteria", [])
    )

    return f"""
Task ID: {task["task_id"]}
Task type: {task["task_type"]}
Task directory: {task["task_dir"]}

Instruction:
{task["instruction"]}

Required files:
{required_files}

Expected tools:
{expected_tools}

Success criteria:
{success_criteria}
""".strip()


def load_tasks(tasks_path="tasks/tasks.jsonl"):
    path = Path(tasks_path)
    tasks = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            task = json.loads(line)
            task["_line_number"] = line_number
            tasks.append(task)

    if not tasks:
        raise ValueError(f"No tasks found in {tasks_path}")

    return tasks


def get_task_by_id(tasks, task_id):
    for task in tasks:
        if task.get("task_id") == task_id:
            return task

    raise ValueError(f"Task not found: {task_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="tasks/tasks.jsonl")
    parser.add_argument("--task-id", default=None)
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)

    if args.task_id:
        selected_tasks = [get_task_by_id(tasks, args.task_id)]
    else:
        selected_tasks = tasks

    print(SYSTEM_PROMPT)

    for task in selected_tasks:
        print()
        print("=" * 80)
        print(build_task_prompt(task))