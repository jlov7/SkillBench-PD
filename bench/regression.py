from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Dict, List, Sequence, Tuple

from tabulate import tabulate


@dataclass
class RegressionThresholds:
    latency_regression_pct: float = 250.0
    cost_regression_pct: float = 250.0
    rule_score_drop: float = 0.20
    alpha: float = 0.10
    min_effect_size: float = 0.10
    bootstrap_samples: int = 400
    permutation_samples: int = 400
    confidence: float = 0.95
    random_seed: int = 17


def build_regression_report(
    results: List[Dict],
    thresholds: RegressionThresholds,
    *,
    baseline_mode: str = "baseline",
) -> Dict:
    metrics = ("latency_ms", "rule_score", "cost_usd")
    grouped: Dict[Tuple[str, str, str], Dict[str, Dict[str, List[float]]]] = {}
    for row in results:
        group = (
            str(row.get("task_id", "")),
            str(row.get("model", "")),
            str(row.get("judge", "")),
        )
        mode = str(row.get("mode", ""))
        grouped.setdefault(group, {}).setdefault(mode, {})
        for metric in metrics:
            value = row.get(metric)
            if isinstance(value, (int, float)):
                grouped[group][mode].setdefault(metric, []).append(float(value))

    comparisons: List[Dict] = []
    regressions: List[Dict] = []

    for group_key, mode_map in sorted(grouped.items()):
        task_id, model, judge = group_key
        baseline_metrics = mode_map.get(baseline_mode, {})
        if not baseline_metrics:
            continue
        for mode, metric_map in sorted(mode_map.items()):
            if mode == baseline_mode:
                continue
            for metric in metrics:
                baseline_values = baseline_metrics.get(metric, [])
                candidate_values = metric_map.get(metric, [])
                if not baseline_values or not candidate_values:
                    continue

                seed = _stable_seed(
                    f"{thresholds.random_seed}|{task_id}|{model}|{judge}|{mode}|{metric}"
                )
                rng = random.Random(seed)
                baseline_mean = fmean(baseline_values)
                candidate_mean = fmean(candidate_values)
                delta = candidate_mean - baseline_mean
                delta_pct = None
                if baseline_mean != 0:
                    delta_pct = (delta / abs(baseline_mean)) * 100.0
                ci_low, ci_high = bootstrap_delta_ci(
                    baseline_values,
                    candidate_values,
                    confidence=thresholds.confidence,
                    samples=thresholds.bootstrap_samples,
                    rng=rng,
                )
                p_value = permutation_test_p_value(
                    baseline_values,
                    candidate_values,
                    samples=thresholds.permutation_samples,
                    rng=rng,
                )
                effect_size = cohens_d(candidate_values, baseline_values)
                significant = p_value <= thresholds.alpha
                effect_ok = abs(effect_size) >= thresholds.min_effect_size

                regression_flag, reason = _flag_regression(
                    metric=metric,
                    delta=delta,
                    delta_pct=delta_pct,
                    significant=significant,
                    effect_ok=effect_ok,
                    thresholds=thresholds,
                )
                comparison = {
                    "task_id": task_id,
                    "model": model,
                    "judge": judge,
                    "metric": metric,
                    "baseline_mode": baseline_mode,
                    "candidate_mode": mode,
                    "baseline_mean": round(baseline_mean, 6),
                    "candidate_mean": round(candidate_mean, 6),
                    "delta": round(delta, 6),
                    "delta_pct": round(delta_pct, 6) if delta_pct is not None else None,
                    "ci_low": round(ci_low, 6),
                    "ci_high": round(ci_high, 6),
                    "p_value": round(p_value, 6),
                    "effect_size": round(effect_size, 6),
                    "significant": significant,
                    "regression": regression_flag,
                    "reason": reason,
                    "n_baseline": len(baseline_values),
                    "n_candidate": len(candidate_values),
                }
                comparisons.append(comparison)
                if regression_flag:
                    regressions.append(comparison)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_mode": baseline_mode,
        "thresholds": asdict(thresholds),
        "total_records": len(results),
        "comparison_count": len(comparisons),
        "regression_count": len(regressions),
        "passed": len(regressions) == 0,
        "comparisons": comparisons,
        "regressions": regressions,
    }
    return report


def write_regression_report(
    report: Dict,
    *,
    output_dir: Path,
    json_path: Path | None = None,
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_output = json_path or (output_dir / "regression_report.json")
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2))

    md_output = json_output.with_suffix(".md")
    md_output.write_text(_render_regression_markdown(report))
    return {"regression_json": json_output, "regression_markdown": md_output}


