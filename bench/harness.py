from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import yaml

from .judges import JudgeResult, evaluate_output
from .providers import BaseProvider, ProviderFactory, ProviderResult


@dataclass
class BenchmarkConfig:
    modes: List[str]
    tasks: List[str]
    repetitions: int
    provider: str
    model: str
    judge: str = "rule"
    output_dir: str = "results"
    skill_root: Path = Path("skills/brand_voice")
    pricing: "PricingConfig | None" = None


@dataclass
class PricingConfig:
    input_per_1k: float = 0.0
    output_per_1k: float = 0.0


ALLOWED_MODES = {"baseline", "naive", "progressive"}
ALLOWED_JUDGES = {"rule", "llm"}


def load_config(path: str | Path) -> BenchmarkConfig:
    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text())
    pricing_data = data.get("pricing")
    pricing = None
    if isinstance(pricing_data, dict):
        pricing = PricingConfig(
            input_per_1k=float(pricing_data.get("input_per_1k", 0.0) or 0.0),
            output_per_1k=float(pricing_data.get("output_per_1k", 0.0) or 0.0),
        )

    config = BenchmarkConfig(
        modes=data.get("modes", []),
        tasks=data.get("tasks", []),
        repetitions=int(data.get("repetitions", 1)),
        provider=data.get("provider", "mock"),
        model=data.get("model", "claude-3-5-sonnet"),
        judge=data.get("judge", "rule"),
        output_dir=data.get("output_dir", "results"),
        skill_root=Path(data.get("skill_root", "skills/brand_voice")),
        pricing=pricing,
    )
    validate_config(config, base_dir=config_path.parent)
    return config


def validate_config(config: BenchmarkConfig, base_dir: Path | None = None) -> None:
    base = base_dir or Path(".")
    if not config.modes:
        raise ValueError("Config must specify at least one mode.")
    invalid_modes = [mode for mode in config.modes if mode not in ALLOWED_MODES]
    if invalid_modes:
        raise ValueError(f"Unsupported modes: {invalid_modes}. Allowed: {sorted(ALLOWED_MODES)}")

    if not config.tasks:
        raise ValueError("Config must list at least one task.")
    missing_tasks = []
    for task_path in config.tasks:
        candidate = _resolve_with_base(task_path, base)
        if candidate is None or not candidate.exists():
            missing_tasks.append(task_path)
    if missing_tasks:
        raise FileNotFoundError(f"Task file(s) not found: {missing_tasks}")

    if config.repetitions < 1:
        raise ValueError("Repetitions must be >= 1.")

    if config.judge not in ALLOWED_JUDGES:
        raise ValueError(f"Judge must be one of {sorted(ALLOWED_JUDGES)}")

    if config.pricing:
        if config.pricing.input_per_1k < 0 or config.pricing.output_per_1k < 0:
            raise ValueError("Pricing rates must be non-negative.")

    skill_root_resolved = _resolve_with_base(str(config.skill_root), base)
    if skill_root_resolved is None or not skill_root_resolved.exists():
        raise FileNotFoundError(f"Skill root does not exist: {config.skill_root}")
    skill_root = skill_root_resolved
    if not skill_root.exists():
        raise FileNotFoundError(f"Skill root does not exist: {skill_root}")
    skill_md = skill_root / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"Missing SKILL.md at {skill_md}")


def _resolve_with_base(path_str: str, base: Path) -> Path | None:
    path_obj = Path(path_str)
    if path_obj.is_absolute():
        return path_obj
    search_roots = [base, *base.parents]
    for root in search_roots:
        candidate = (root / path_obj).resolve()
        if candidate.exists():
            return candidate
    # Return the immediate resolution even if missing so callers can inspect
    return (base / path_obj).resolve()


def run_benchmark(config: BenchmarkConfig, provider: Optional[BaseProvider] = None) -> List[Dict]:
    results: List[Dict] = []
    provider = provider or ProviderFactory.create(config.provider, config.model)
    skill_root = config.skill_root
    topics = parse_skill_topics(skill_root / "SKILL.md")

    for task_path in config.tasks:
        task = load_task(Path(task_path))
        for mode in config.modes:
            for iteration in range(config.repetitions):
                prompt = build_prompt(
                    mode=mode,
                    task=task,
                    skill_root=skill_root,
                    topics=topics,
                )
                provider_result = provider.infer(prompt)
                judges = evaluate_output(task, provider_result.output, config.judge, provider)
                record = build_record(
                    task_path=task_path,
                    task=task,
                    mode=mode,
                    iteration=iteration,
                    prompt=prompt,
                    provider_result=provider_result,
                    judges=judges,
                    pricing=config.pricing,
                )
                results.append(record)
                time.sleep(0.02)  # keep results stable without hammering real APIs
    return results


