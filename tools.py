from pathlib import Path
import re
import subprocess
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent


class ToolError(Exception):
    pass


def _resolve_task_dir(task_dir):
    task_path = (PROJECT_ROOT / task_dir).resolve()

    try:
        task_path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ToolError("Task directory must stay inside the project root.") from exc

    if not task_path.exists():
        raise ToolError(f"Task directory does not exist: {task_dir}")

    if not task_path.is_dir():
        raise ToolError(f"Task path is not a directory: {task_dir}")

    return task_path


def _resolve_task_file(task_dir, relative_path):
    task_path = _resolve_task_dir(task_dir)
    file_path = (task_path / relative_path).resolve()

    try:
        file_path.relative_to(task_path)
    except ValueError as exc:
        raise ToolError("File path must stay inside the task directory.") from exc

    if not file_path.exists():
        raise ToolError(f"File does not exist: {relative_path}")

    if not file_path.is_file():
        raise ToolError(f"Path is not a file: {relative_path}")

    return file_path


def _safe_read_text(file_path):
    return file_path.read_text(encoding="utf-8", errors="replace")


def _trim_text(text, max_chars):
    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n...[truncated]"


def list_files(task_dir):
    task_path = _resolve_task_dir(task_dir)
    files = []

    ignored_parts = {"__pycache__", ".pytest_cache"}

    for path in sorted(task_path.rglob("*")):
        if not path.is_file():
            continue

        relative = path.relative_to(task_path)

        if any(part in ignored_parts for part in relative.parts):
            continue

        files.append(str(relative).replace("\\", "/"))

    return {
        "ok": True,
        "task_dir": task_dir,
        "files": files,
    }


def read_file(task_dir, path, max_chars=8000):
    file_path = _resolve_task_file(task_dir, path)
    content = _safe_read_text(file_path)

    return {
        "ok": True,
        "path": path,
        "char_count": len(content),
        "content": _trim_text(content, max_chars),
        "truncated": len(content) > max_chars,
    }


def search_text(task_dir, pattern, path=None, max_matches=20):
    task_path = _resolve_task_dir(task_dir)
    regex = re.compile(pattern, re.IGNORECASE)
    matches = []

    if path:
        candidate_files = [_resolve_task_file(task_dir, path)]
    else:
        candidate_files = [
            file_path
            for file_path in task_path.rglob("*")
            if file_path.is_file()
            and "__pycache__" not in file_path.parts
            and ".pytest_cache" not in file_path.parts
        ]

    for file_path in candidate_files:
        content = _safe_read_text(file_path)
        relative = str(file_path.relative_to(task_path)).replace("\\", "/")

        for line_number, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                matches.append(
                    {
                        "path": relative,
                        "line_number": line_number,
                        "line": line[:500],
                    }
                )

            if len(matches) >= max_matches:
                break

        if len(matches) >= max_matches:
            break

    return {
        "ok": True,
        "pattern": pattern,
        "path": path,
        "num_matches": len(matches),
        "matches": matches,
    }


def run_tests(task_dir, timeout_sec=30, max_chars=12000):
    task_path = _resolve_task_dir(task_dir)

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", ".", "-q"],
            cwd=task_path,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "tests_passed": False,
            "return_code": None,
            "output": f"Test execution timed out after {timeout_sec} seconds.",
        }

    output = completed.stdout

    if completed.stderr:
        output = output + "\n" + completed.stderr

    return {
        "ok": True,
        "tests_passed": completed.returncode == 0,
        "return_code": completed.returncode,
        "output": _trim_text(output, max_chars),
        "truncated": len(output) > max_chars,
    }


def inspect_csv(task_dir, path, max_sample_rows=5):
    file_path = _resolve_task_file(task_dir, path)
    dataframe = pd.read_csv(file_path)

    missing_values = dataframe.isna().sum().to_dict()
    dtypes = {column: str(dtype) for column, dtype in dataframe.dtypes.items()}
    duplicate_rows = int(dataframe.duplicated().sum())

    value_counts = {}

    for column in dataframe.columns:
        unique_count = dataframe[column].nunique(dropna=False)

        if unique_count <= 20:
            value_counts[column] = dataframe[column].value_counts(dropna=False).head(10).to_dict()

    return {
        "ok": True,
        "path": path,
        "num_rows": int(len(dataframe)),
        "num_columns": int(len(dataframe.columns)),
        "columns": list(dataframe.columns),
        "dtypes": dtypes,
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
        "value_counts": value_counts,
        "sample_rows": dataframe.head(max_sample_rows).to_dict(orient="records"),
    }


def apply_patch_safely(task_dir, path, old_text, new_text):
    file_path = _resolve_task_file(task_dir, path)
    content = _safe_read_text(file_path)

    if old_text not in content:
        return {
            "ok": False,
            "path": path,
            "message": "The target text was not found. No changes were applied.",
        }

    updated_content = content.replace(old_text, new_text, 1)
    file_path.write_text(updated_content, encoding="utf-8")

    return {
        "ok": True,
        "path": path,
        "message": "Patch applied successfully.",
    }


if __name__ == "__main__":
    task = "tasks/bugfix_001"

    files_result = list_files(task)
    source_result = read_file(task, "src/median.py")
    test_result = run_tests(task)

    print("Files:")
    for file_path in files_result["files"]:
        print(f"- {file_path}")

    print("\nSource file:")
    print(source_result["content"])

    print("\nTest result:")
    print(f"tests_passed: {test_result['tests_passed']}")
    print(f"return_code: {test_result['return_code']}")
    print(test_result["output"])