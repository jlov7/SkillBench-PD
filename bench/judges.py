from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Optional

from .providers import BaseProvider, MockProvider


# --- Rule-based scorers ----------------------------------------------------

def score_brand_guidelines(text: str, rules: dict) -> float:
    penalties = 0
    banned = rules.get("avoid", [])
    for word in banned:
        if re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE):
            penalties += 1
    sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
    long_sentences = sum(1 for s in sentences if len(s.split()) > 26)
    penalties += long_sentences * 0.5
    return float(max(0.0, 1.0 - 0.2 * penalties))


def score_policy_format(text: str, rules: dict) -> float:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return 0.0
    bullets = [ln for ln in lines[1:] if ln.startswith(("-", "*"))]
    heading = lines[0]
    expected_case = rules.get("heading_case", "sentence")
    heading_ok = expected_case == "sentence" and is_sentence_case(heading)
    bullets_ok = rules.get("format") == "bullets" and len(bullets) >= 2
    return 1.0 if heading_ok and bullets_ok else 0.5


def score_metrics_report(text: str, rules: dict) -> float:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return 0.0
    headline = lines[0]
    target_bullets = int(rules.get("bullets", 3))
    bullets = [ln for ln in lines[1:] if ln.startswith(("-", "*"))]
    bullet_count_ok = len(bullets) == target_bullets
    percent_mentions = sum(1 for ln in bullets if "%" in ln or any(char.isdigit() for char in ln))
    percent_ok = percent_mentions >= min(2, target_bullets)
    exclamation = "!" in text
    tone_ok = rules.get("tone") == "analytical" and not exclamation
    headline_ok = headline[:1].isupper()
    if bullet_count_ok and percent_ok and tone_ok and headline_ok:
        return 1.0
    if bullet_count_ok and tone_ok:
        return 0.8
    return 0.5


def is_sentence_case(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    rest = stripped[1:]
    target = "".join(ch.lower() if ch.isalpha() else ch for ch in rest)
    return stripped[0].isupper() and rest == target


def score_rule(task_json: dict, output: str) -> float:
    task_id = task_json.get("id", "")
    if task_id.startswith("t1_rewrite_brand"):
        return score_brand_guidelines(output, task_json.get("rules", {}))
    if task_id.startswith("t2_format_policy"):
        return score_policy_format(output, task_json.get("rules", {}))
    if task_id.startswith("t3_summarize_metrics"):
        return score_metrics_report(output, task_json.get("rules", {}))
    return 0.5


# --- Optional LLM-as-judge --------------------------------------------------

LLM_PROMPT_TEMPLATE = """You are a meticulous reviewer. Rate how well the assistant output follows the task instructions.

Task ID: {task_id}
Goal: {goal}
Original input:
{task_input}

Assistant output:
{output}

Provide a single integer rating from 1 (non-compliant) to 5 (fully compliant) preceded by 'score:'."""


@dataclass
class JudgeResult:
    rule_score: float
    llm_score: Optional[float] = None


def llm_score(task_json: dict, output: str, provider: BaseProvider) -> float:
    prompt = LLM_PROMPT_TEMPLATE.format(
        task_id=task_json.get("id", ""),
        goal=task_json.get("goal", ""),
        task_input=task_json.get("input", ""),
        output=output,
    )
    result = provider.infer(prompt)
    match = re.search(r"score:\s*([1-5])", result.output)
    if match:
        return float(int(match.group(1)))
    # Fall back to rule score scaled to 1-5 for deterministic mocks.
    return max(1.0, min(5.0, round(score_rule(task_json, output) * 5)))


def evaluate_output(task_json: dict, output: str, judge_mode: str, provider: Optional[BaseProvider]) -> JudgeResult:
    rule = score_rule(task_json, output)
    if judge_mode.lower() != "llm":
        return JudgeResult(rule_score=rule)

    if provider is None or isinstance(provider, MockProvider):
        llm = max(1.0, min(5.0, round(rule * 5)))
        return JudgeResult(rule_score=rule, llm_score=llm)

    try:
        llm = llm_score(task_json, output, provider)
    except Exception:
        llm = max(1.0, min(5.0, round(rule * 5)))
    return JudgeResult(rule_score=rule, llm_score=llm)
