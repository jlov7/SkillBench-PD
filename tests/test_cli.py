import json
from pathlib import Path

import pytest

from bench import cli


ROOT = Path(__file__).resolve().parents[1]


def test_cli_runs_with_mock_provider(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    output_dir = tmp_path / "out"
    results_json = tmp_path / "raw.json"

    args = [
        "--config",
        str(ROOT / "configs/bench.yaml"),
        "--output-dir",
        str(output_dir),
        "--results-json",
        str(results_json),
        "--repetitions",
        "1",
        "--modes",
        "baseline",
        "progressive",
        "--tasks",
        str(ROOT / "tasks/t1_rewrite_brand.json"),
        "--provider",
        "mock",
        "--pricing-input",
        "1",
        "--pricing-output",
        "1",
        "--percentiles",
        "50",
        "90",
    ]

    cli.main(args)
    captured = capsys.readouterr()
    assert "Benchmark completed." in captured.out
    assert "latency_p50" in captured.out
    assert "cost_usd" in captured.out

    csv_path = output_dir / "results.csv"
    md_path = output_dir / "results.md"
    assert csv_path.exists()
    assert md_path.exists()
    assert results_json.exists()

    data = json.loads(results_json.read_text())
    assert data
    assert all(record["mode"] in {"baseline", "progressive"} for record in data)
    baseline_record = next(rec for rec in data if rec["mode"] == "baseline")
    expected_cost = ((baseline_record.get("tokens_in", 0) or 0) + (baseline_record.get("tokens_out", 0) or 0)) / 1000
    assert abs(baseline_record.get("cost_usd", 0) - round(expected_cost, 6)) < 1e-6


def test_cli_auto_provider_falls_back_without_key(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    output_dir = tmp_path / "out"

    args = [
        "--config",
        str(ROOT / "configs/bench.yaml"),
        "--output-dir",
        str(output_dir),
        "--repetitions",
        "1",
        "--modes",
        "baseline",
        "--tasks",
        str(ROOT / "tasks/t1_rewrite_brand.json"),
        "--provider",
        "auto",
    ]

    cli.main(args)
    captured = capsys.readouterr()
    assert "falling back to mock provider" in captured.out
    assert "latency_p50" in captured.out
    assert (output_dir / "results.csv").exists()


def test_cli_open_report_invokes_browser(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr("bench.cli._open_report", lambda path: opened.append(path))

    args = [
        "--config",
        str(ROOT / "configs/bench.yaml"),
        "--output-dir",
        str(tmp_path),
        "--repetitions",
        "1",
        "--modes",
        "baseline",
        "--tasks",
        str(ROOT / "tasks/t1_rewrite_brand.json"),
        "--provider",
        "mock",
        "--open-report",
    ]

    cli.main(args)
    assert opened


def test_cli_orchestrate_writes_regression_report(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    output_dir = tmp_path / "orchestrated"
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    regression_path = tmp_path / "regression.json"

    args = [
        "--config",
        str(ROOT / "configs/bench.yaml"),
        "--output-dir",
        str(output_dir),
        "--tasks",
        str(ROOT / "tasks/t1_rewrite_brand.json"),
        "--modes",
        "baseline",
        "progressive",
        "--repetitions",
        "2",
        "--provider",
        "mock",
        "--orchestrate",
        "--matrix-models",
        "mock-a",
        "mock-b",
        "--matrix-judges",
        "rule",
        "--max-workers",
        "2",
        "--checkpoint-path",
        str(checkpoint_path),
        "--regression-report",
        str(regression_path),
    ]

    cli.main(args)
    captured = capsys.readouterr()
    assert "Orchestration: total=" in captured.out
    assert "Regression gate:" in captured.out
    assert regression_path.exists()
    assert regression_path.with_suffix(".md").exists()
    assert checkpoint_path.exists()


def test_cli_fail_on_regression_exits_non_zero(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    output_dir = tmp_path / "gate"

    args = [
        "--config",
        str(ROOT / "configs/bench.yaml"),
        "--output-dir",
        str(output_dir),
        "--tasks",
        str(ROOT / "tasks/t1_rewrite_brand.json"),
        "--modes",
        "baseline",
        "progressive",
        "--repetitions",
        "3",
        "--provider",
        "mock",
        "--orchestrate",
        "--matrix-models",
        "mock-model",
        "--matrix-judges",
        "rule",
        "--fail-on-regression",
        "--latency-regression-pct",
        "0.01",
        "--cost-regression-pct",
        "0.01",
        "--rule-score-drop",
        "0.001",
        "--regression-alpha",
        "1.0",
        "--min-effect-size",
        "0.0",
        "--bootstrap-samples",
        "80",
        "--permutation-samples",
        "80",
    ]

    with pytest.raises(SystemExit) as exc:
        cli.main(args)
    assert exc.value.code == 2
