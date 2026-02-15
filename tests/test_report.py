from pathlib import Path

from bench.report import (
    aggregate_by_mode,
    aggregate_by_task_mode,
    compute_mode_deltas,
    compute_task_deltas,
    generate_reports,
)


def sample_results():
    return [
        {
            "task_id": "t1",
            "mode": "baseline",
            "latency_ms": 100.0,
            "rule_score": 0.6,
            "tokens_in": 50,
            "tokens_out": 10,
            "cost_usd": 0.2,
        },
        {
            "task_id": "t1",
            "mode": "progressive",
            "latency_ms": 80.0,
            "rule_score": 0.9,
            "tokens_in": 40,
            "tokens_out": 12,
            "cost_usd": 0.25,
        },
        {
            "task_id": "t1",
            "mode": "naive",
            "latency_ms": 140.0,
            "rule_score": 0.7,
            "tokens_in": 70,
            "tokens_out": 12,
            "cost_usd": 0.3,
        },
    ]


def sample_results_without_baseline():
    return [
        {
            "task_id": "t1",
            "mode": "progressive",
            "latency_ms": 80.0,
            "rule_score": 0.9,
            "tokens_in": 40,
            "tokens_out": 12,
            "cost_usd": 0.25,
        }
    ]


def test_mode_deltas_computed_against_baseline():
    aggregates = aggregate_by_mode(sample_results())
    assert aggregates["baseline"]["latency_p50"] == 100.0
    assert aggregates["naive"]["latency_p95"] == 140.0
    assert "cost_usd" in aggregates["baseline"]
    deltas = compute_mode_deltas(aggregates)

    assert "progressive" in deltas
    assert deltas["progressive"]["latency_ms"] == -20.0
    assert deltas["progressive"]["latency_p50"] == -20.0
    assert deltas["progressive"]["rule_score"] == 0.3

    assert "naive" in deltas
    assert deltas["naive"]["latency_ms"] == 40.0
    assert deltas["naive"]["tokens_in"] == 20.0
    assert "cost_usd" in deltas["naive"]


def test_task_deltas_include_each_mode():
    task_aggregates = aggregate_by_task_mode(sample_results())
    deltas = compute_task_deltas(task_aggregates)

    assert set(deltas["t1"].keys()) == {"naive", "progressive"}
    assert deltas["t1"]["progressive"]["latency_ms"] == -20.0
    assert deltas["t1"]["naive"]["rule_score"] == 0.1
    assert "cost_usd" in deltas["t1"]["progressive"]


def test_generate_reports_creates_task_chart(tmp_path):
    artifacts = generate_reports(sample_results(), tmp_path)
    assert "markdown" in artifacts and Path(artifacts["markdown"]).exists()
    assert any(key.endswith("_latency") for key in artifacts)
    chart_paths = [Path(path) for key, path in artifacts.items() if key.endswith("_latency")]
    assert all(p.exists() for p in chart_paths)
    markdown_text = Path(artifacts["markdown"]).read_text()
    assert "cost_usd" in markdown_text
    aggregates_csv = Path(artifacts["aggregates_csv"])
    assert aggregates_csv.exists()
    content = aggregates_csv.read_text()
    assert "latency_p50" in content
    assert "cost_usd" in content


def test_generate_reports_creates_html_assets(tmp_path):
    artifacts = generate_reports(sample_results(), tmp_path)
    html_root = Path(tmp_path) / "html"
    assert html_root.exists()
    assert (html_root / "index.html").exists()
    assert (html_root / "assets" / "style.css").exists()
    assert (html_root / "assets" / "app.js").exists()


def test_html_report_contains_sections(tmp_path):
    generate_reports(sample_results(), tmp_path)
    html_text = (Path(tmp_path) / "html" / "index.html").read_text()
    assert "Overview" in html_text
    assert "Aggregated metrics" in html_text
    assert "Delta vs baseline" in html_text
    assert "Help & Methodology" in html_text


def test_html_report_copies_charts(tmp_path):
    generate_reports(sample_results(), tmp_path)
    html_assets = Path(tmp_path) / "html" / "assets"
    assert (html_assets / "chart_latency.png").exists()


def test_html_report_empty_state(tmp_path):
    generate_reports([], tmp_path)
    html_text = (Path(tmp_path) / "html" / "index.html").read_text()
    assert "No benchmark results were recorded" in html_text
    assert "skillbench-pd --modes baseline progressive --repetitions 1" in html_text


def test_html_report_warns_when_baseline_missing(tmp_path):
    generate_reports(sample_results_without_baseline(), tmp_path)
    html_text = (Path(tmp_path) / "html" / "index.html").read_text()
    assert "Baseline mode is required to compute deltas." in html_text
