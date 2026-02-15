from __future__ import annotations

import csv
import shutil
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional

from tabulate import tabulate
import matplotlib.pyplot as plt


def generate_reports(results: List[Dict], output_dir: str | Path) -> Dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    csv_path = output_path / "results.csv"
    md_path = output_path / "results.md"
    chart_paths = {
        "latency": output_path / "chart_latency.png",
        "rule_score": output_path / "chart_rule_score.png",
    }

    _write_csv(results, csv_path)
    aggregates = aggregate_by_mode(results)
    task_aggregates = aggregate_by_task_mode(results)
    mode_deltas = compute_mode_deltas(aggregates)
    task_deltas = compute_task_deltas(task_aggregates)
    aggregate_csv_path = output_path / "aggregates_by_mode.csv"
    mode_delta_csv_path = output_path / "deltas_by_mode.csv"
    task_aggregate_csv_path = output_path / "aggregates_by_task.csv"
    _write_aggregates_csv(aggregates, aggregate_csv_path)
    _write_task_aggregates_csv(task_aggregates, task_aggregate_csv_path)
    _write_mode_deltas_csv(mode_deltas, mode_delta_csv_path)
    create_charts(aggregates, chart_paths)
    task_chart_paths = create_task_charts(results, output_path)
    _write_markdown(
        md_path,
        aggregates,
        mode_deltas,
        task_deltas,
        chart_paths,
        task_chart_paths,
        results,
    )
    html_paths = _write_html_report(
        results,
        aggregates,
        mode_deltas,
        task_deltas,
        chart_paths,
        task_chart_paths,
        output_path,
    )

    return {
        "csv": csv_path,
        "markdown": md_path,
        "aggregates_csv": aggregate_csv_path,
        "deltas_csv": mode_delta_csv_path,
        "task_aggregates_csv": task_aggregate_csv_path,
        **chart_paths,
        **task_chart_paths,
        **html_paths,
    }


def _write_csv(results: List[Dict], path: Path) -> None:
    if not results:
        path.write_text("")
        return
    fieldnames = sorted({key for row in results for key in row.keys()})
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def _write_aggregates_csv(aggregates: Dict[str, Dict[str, float]], path: Path) -> None:
    if not aggregates:
        path.write_text("")
        return
    headers = sorted({metric for metrics in aggregates.values() for metric in metrics.keys()})
    headers = ["mode"] + headers
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for mode, metrics in sorted(aggregates.items()):
            row = {"mode": mode}
            row.update(metrics)
            writer.writerow(row)


def _write_mode_deltas_csv(mode_deltas: Dict[str, Dict[str, float]], path: Path) -> None:
    if not mode_deltas:
        path.write_text("")
        return
    headers = sorted({metric for metrics in mode_deltas.values() for metric in metrics.keys()})
    headers = ["mode"] + headers
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for mode, metrics in sorted(mode_deltas.items()):
            row = {"mode": mode}
            row.update(metrics)
            writer.writerow(row)


def _write_task_aggregates_csv(
    task_aggregates: Dict[str, Dict[str, Dict[str, float]]],
    path: Path,
) -> None:
    if not task_aggregates:
        path.write_text("")
        return
    headers = sorted(
        {metric for modes in task_aggregates.values() for metrics in modes.values() for metric in metrics.keys()}
    )
    headers = ["task_id", "mode"] + headers
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for task_id, modes in sorted(task_aggregates.items()):
            for mode, metrics in sorted(modes.items()):
                row = {"task_id": task_id, "mode": mode}
                row.update(metrics)
                writer.writerow(row)