def build_record(
    task_path: str,
    task: dict,
    mode: str,
    iteration: int,
    prompt: str,
    provider_result: ProviderResult,
    judges: JudgeResult,
    pricing: PricingConfig | None = None,
) -> Dict:
    record: Dict = {
        "task_path": task_path,
        "task_id": task.get("id"),
        "mode": mode,
        "iteration": iteration,
        "prompt_chars": len(prompt),
        "output_chars": len(provider_result.output),
        "latency_ms": provider_result.latency_ms,
        "tokens_in": provider_result.tokens_in,
        "tokens_out": provider_result.tokens_out,
        "rule_score": judges.rule_score,
    }
    if judges.llm_score is not None:
        record["llm_score"] = judges.llm_score
    if pricing is not None:
        cost = calculate_cost(provider_result.tokens_in, provider_result.tokens_out, pricing)
        if cost is not None:
            record["cost_usd"] = cost
    return record


def calculate_cost(tokens_in: Optional[int], tokens_out: Optional[int], pricing: PricingConfig) -> Optional[float]:
    if tokens_in is None and tokens_out is None:
        return None
    in_cost = (tokens_in or 0) / 1000 * pricing.input_per_1k
    out_cost = (tokens_out or 0) / 1000 * pricing.output_per_1k
    return round(in_cost + out_cost, 6)


def load_task(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def build_prompt(mode: str, task: dict, skill_root: Path, topics: Dict[str, dict]) -> str:
    if mode == "baseline":
        return format_task_prompt(task)
    if mode == "naive":
        skill_blob = load_skill_blob(skill_root)
        return f"{skill_blob}\n\n---\n{format_task_prompt(task)}"
    if mode == "progressive":
        topic_name, topic_meta = select_topic(task, topics)
        skill_md = (skill_root / "SKILL.md").read_text()
        reference_blocks = "\n".join(
            f"[reference: {ref}]\n{(skill_root / ref).read_text()}"
            for ref in topic_meta.get("references", [])
        )
        return (
            f"{skill_md}\n\n"
            f"[selected-topic: {topic_name}]\n"
            f"{reference_blocks}\n\n---\n"
            f"{format_task_prompt(task)}"
        ).strip()
    raise ValueError(f"Unknown mode '{mode}'")


def format_task_prompt(task: dict) -> str:
    return f"Goal: {task['goal']}\n\nInput:\n{task['input']}"


def load_skill_blob(skill_root: Path) -> str:
    parts: List[str] = []
    for path in sorted(skill_root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(skill_root)
            parts.append(f"[file: {rel}]\n{path.read_text()}")
    return "\n\n".join(parts)


def parse_skill_topics(skill_md_path: Path) -> Dict[str, dict]:
    topics: Dict[str, dict] = {}
    current_topic: Optional[str] = None

    for raw_line in skill_md_path.read_text().splitlines():
        line = raw_line.strip()
        if line.startswith("## Topic:"):
            current_topic = line.split(":", 1)[1].strip()
            topics[current_topic] = {"references": [], "cues": []}
            continue
        if not current_topic:
            continue
        if line.startswith("- reference:"):
            ref = line.split(":", 1)[1].strip()
            topics[current_topic].setdefault("references", []).append(ref)
        if line.startswith("- cues:"):
            cues = [token.strip() for token in line.split(":", 1)[1].split(",")]
            topics[current_topic].setdefault("cues", []).extend(filter(None, cues))
    return topics


def select_topic(task: dict, topics: Dict[str, dict]) -> tuple[str, dict]:
    if not topics:
        raise ValueError("No topics parsed from SKILL.md")
    task_text = " ".join([task.get("id", ""), task.get("goal", ""), task.get("input", "")]).lower()
    for topic, meta in topics.items():
        cues: Iterable[str] = meta.get("cues", [])
        if any(cue.lower() in task_text for cue in cues):
            return topic, meta
    # fallback: first topic defined
    default_topic = next(iter(topics.items()))
    return default_topic