def bootstrap_delta_ci(
    baseline_values: Sequence[float],
    candidate_values: Sequence[float],
    *,
    confidence: float,
    samples: int,
    rng: random.Random,
) -> Tuple[float, float]:
    if not baseline_values or not candidate_values:
        return (0.0, 0.0)
    if samples <= 1:
        delta = fmean(candidate_values) - fmean(baseline_values)
        return (delta, delta)
    diffs: List[float] = []
    for _ in range(samples):
        sample_base = [baseline_values[rng.randrange(len(baseline_values))] for _ in baseline_values]
        sample_candidate = [
            candidate_values[rng.randrange(len(candidate_values))] for _ in candidate_values
        ]
        diffs.append(fmean(sample_candidate) - fmean(sample_base))
    diffs.sort()
    tail = (1.0 - confidence) / 2.0
    low_index = max(0, min(samples - 1, int(tail * samples)))
    high_index = max(0, min(samples - 1, int((1.0 - tail) * samples) - 1))
    return diffs[low_index], diffs[high_index]


def permutation_test_p_value(
    baseline_values: Sequence[float],
    candidate_values: Sequence[float],
    *,
    samples: int,
    rng: random.Random,
) -> float:
    if not baseline_values or not candidate_values:
        return 1.0
    observed = abs(fmean(candidate_values) - fmean(baseline_values))
    merged = list(baseline_values) + list(candidate_values)
    base_size = len(baseline_values)
    if samples <= 1:
        return 1.0
    extreme = 0
    for _ in range(samples):
        rng.shuffle(merged)
        perm_base = merged[:base_size]
        perm_candidate = merged[base_size:]
        perm_delta = abs(fmean(perm_candidate) - fmean(perm_base))
        if perm_delta >= observed:
            extreme += 1
    return (extreme + 1) / (samples + 1)


def cohens_d(sample_a: Sequence[float], sample_b: Sequence[float]) -> float:
    if not sample_a or not sample_b:
        return 0.0
    mean_a = fmean(sample_a)
    mean_b = fmean(sample_b)
    var_a = _sample_variance(sample_a)
    var_b = _sample_variance(sample_b)
    pooled_denom = len(sample_a) + len(sample_b) - 2
    if pooled_denom <= 0:
        return 0.0
    pooled_var = ((len(sample_a) - 1) * var_a + (len(sample_b) - 1) * var_b) / pooled_denom
    if pooled_var <= 0:
        return 0.0
    return (mean_a - mean_b) / math.sqrt(pooled_var)


def _sample_variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_value = fmean(values)
    return sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)


def _flag_regression(
    *,
    metric: str,
    delta: float,
    delta_pct: float | None,
    significant: bool,
    effect_ok: bool,
    thresholds: RegressionThresholds,
) -> Tuple[bool, str]:
    if metric == "latency_ms":
        if (
            delta_pct is not None
            and delta_pct >= thresholds.latency_regression_pct
            and significant
            and effect_ok
        ):
            return True, "Latency regression exceeds threshold"
        return False, ""

    if metric == "cost_usd":
        if (
            delta_pct is not None
            and delta_pct >= thresholds.cost_regression_pct
            and significant
            and effect_ok
        ):
            return True, "Cost regression exceeds threshold"
        return False, ""

    if metric == "rule_score":
        if delta <= -thresholds.rule_score_drop and significant and effect_ok:
            return True, "Rule score regression exceeds threshold"
        return False, ""

    return False, ""


def _stable_seed(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _render_regression_markdown(report: Dict) -> str:
    lines = [
        "# Regression Gate Report",
        "",
        f"- Generated at: {report.get('generated_at', '')}",
        f"- Baseline mode: {report.get('baseline_mode', 'baseline')}",
        f"- Passed: {report.get('passed')}",
        f"- Comparisons: {report.get('comparison_count', 0)}",
        f"- Regressions: {report.get('regression_count', 0)}",
        "",
        "## Thresholds",
        "```json",
        json.dumps(report.get("thresholds", {}), indent=2),
        "```",
        "",
    ]

    regressions = report.get("regressions", [])
    if regressions:
        headers = [
            "task_id",
            "model",
            "judge",
            "candidate_mode",
            "metric",
            "delta",
            "delta_pct",
            "p_value",
            "effect_size",
            "reason",
        ]
        rows = []
        for item in regressions:
            rows.append(
                [
                    item.get("task_id", ""),
                    item.get("model", ""),
                    item.get("judge", ""),
                    item.get("candidate_mode", ""),
                    item.get("metric", ""),
                    _fmt(item.get("delta")),
                    _fmt(item.get("delta_pct")),
                    _fmt(item.get("p_value")),
                    _fmt(item.get("effect_size")),
                    item.get("reason", ""),
                ]
            )
        lines.append("## Flagged Regressions")
        lines.append(tabulate(rows, headers=headers, tablefmt="github"))
        lines.append("")
    else:
        lines.append("## Flagged Regressions")
        lines.append("_No regressions flagged._")
        lines.append("")

    return "\n".join(lines)


def _fmt(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return ""