def aggregate_by_mode(results: Iterable[Dict]) -> Dict[str, Dict[str, float]]:
    buckets: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for row in results:
        mode = row["mode"]
        buckets[mode]["latency_ms"].append(row.get("latency_ms", 0.0))
        if row.get("tokens_in") is not None:
            buckets[mode]["tokens_in"].append(row["tokens_in"])
        if row.get("tokens_out") is not None:
            buckets[mode]["tokens_out"].append(row["tokens_out"])
        buckets[mode]["rule_score"].append(row.get("rule_score", 0.0))
        if row.get("llm_score") is not None:
            buckets[mode]["llm_score"].append(row["llm_score"])
        if row.get("cost_usd") is not None:
            buckets[mode]["cost_usd"].append(row["cost_usd"])

    aggregates: Dict[str, Dict[str, float]] = {}
    for mode, metrics in buckets.items():
        aggregates[mode] = {}
        for metric, values in metrics.items():
            if not values:
                continue
            aggregates[mode][metric] = round(mean(values), 4)
        latencies = metrics.get("latency_ms", [])
        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        if p50 is not None:
            aggregates[mode]["latency_p50"] = round(p50, 4)
        if p95 is not None:
            aggregates[mode]["latency_p95"] = round(p95, 4)
    return aggregates


