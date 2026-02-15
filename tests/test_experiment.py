import json
from pathlib import Path

from bench.experiment import ExperimentOptions, run_experiment
from bench.harness import BenchmarkConfig, PricingConfig
from bench.regression import RegressionThresholds, build_regression_report, write_regression_report


ROOT = Path(__file__).resolve().parents[1]


def test_run_experiment_matrix_and_checkpoint_resume(tmp_path):
    config = BenchmarkConfig(
        modes=["baseline", "progressive"],
        tasks=["tasks/t1_rewrite_brand.json"],
        repetitions=2,
        provider="mock",
        model="mock-model",
        judge="rule",
        skill_root=ROOT / "skills" / "brand-voice",
        pricing=PricingConfig(input_per_1k=1.0, output_per_1k=1.0),
    )
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    options = ExperimentOptions(
        models=["mock-a", "mock-b"],
        judges=["rule"],
        max_workers=2,
        retry_attempts=1,
        rate_limit_qps=0.0,
        checkpoint_path=str(checkpoint_path),
        resume=True,
    )

    results, meta = run_experiment(config, options, base_dir=ROOT)

    assert len(results) == 8
    assert meta["total_cases"] == 8
    assert meta["executed_cases"] == 8
    assert meta["reused_cases"] == 0
    assert checkpoint_path.exists()
    assert len(checkpoint_path.read_text().splitlines()) == 8
    assert {row["model"] for row in results} == {"mock-a", "mock-b"}

    resumed_results, resumed_meta = run_experiment(config, options, base_dir=ROOT)
    assert len(resumed_results) == 8
    assert resumed_meta["executed_cases"] == 0
    assert resumed_meta["reused_cases"] == 8
    assert len(checkpoint_path.read_text().splitlines()) == 8


def test_regression_report_flags_regressions_and_writes_artifacts(tmp_path):
    results = []
    baseline_latencies = [100.0, 102.0, 99.0, 101.0]
    progressive_latencies = [168.0, 170.0, 172.0, 169.0]
    for idx, latency in enumerate(baseline_latencies):
        results.append(
            {
                "task_id": "t1",
                "mode": "baseline",
                "model": "mock-a",
                "judge": "rule",
                "iteration": idx,
                "latency_ms": latency,
                "rule_score": 0.92,
                "cost_usd": 0.30,
            }
        )
    for idx, latency in enumerate(progressive_latencies):
        results.append(
            {
                "task_id": "t1",
                "mode": "progressive",
                "model": "mock-a",
                "judge": "rule",
                "iteration": idx,
                "latency_ms": latency,
                "rule_score": 0.55,
                "cost_usd": 0.95,
            }
        )

    thresholds = RegressionThresholds(
        latency_regression_pct=20.0,
        cost_regression_pct=100.0,
        rule_score_drop=0.2,
        alpha=1.0,
        min_effect_size=0.0,
        bootstrap_samples=120,
        permutation_samples=120,
        confidence=0.95,
        random_seed=11,
    )
    report = build_regression_report(results, thresholds)
    assert report["comparison_count"] >= 3
    assert report["regression_count"] >= 2
    assert not report["passed"]

    paths = write_regression_report(report, output_dir=tmp_path)
    assert paths["regression_json"].exists()
    assert paths["regression_markdown"].exists()
    loaded = json.loads(paths["regression_json"].read_text())
    assert loaded["regression_count"] == report["regression_count"]
    assert "Flagged Regressions" in paths["regression_markdown"].read_text()
