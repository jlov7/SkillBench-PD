from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from tabulate import tabulate

from .harness import BenchmarkConfig, load_config, run_benchmark, validate_config
from .providers import ProviderFactory
from .report import (
    aggregate_by_mode,
    compute_mode_deltas,
    generate_reports,
)


ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillbench-pd",
        description="Benchmark progressive disclosure vs naive prompting for Claude Skills.",
    )
    parser.add_argument(
        "--config",
        default="configs/bench.yaml",
        help="Path to the YAML config (default: configs/bench.yaml).",
    )
    parser.add_argument(
        "--provider",
        choices=["mock", "anthropic", "auto"],
        help="Override provider. 'auto' uses Anthropic when ANTHROPIC_API_KEY is set.",
    )
    parser.add_argument("--model", help="Override model name for the selected provider.")
    parser.add_argument(
        "--modes",
        nargs="+",
        help="Override modes to run (subset of baseline|naive|progressive).",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        help="Override task file paths (JSON).",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        help="Override repetitions per task/mode.",
    )
    parser.add_argument(
        "--judge",
        choices=["rule", "llm"],
        help="Override judge mode.",
    )
    parser.add_argument(
        "--skill-root",
        help="Override skill root directory.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for CSV/Markdown/plots (default from config).",
    )
    parser.add_argument(
        "--results-json",
        help="Where to write the raw JSON results (default: <output_dir>/results.json).",
    )
    parser.add_argument(
        "--percentiles",
        type=float,
        nargs="*",
        default=[50.0, 95.0],
        help="Latency percentiles to show in console summary (default: 50 95).",
    )
    return parser


def resolve_provider_name(config_provider: str, override: Optional[str]) -> tuple[str, Optional[str]]:
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    notice: Optional[str] = None

    if override:
        if override == "auto":
            chosen = "anthropic" if has_key else "mock"
            notice = (
                "ANTHROPIC_API_KEY detected; using Anthropic provider."
                if has_key
                else "ANTHROPIC_API_KEY not set; falling back to mock provider."
            )
            return chosen, notice
        return override, notice

    if config_provider == "mock" and has_key:
        notice = "ANTHROPIC_API_KEY detected; overriding config to use Anthropic provider."
        return "anthropic", notice

    return config_provider, notice


def apply_overrides(config: BenchmarkConfig, args: argparse.Namespace, root: Path) -> BenchmarkConfig:
    updates = {}

    if args.modes:
        updates["modes"] = list(args.modes)
    if args.tasks:
        updates["tasks"] = [normalise_path(task_path, root) for task_path in args.tasks]
    if args.repetitions is not None:
        updates["repetitions"] = max(1, int(args.repetitions))
    if args.judge:
        updates["judge"] = args.judge
    if args.skill_root:
        updates["skill_root"] = Path(normalise_path(args.skill_root, root))
    if args.output_dir:
        updates["output_dir"] = normalise_path(args.output_dir, root, keep_relative=True)

    if updates:
        config = replace(config, **updates)
    return config


def normalise_path(path_str: str, root: Path, *, keep_relative: bool = False) -> str:
    candidate = Path(path_str)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        rel = candidate.relative_to(root)
        return rel.as_posix() if keep_relative else str(rel)
    except ValueError:
        # Outside repo: return absolute path string
        return str(candidate)


def _resolve_to_path(path_value: str, root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = root / path
    return path


def _percentile(values: Sequence[float], percentile: float) -> Optional[float]:
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


def latency_percentiles_by_mode(results: List[dict], percentiles: Sequence[float]) -> Dict[str, Dict[float, float]]:
    by_mode: Dict[str, List[float]] = defaultdict(list)
    for row in results:
        by_mode[row["mode"]].append(row.get("latency_ms", 0.0))
    output: Dict[str, Dict[float, float]] = {}
    for mode, latencies in by_mode.items():
        if not latencies:
            continue
        output[mode] = {}
        for percentile in percentiles:
            pct = max(0.0, min(100.0, float(percentile)))
            value = _percentile(latencies, pct)
            if value is not None:
                output[mode][pct] = value
    return output


def print_console_summary(results: List[dict], percentiles: Sequence[float]) -> None:
    aggregates = aggregate_by_mode(results)
    if not aggregates:
        print("No results produced.")
        return
    deltas = compute_mode_deltas(aggregates)
    percentile_map = latency_percentiles_by_mode(results, percentiles)

    headers = ["mode", "latency_ms"]
    headers.extend(
        [f"latency_p{int(p) if float(p).is_integer() else float(p)}" for p in percentiles]
    )
    headers.extend(["tokens_in", "tokens_out", "rule_score", "llm_score", "cost_usd"])
    rows = []
    for mode, metrics in sorted(aggregates.items()):
        row = [mode]
        row.append(f"{metrics.get('latency_ms', 0.0):.3f}")
        for percentile in percentiles:
            label = f"latency_p{int(percentile) if float(percentile).is_integer() else float(percentile)}"
            value = percentile_map.get(mode, {}).get(float(percentile))
            row.append(f"{value:.3f}" if value is not None else "")
        for metric in ("tokens_in", "tokens_out", "rule_score", "llm_score", "cost_usd"):
            value = aggregates[mode].get(metric)
            row.append(f"{value:.3f}" if isinstance(value, (int, float)) else "")
        rows.append(row)

    print("\nAverage metrics by mode")
    print(tabulate(rows, headers=headers, tablefmt="github"))

    if deltas:
        delta_headers = [
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
        delta_rows = []
        for mode, metrics in sorted(deltas.items()):
            row = [mode]
            for metric in delta_headers[1:]:
                value = metrics.get(metric)
                row.append(f"{value:+.3f}" if isinstance(value, (int, float)) else "")
            delta_rows.append(row)
        print("\nDelta vs baseline (default percentiles)")
        print(tabulate(delta_rows, headers=delta_headers, tablefmt="github"))


def main(argv: Optional[Iterable[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    config_path = _resolve_to_path(args.config, ROOT)
    config = load_config(config_path)
    config = apply_overrides(config, args, ROOT)

    provider_name, notice = resolve_provider_name(config.provider, args.provider)
    if notice:
        print(notice)

    model_name = args.model or config.model
    config = replace(config, provider=provider_name, model=model_name)
    validate_config(config, base_dir=ROOT)

    percentiles = args.percentiles or [50.0, 95.0]
    percentiles = [max(0.0, min(100.0, float(p))) for p in percentiles]
    if not percentiles:
        percentiles = [50.0, 95.0]

    provider = ProviderFactory.create(config.provider, config.model)
    results = run_benchmark(config, provider=provider)

    output_dir = _resolve_to_path(config.output_dir, ROOT)
    artifacts = generate_reports(results, output_dir)

    results_json_path = (
        Path(args.results_json).expanduser().resolve()
        if args.results_json
        else output_dir / "results.json"
    )
    results_json_path.parent.mkdir(parents=True, exist_ok=True)
    results_json_path.write_text(json.dumps(results, indent=2))

    print("Benchmark completed.")
    print(f"- Provider: {config.provider} (model: {config.model})")
    print(f"- CSV: {artifacts['csv']}")
    print(f"- Markdown: {artifacts['markdown']}")
    print(f"- JSON: {results_json_path}")

    print_console_summary(results, percentiles)


if __name__ == "__main__":
    main()
