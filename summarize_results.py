import argparse
import csv
from collections import Counter
from pathlib import Path


def read_rows(input_path):
    path = Path(input_path)

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def to_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_number(value):
    return f"{value:.2f}"


def escape_markdown(value):
    return str(value).replace("|", "\\|")


def count_true(rows, field):
    return sum(1 for row in rows if to_bool(row.get(field)))


def average(rows, field):
    values = [to_float(row.get(field)) for row in rows if row.get(field) not in {None, ""}]

    if not values:
        return 0.0

    return sum(values) / len(values)


def make_overview_table(rows):
    total_runs = len(rows)
    average_score = average(rows, "success_score")
    average_latency = average(rows, "total_latency_sec")
    workspace_passed = count_true(rows, "workspace_tests_passed")
    trace_verified = count_true(rows, "tests_passed_in_trace")
    final_answers = count_true(rows, "final_answer_present")
    finalization_used = count_true(rows, "finalization_used")

    return [
        ("Total runs", total_runs),
        ("Average success score", format_number(average_score)),
        ("Workspace tests passed", f"{workspace_passed}/{total_runs}"),
        ("Trace-level test verification", f"{trace_verified}/{total_runs}"),
        ("Final answers produced", f"{final_answers}/{total_runs}"),
        ("Finalization step used", f"{finalization_used}/{total_runs}"),
        ("Average latency seconds", format_number(average_latency)),
    ]


def make_failure_type_table(rows):
    counts = Counter(row.get("failure_type", "unknown") for row in rows)

    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def make_task_type_table(rows):
    counts = Counter(row.get("task_type", "unknown") for row in rows)

    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def make_run_table(rows):
    selected_fields = [
        "task_id",
        "run_id",
        "model",
        "success_score",
        "workspace_tests_passed",
        "tests_passed_in_trace",
        "finalization_used",
        "failure_type",
    ]

    lines = []
    lines.append("| " + " | ".join(selected_fields) + " |")
    lines.append("| " + " | ".join(["---"] * len(selected_fields)) + " |")

    for row in rows:
        values = [escape_markdown(row.get(field, "")) for field in selected_fields]
        lines.append("| " + " | ".join(values) + " |")

    return lines


def build_summary(rows, input_path):
    if not rows:
        raise ValueError("No rows found in the input CSV.")

    overview_rows = make_overview_table(rows)
    failure_type_rows = make_failure_type_table(rows)
    task_type_rows = make_task_type_table(rows)
    run_table_lines = make_run_table(rows)

    lines = []
    lines.append("# Evaluation Summary")
    lines.append("")
    display_input_path = str(input_path).replace("\\", "/")
    lines.append(f"Source file: `{display_input_path}`")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")

    for metric, value in overview_rows:
        lines.append(f"| {metric} | {value} |")

    lines.append("")
    lines.append("## Task Types")
    lines.append("")
    lines.append("| Task type | Count |")
    lines.append("| --- | --- |")

    for task_type, count in task_type_rows:
        lines.append(f"| {escape_markdown(task_type)} | {count} |")

    lines.append("")
    lines.append("## Failure and Observation Types")
    lines.append("")
    lines.append("| Failure type | Count |")
    lines.append("| --- | --- |")

    for failure_type, count in failure_type_rows:
        lines.append(f"| `{escape_markdown(failure_type)}` | {count} |")

    lines.append("")
    lines.append("## Run-Level Results")
    lines.append("")
    lines.extend(run_table_lines)
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("The summary combines workspace-level checks and trace-level checks.")
    lines.append("")
    lines.append("A workspace-level pass means the final task workspace passed its tests after the agent run.")
    lines.append("")
    lines.append("A trace-level verification pass means the raw trace contains an explicit successful post-fix test result from the agent's own tool calls.")
    lines.append("")
    lines.append("These two signals are intentionally tracked separately because a task can be solved in the final workspace while still lacking a complete verification record in the trace.")

    return "\n".join(lines) + "\n"


def write_summary(content, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/results.csv")
    parser.add_argument("--output", default="results/summary.md")
    args = parser.parse_args()

    rows = read_rows(args.input)
    summary = build_summary(rows, args.input)
    write_summary(summary, args.output)

    print(f"Read {len(rows)} result row(s).")
    print(f"Summary saved to: {args.output}")


if __name__ == "__main__":
    main()