from bench import judges
from bench.providers import MockProvider


def test_brand_guideline_scoring_penalises_banned_words():
    task = {
        "id": "t1_rewrite_brand",
        "rules": {"avoid": ["revolutionary"]},
    }
    bad_output = "This revolutionary launch changes everything."
    good_output = "This update improves everyday workflows."

    bad_score = judges.score_rule(task, bad_output)
    good_score = judges.score_rule(task, good_output)

    assert good_score > bad_score
    assert bad_score < 1.0


def test_policy_format_scoring_checks_heading_and_bullets():
    task = {
        "id": "t2_format_policy",
        "rules": {"format": "bullets", "heading_case": "sentence"},
    }
    formatted = "Policy: data handling\n- Keep data safe.\n- Never share."
    malformed = "POLICY DATA\nKeep data safe."

    assert judges.score_rule(task, formatted) == 1.0
    assert judges.score_rule(task, malformed) == 0.5


def test_llm_judge_falls_back_for_mock_provider():
    task = {
        "id": "t1_rewrite_brand",
        "goal": "Rewrite copy.",
        "input": "Example input",
        "rules": {"avoid": ["bad"]},
    }
    provider = MockProvider()
    output = "An improved message for teams."

    result = judges.evaluate_output(task, output, judge_mode="llm", provider=provider)

    assert result.llm_score is not None
    assert 1.0 <= result.llm_score <= 5.0
    assert result.rule_score <= 1.0


def test_metrics_report_scoring_requires_three_bullets():
    task = {
        "id": "t3_summarize_metrics",
        "rules": {"bullets": 3, "tone": "analytical"},
    }
    good_output = (
        "Product engagement rose across the board.\n"
        "- Active users increased 8% QoQ driven by onboarding updates.\n"
        "- Churn decreased 2 points as support stabilized.\n"
        "- Response time fell from 480 ms to 410 ms after caching."
    )
    bad_output = "Great job! Metrics are amazing!\n- Users up"

    assert judges.score_rule(task, good_output) == 1.0
    assert judges.score_rule(task, bad_output) <= 0.5