def aggregate_by_task_mode(results: Iterable[Dict]) -> Dict[str, Dict[str, Dict[str, float]]]:
    buckets: Dict[str, Dict[str, Dict[str, List[float]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for row in results:
        task_id = row.get("task_id") or row.get("task")
        if not task_id:
            continue
        mode = row["mode"]
        buckets[task_id][mode]["latency_ms"].append(row.get("latency_ms", 0.0))
        for metric in ("tokens_in", "tokens_out", "rule_score", "llm_score", "cost_usd"):
            value = row.get(metric)
            if value is not None:
                buckets[task_id][mode][metric].append(value)

    aggregates: Dict[str, Dict[str, Dict[str, float]]] = {}
    for task_id, mode_map in buckets.items():
        aggregates[task_id] = {}
        for mode, metrics in mode_map.items():
            aggregates[task_id][mode] = {}
            for metric, values in metrics.items():
                if values:
                    aggregates[task_id][mode][metric] = round(mean(values), 4)
            latencies = buckets[task_id][mode].get("latency_ms", [])
            p50 = _percentile(latencies, 50)
            p95 = _percentile(latencies, 95)
            if p50 is not None:
                aggregates[task_id][mode]["latency_p50"] = round(p50, 4)
            if p95 is not None:
                aggregates[task_id][mode]["latency_p95"] = round(p95, 4)
    return aggregates


def compute_mode_deltas(aggregates: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    baseline = aggregates.get("baseline")
    if not baseline:
        return {}
    deltas: Dict[str, Dict[str, float]] = {}
    for mode, metrics in aggregates.items():
        if mode == "baseline":
            continue
        diff: Dict[str, float] = {}
        for metric, value in metrics.items():
            base_value = baseline.get(metric)
            if base_value is None:
                continue
            diff[metric] = round(value - base_value, 4)
        if diff:
            deltas[mode] = diff
    return deltas


def compute_task_deltas(task_aggregates: Dict[str, Dict[str, Dict[str, float]]]) -> Dict[str, Dict[str, Dict[str, float]]]:
    deltas: Dict[str, Dict[str, Dict[str, float]]] = {}
    for task_id, modes in task_aggregates.items():
        baseline = modes.get("baseline")
        if not baseline:
            continue
        for mode, metrics in modes.items():
            if mode == "baseline":
                continue
            diff: Dict[str, float] = {}
            for metric, value in metrics.items():
                base_value = baseline.get(metric)
                if base_value is None:
                    continue
                diff[metric] = round(value - base_value, 4)
            if diff:
                deltas.setdefault(task_id, {})[mode] = diff
    return deltas


def create_charts(aggregates: Dict[str, Dict[str, float]], chart_paths: Dict[str, Path]) -> None:
    if not aggregates:
        for path in chart_paths.values():
            path.write_text("")
        return

    modes = list(aggregates.keys())

    latency_values = [aggregates[mode].get("latency_ms", 0.0) for mode in modes]
    _bar_chart(
        modes,
        latency_values,
        ylabel="Avg latency (ms)",
        title="Latency by mode",
        path=chart_paths["latency"],
    )

    rule_values = [aggregates[mode].get("rule_score", 0.0) for mode in modes]
    _bar_chart(
        modes,
        rule_values,
        ylabel="Avg rule score",
        title="Rule-based quality by mode",
        path=chart_paths["rule_score"],
        ylim=(0, 1),
    )


def create_task_charts(results: List[Dict], output_path: Path) -> Dict[str, Path]:
    by_task: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for row in results:
        task_id = row.get("task_id") or row.get("task_path")
        if not task_id:
            continue
        by_task[task_id][row["mode"]].append(row.get("latency_ms", 0.0))

    chart_paths: Dict[str, Path] = {}
    for task_id, modes in by_task.items():
        fig, ax = plt.subplots(figsize=(4, 3))
        has_data = False
        for mode, latencies in modes.items():
            if not latencies:
                continue
            has_data = True
            ax.hist(latencies, bins=min(5, len(latencies)), alpha=0.6, label=mode)
        if not has_data:
            plt.close(fig)
            continue
        ax.set_title(f"Latency distribution — {task_id}")
        ax.set_xlabel("Latency (ms)")
        ax.set_ylabel("Count")
        ax.legend()
        fig.tight_layout()
        filename = f"chart_{_sanitize_name(task_id)}_latency.png"
        path = output_path / filename
        fig.savefig(path, dpi=150)
        plt.close(fig)
        chart_paths[f"{task_id}_latency"] = path
    return chart_paths


def _write_html_report(
    results: List[Dict],
    aggregates: Dict[str, Dict[str, float]],
    mode_deltas: Dict[str, Dict[str, float]],
    task_deltas: Dict[str, Dict[str, Dict[str, float]]],
    chart_paths: Dict[str, Path],
    task_chart_paths: Dict[str, Path],
    output_path: Path,
) -> Dict[str, Path]:
    html_root = output_path / "html"
    assets_dir = html_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    assets_source = Path(__file__).resolve().parent / "report_assets"
    style_src = assets_source / "style.css"
    script_src = assets_source / "app.js"

    if style_src.exists():
        shutil.copyfile(style_src, assets_dir / "style.css")
    if script_src.exists():
        shutil.copyfile(script_src, assets_dir / "app.js")

    for chart in list(chart_paths.values()) + list(task_chart_paths.values()):
        if chart.exists():
            shutil.copyfile(chart, assets_dir / chart.name)

    index_path = html_root / "index.html"
    index_path.write_text(_render_html_stub())

    return {
        "html_index": index_path,
        "html_assets_dir": assets_dir,
    }


def _render_html_stub() -> str:
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\" />\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
        "  <title>SkillBench-PD Report</title>\n"
        "  <link rel=\"stylesheet\" href=\"assets/style.css\" />\n"
        "</head>\n"
        "<body>\n"
        "  <main>\n"
        "    <h1>SkillBench-PD Report</h1>\n"
        "    <section>\n"
        "      <h2>Overview</h2>\n"
        "      <p>Summary of benchmark results and key deltas.</p>\n"
        "    </section>\n"
        "    <section>\n"
        "      <h2>Aggregated metrics</h2>\n"
        "      <p>Average latency, tokens, and quality by mode.</p>\n"
        "    </section>\n"
        "    <section>\n"
        "      <h2>Delta vs baseline</h2>\n"
        "      <p>How each mode differs from baseline.</p>\n"
        "    </section>\n"
        "    <section>\n"
        "      <h2>Help & Methodology</h2>\n"
        "      <p>How to interpret this report and next steps.</p>\n"
        "    </section>\n"
        "  </main>\n"
        "  <script src=\"assets/app.js\"></script>\n"
        "</body>\n"
        "</html>\n"
    )


def _percentile(values: List[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    if percentile <= 0:
        return min(values)
    if percentile >= 100:
        return max(values)
    sorted_vals = sorted(values)
    rank = (len(sorted_vals) - 1) * (percentile / 100)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_vals) - 1)
    weight = rank - lower
    return sorted_vals[lower] * (1 - weight) + sorted_vals[upper] * weight


def _sanitize_name(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name)
    return safe.strip("-_") or "task"


def _bar_chart(
    modes: List[str],
    values: List[float],
    *,
    ylabel: str,
    title: str,
    path: Path,
    ylim: Optional[tuple[float, float]] = None,
) -> None:
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(modes, values, color=["#6C8EBF", "#F6C344", "#88C999"][: len(modes)])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if ylim:
        ax.set_ylim(*ylim)
    for idx, value in enumerate(values):
        ax.text(idx, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _write_markdown(
    path: Path,
    aggregates: Dict[str, Dict[str, float]],
    mode_deltas: Dict[str, Dict[str, float]],
    task_deltas: Dict[str, Dict[str, Dict[str, float]]],
    chart_paths: Dict[str, Path],
    task_chart_paths: Dict[str, Path],
    results: List[Dict],
) -> None:
    lines: List[str] = [
        "# SkillBench-PD Results",
        "",
        "## Aggregated metrics by mode",
    ]
    if aggregates:
        table_rows = []
        headers = [
            "mode",
            "latency_ms",
            "latency_p50",
            "latency_p95",
            "tokens_in",
            "tokens_out",
            "rule_score",
            "llm_score",
            "cost_usd",
        ]
        for mode, metrics in sorted(aggregates.items()):
            row = [mode]
            for metric in headers[1:]:
                value = metrics.get(metric)
                if isinstance(value, (int, float)):
                    row.append(f"{value:.3f}")
                else:
                    row.append("")
            table_rows.append(row)
        lines.append(tabulate(table_rows, headers=headers, tablefmt="github"))
    else:
        lines.append("_No results recorded._")

    lines.extend(
        [
            "",
            "## Charts",
            f"![Latency by mode]({chart_paths['latency'].name})",
            f"![Rule quality by mode]({chart_paths['rule_score'].name})",
            "",
            "## Raw run count",
            f"- Total records: {len(results)}",
        ]
    )

    if mode_deltas:
        headers = [
            "mode",
            "latency_ms",
            "latency_p50",
            "latency_p95",
            "tokens_in",
            "tokens_out",
            "rule_score",
            "llm_score",
            "cost_usd",
        ]
        rows = []
        for mode, metrics in sorted(mode_deltas.items()):
            row = [mode]
            for metric in headers[1:]:
                value = metrics.get(metric)
                if isinstance(value, (int, float)):
                    row.append(f"{value:+.3f}")
                else:
                    row.append("")
            rows.append(row)
        lines.extend(
            [
                "",
                "## Mode deltas vs baseline",
                "Positive numbers indicate an increase relative to baseline.",
                tabulate(rows, headers=headers, tablefmt="github"),
            ]
        )

    if task_deltas:
        lines.append("")
        lines.append("## Per-task deltas vs baseline")
        for task_id, modes in sorted(task_deltas.items()):
            headers = [
                "mode",
                "latency_ms",
                "latency_p50",
                "latency_p95",
                "tokens_in",
                "tokens_out",
                "rule_score",
                "llm_score",
                "cost_usd",
            ]
            rows = []
            for mode, metrics in sorted(modes.items()):
                row = [mode]
                for metric in headers[1:]:
                    value = metrics.get(metric)
                    if isinstance(value, (int, float)):
                        row.append(f"{value:+.3f}")
                    else:
                        row.append("")
                rows.append(row)
            lines.append(f"### Task {task_id}")
            lines.append(tabulate(rows, headers=headers, tablefmt="github"))
            lines.append("")

    if task_chart_paths:
        lines.append("## Task-level latency histograms")
        for key, path_obj in sorted(task_chart_paths.items()):
            if not path_obj.exists():
                continue
            task_id = key.rsplit("_latency", 1)[0]
            lines.append(f"### {task_id}")
            lines.append(f"![Latency histogram for {task_id}]({path_obj.name})")
            lines.append("")

    path.write_text("\n".join(lines))
