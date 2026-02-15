from pathlib import Path

from bench.harness import (
    BenchmarkConfig,
    build_prompt,
    load_task,
    load_skill_definition,
    run_benchmark,
)
from bench.providers import MockProvider


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "brand-voice"


def test_prompt_construction_modes():
    task = load_task(ROOT / "tasks/t1_rewrite_brand.json")
    skill = load_skill_definition(SKILL_ROOT)

    baseline = build_prompt("baseline", task, SKILL_ROOT, skill)
    naive = build_prompt("naive", task, SKILL_ROOT, skill)
    progressive = build_prompt("progressive", task, SKILL_ROOT, skill)

    assert "Goal:" in baseline and "SKILL.md" not in baseline
    assert "[file:" in naive and "references/brand-voice.md" in naive
    assert "[selected-section:" in progressive
    assert "[reference: references/brand-voice.md]" in progressive


def test_progressive_prompt_selects_reporting_reference():
    task = load_task(ROOT / "tasks/t3_summarize_metrics.json")
    skill = load_skill_definition(SKILL_ROOT)

    progressive = build_prompt("progressive", task, SKILL_ROOT, skill)

    assert "[selected-section: Summarize metrics]" in progressive
    assert "[reference: references/reporting-style.md]" in progressive


def test_run_benchmark_collects_records():
    config = BenchmarkConfig(
        modes=["baseline", "progressive"],
        tasks=["tasks/t2_format_policy.json"],
        repetitions=1,
        provider="mock",
        model="mock-model",
        judge="rule",
    )
    provider = MockProvider()

    results = run_benchmark(config, provider=provider)

    assert len(results) == 2
    for record in results:
        assert record["task_id"] == "t2_format_policy"
        assert record["mode"] in {"baseline", "progressive"}
        assert "latency_ms" in record
        assert record["rule_score"] >= 0.0
        assert record["provider"] == "mock"
        assert record["model"] == "mock-model"
        assert record["judge"] == "rule"
