import argparse
import json
import time
from pathlib import Path

from openai import OpenAI

from config import load_llm_config
from prompts import SYSTEM_PROMPT, build_task_prompt, get_task_by_id, load_tasks
import tools as local_tools


TRACE_DIR = Path("traces")


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files available inside a task directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_dir": {"type": "string"}
                },
                "required": ["task_dir"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file inside a task directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_dir": {"type": "string"},
                    "path": {"type": "string"},
                    "max_chars": {"type": "integer"}
                },
                "required": ["task_dir", "path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "Search for a text pattern inside one file or across a task directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_dir": {"type": "string"},
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "max_matches": {"type": "integer"}
                },
                "required": ["task_dir", "pattern"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run pytest inside a task directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_dir": {"type": "string"},
                    "timeout_sec": {"type": "integer"}
                },
                "required": ["task_dir"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_csv",
            "description": "Inspect a CSV file inside a task directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_dir": {"type": "string"},
                    "path": {"type": "string"},
                    "max_sample_rows": {"type": "integer"}
                },
                "required": ["task_dir", "path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch_safely",
            "description": "Apply a controlled text replacement inside a task file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_dir": {"type": "string"},
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"}
                },
                "required": ["task_dir", "path", "old_text", "new_text"],
                "additionalProperties": False
            }
        }
    }
]


TOOL_FUNCTIONS = {
    "list_files": local_tools.list_files,
    "read_file": local_tools.read_file,
    "search_text": local_tools.search_text,
    "run_tests": local_tools.run_tests,
    "inspect_csv": local_tools.inspect_csv,
    "apply_patch_safely": local_tools.apply_patch_safely,
}


def tool_call_to_dict(tool_call):
    if hasattr(tool_call, "model_dump"):
        return tool_call.model_dump(exclude_none=True)

    return {
        "id": tool_call.id,
        "type": tool_call.type,
        "function": {
            "name": tool_call.function.name,
            "arguments": tool_call.function.arguments,
        },
    }


def message_to_dict(message):
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)

    result = {
        "role": "assistant",
        "content": message.content,
    }

    if getattr(message, "tool_calls", None):
        result["tool_calls"] = [
            tool_call_to_dict(tool_call)
            for tool_call in message.tool_calls
        ]

    return result


def execute_tool_call(tool_call):
    name = tool_call.function.name
    arguments_text = tool_call.function.arguments or "{}"

    try:
        arguments = json.loads(arguments_text)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "tool_name": name,
            "error": f"Invalid JSON arguments: {exc}",
            "raw_arguments": arguments_text,
        }

    if name not in TOOL_FUNCTIONS:
        return {
            "ok": False,
            "tool_name": name,
            "error": f"Unknown tool: {name}",
            "arguments": arguments,
        }

    try:
        result = TOOL_FUNCTIONS[name](**arguments)
    except Exception as exc:
        return {
            "ok": False,
            "tool_name": name,
            "error": str(exc),
            "arguments": arguments,
        }

    return {
        "ok": True,
        "tool_name": name,
        "arguments": arguments,
        "result": result,
    }


def save_trace(task_id, trace):
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    trace_path = TRACE_DIR / f"{task_id}_trace.json"

    with trace_path.open("w", encoding="utf-8") as file:
        json.dump(trace, file, ensure_ascii=False, indent=2)

    return trace_path


def run_agent_on_task(task, max_steps=6):
    config = load_llm_config()

    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_task_prompt(task)},
    ]

    trace = {
        "task_id": task["task_id"],
        "task_type": task["task_type"],
        "task_dir": task["task_dir"],
        "model": config.model,
        "max_steps": max_steps,
        "steps": [],
        "final_answer": None,
        "completed": False,
    }

    for step_index in range(1, max_steps + 1):
        start_time = time.perf_counter()

        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        latency_sec = time.perf_counter() - start_time
        message = response.choices[0].message
        assistant_message = message_to_dict(message)

        messages.append(assistant_message)

        step_record = {
            "step": step_index,
            "latency_sec": round(latency_sec, 4),
            "assistant_message": assistant_message,
            "tool_results": [],
        }

        if getattr(response, "usage", None):
            step_record["usage"] = response.usage.model_dump(exclude_none=True)

        tool_calls = message.tool_calls or []

        if not tool_calls:
            trace["final_answer"] = message.content or ""
            trace["completed"] = True
            trace["steps"].append(step_record)
            break

        for tool_call in tool_calls:
            tool_result = execute_tool_call(tool_call)
            tool_result_text = json.dumps(tool_result, ensure_ascii=False)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result_text,
                }
            )

            step_record["tool_results"].append(
                {
                    "tool_call": tool_call_to_dict(tool_call),
                    "tool_result": tool_result,
                }
            )

        trace["steps"].append(step_record)

    if not trace["completed"]:
        trace["final_answer"] = "Maximum step limit reached before a final answer was produced."

    trace_path = save_trace(task["task_id"], trace)

    return trace, trace_path


def dry_run(task):
    print("System prompt:")
    print(SYSTEM_PROMPT)

    print("\nTask prompt:")
    print(build_task_prompt(task))

    print("\nAvailable tools:")
    for tool_schema in TOOL_SCHEMAS:
        print(f"- {tool_schema['function']['name']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default="tasks/tasks.jsonl")
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)

    if args.task_id:
        selected_tasks = [get_task_by_id(tasks, args.task_id)]
    else:
        selected_tasks = tasks

    for task in selected_tasks:
        print(f"\nRunning task: {task['task_id']}")

        if args.dry_run:
            dry_run(task)
            continue

        trace, trace_path = run_agent_on_task(task, max_steps=args.max_steps)

        print("\nFinal answer:")
        print(trace["final_answer"])

        print("\nTrace saved to:")
        print(trace_path)


if __name__ == "__main__":
    main()