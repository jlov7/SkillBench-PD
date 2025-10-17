from pathlib import Path

from bench.harness import (
    BenchmarkConfig,
    build_prompt,
    load_task,
    parse_skill_topics,
    run_benchmark,
)
from bench.providers import MockProvider


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "brand_voice"


def test_prompt_construction_modes():
    task = load_task(ROOT / "tasks/t1_rewrite_brand.json")
    topics = parse_skill_topics(SKILL_ROOT / "SKILL.md")

    baseline = build_prompt("baseline", task, SKILL_ROOT, topics)
    naive = build_prompt("naive", task, SKILL_ROOT, topics)
    progressive = build_prompt("progressive", task, SKILL_ROOT, topics)

    assert "Goal:" in baseline and "SKILL.md" not in baseline
    assert "[file:" in naive and "style-guide/brand-voice.md" in naive
    assert "[selected-topic:" in progressive
    assert "[reference: style-guide/brand-voice.md]" in progressive


def test_progressive_prompt_selects_reporting_reference():
    task = load_task(ROOT / "tasks/t3_summarize_metrics.json")
    topics = parse_skill_topics(SKILL_ROOT / "SKILL.md")

    progressive = build_prompt("progressive", task, SKILL_ROOT, topics)

    assert "[selected-topic: summarize_metrics]" in progressive
    assert "[reference: reference/reporting-style.md]" in progressive


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
