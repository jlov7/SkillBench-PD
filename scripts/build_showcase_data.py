from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "sample_results"
SHOWCASE_DIR = ROOT / "showcase"
SHOWCASE_DATA = SHOWCASE_DIR / "data" / "evidence.json"
SHOWCASE_CHARTS = SHOWCASE_DIR / "assets" / "charts"

CHART_FILES = [
    "chart_latency.png",
    "chart_rule_score.png",
    "chart_t1_rewrite_brand_latency.png",
    "chart_t2_format_policy_latency.png",
    "chart_t3_summarize_metrics_latency.png",
]


def _to_float(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    return float(value)


def _read_aggregates() -> list[dict]:
    rows: list[dict] = []
    with (SAMPLE_DIR / "aggregates_by_mode.csv").open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(
                {
                    "mode": row.get("mode", ""),
                    "latency_ms": _to_float(row.get("latency_ms", "") or "") or 0.0,
                    "tokens_in": _to_float(row.get("tokens_in", "") or "") or 0.0,
                    "rule_score": _to_float(row.get("rule_score", "") or "") or 0.0,
                    "cost_usd": _to_float(row.get("cost_usd", "") or "") or 0.0,
                }
            )
    return rows


def build_showcase_data() -> dict:
    SHOWCASE_CHARTS.mkdir(parents=True, exist_ok=True)
    for chart in CHART_FILES:
        src = SAMPLE_DIR / chart
        if src.exists():
            shutil.copyfile(src, SHOWCASE_CHARTS / chart)

    aggregates = _read_aggregates()
    best_cost_mode = ""
    if aggregates:
        best_cost_mode = min(aggregates, key=lambda row: row.get("cost_usd", float("inf"))).get("mode", "")

    record_count = 0
    task_count = 0
    mode_count = 0

    with (SAMPLE_DIR / "aggregates_by_task.csv").open("r", encoding="utf-8") as fh:
        task_rows = list(csv.DictReader(fh))
        record_count = len(task_rows)
        task_count = len({row.get("task_id", "") for row in task_rows if row.get("task_id")})
        mode_count = len({row.get("mode", "") for row in task_rows if row.get("mode")})

    output = {
        "generated_from": "sample_results",
        "summary": {
            "record_count": record_count,
            "task_count": task_count,
            "mode_count": mode_count,
            "best_cost_mode": best_cost_mode,
        },
        "aggregates": aggregates,
        "repro_command": (
            "uv run skillbench-pd --orchestrate --modes baseline naive progressive "
            "--tasks tasks/t1_rewrite_brand.json tasks/t2_format_policy.json tasks/t3_summarize_metrics.json "
            "--repetitions 3 --matrix-models mock-model --matrix-judges rule --output-dir results"
        ),
    }

    SHOWCASE_DATA.parent.mkdir(parents=True, exist_ok=True)
    SHOWCASE_DATA.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    payload = build_showcase_data()
    print(f"Wrote showcase evidence: {SHOWCASE_DATA}")
    print(f"Modes: {payload['summary']['mode_count']} | Tasks: {payload['summary']['task_count']} | Records: {payload['summary']['record_count']}")
