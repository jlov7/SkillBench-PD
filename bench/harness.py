from __future__ import annotations

import json
import re
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
    skill_root: Path = Path("skills/brand-voice")
    pricing: "PricingConfig | None" = None


@dataclass
class PricingConfig:
    input_per_1k: float = 0.0
    output_per_1k: float = 0.0


@dataclass
class SkillSection:
    title: str
    cues: List[str]
    references: List[str]
    body: str


@dataclass
class SkillDefinition:
    name: str
    description: str
    body: str
    sections: List[SkillSection]


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
        skill_root=Path(data.get("skill_root", "skills/brand-voice")),
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
    metadata, _ = parse_skill_markdown(skill_md)
    validate_skill_metadata(metadata, skill_root)


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


SKILL_NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def parse_skill_markdown(skill_md_path: Path) -> tuple[dict, str]:
    content = skill_md_path.read_text()
    if not content.startswith("---"):
        raise ValueError("SKILL.md must start with YAML frontmatter (---).")
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("SKILL.md frontmatter must be closed with ---.")
    metadata = yaml.safe_load(parts[1]) or {}
    if not isinstance(metadata, dict):
        raise ValueError("SKILL.md frontmatter must be a YAML mapping.")
    body = parts[2].lstrip("\n")
    return metadata, body


def validate_skill_metadata(metadata: dict, skill_root: Path) -> None:
    name = metadata.get("name")
    description = metadata.get("description")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("SKILL.md frontmatter must include a non-empty 'name'.")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("SKILL.md frontmatter must include a non-empty 'description'.")

    normalized = name.strip()
    if len(normalized) > 64:
        raise ValueError("SKILL.md 'name' must be 64 characters or fewer.")
    if not SKILL_NAME_RE.fullmatch(normalized):
        raise ValueError(
            "SKILL.md 'name' must be lowercase and use hyphens only (e.g., brand-voice)."
        )
    if skill_root.name != normalized:
        raise ValueError(
            f"Skill directory '{skill_root.name}' must match frontmatter name '{normalized}'."
        )
    if len(description.strip()) > 1024:
        raise ValueError("SKILL.md 'description' must be 1024 characters or fewer.")


def run_benchmark(config: BenchmarkConfig, provider: Optional[BaseProvider] = None) -> List[Dict]:
    results: List[Dict] = []
    provider = provider or ProviderFactory.create(config.provider, config.model)
    skill_root = config.skill_root
    skill = load_skill_definition(skill_root)

    for task_path in config.tasks:
        task = load_task(Path(task_path))
        for mode in config.modes:
            for iteration in range(config.repetitions):
                prompt = build_prompt(
                    mode=mode,
                    task=task,
                    skill_root=skill_root,
                    skill=skill,
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


def build_prompt(mode: str, task: dict, skill_root: Path, skill: SkillDefinition) -> str:
    if mode == "baseline":
        return format_task_prompt(task)
    if mode == "naive":
        skill_blob = load_skill_blob(skill_root)
        return f"{skill_blob}\n\n---\n{format_task_prompt(task)}"
    if mode == "progressive":
        section = select_section(task, skill.sections)
        skill_md = (skill_root / "SKILL.md").read_text().strip()
        reference_blocks = "\n".join(
            f"[reference: {ref}]\n{(skill_root / ref).read_text()}"
            for ref in section.references
        )
        parts = [skill_md, f"[selected-section: {section.title}]"]
        if reference_blocks:
            parts.append(reference_blocks)
        parts.append(f"---\n{format_task_prompt(task)}")
        return "\n\n".join(part for part in parts if part).strip()
    raise ValueError(f"Unknown mode '{mode}'")


def format_task_prompt(task: dict) -> str:
    return f"Goal: {task['goal']}\n\nInput:\n{task['input']}"


def load_skill_blob(skill_root: Path) -> str:
    parts: List[str] = []
    for path in sorted(skill_root.rglob("*")):
        if path.is_file() and not path.name.startswith(".") and "__pycache__" not in path.parts:
            rel = path.relative_to(skill_root)
            parts.append(f"[file: {rel}]\n{path.read_text()}")
    return "\n\n".join(parts)


KEYWORDS_RE = re.compile(r"(?:\*\*|__)?keywords?(?:\*\*|__)?\s*:\s*(.+)", re.IGNORECASE)
PATH_TOKEN_RE = re.compile(r"(?<![\w/.-])([\w./-]+\.[A-Za-z0-9]+)")


def load_skill_definition(skill_root: Path) -> SkillDefinition:
    skill_md = skill_root / "SKILL.md"
    metadata, body = parse_skill_markdown(skill_md)
    name = str(metadata.get("name", "")).strip()
    description = str(metadata.get("description", "")).strip()
    if not name or not description:
        raise ValueError("SKILL.md frontmatter must include name and description.")
    sections = parse_skill_sections(body, skill_root)
    return SkillDefinition(name=name, description=description, body=body, sections=sections)


def parse_skill_sections(body: str, skill_root: Path) -> List[SkillSection]:
    sections = _parse_sections_by_heading(body, "### ", skill_root)
    if not sections:
        sections = _parse_sections_by_heading(body, "## ", skill_root)
    if not sections:
        sections.append(_build_section("default", body.splitlines(), skill_root))
    return sections


def _parse_sections_by_heading(body: str, marker: str, skill_root: Path) -> List[SkillSection]:
    sections: List[SkillSection] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []

    for line in body.splitlines():
        if line.startswith(marker):
            if current_title is not None:
                sections.append(_build_section(current_title, current_lines, skill_root))
            current_title = line[len(marker):].strip()
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections.append(_build_section(current_title, current_lines, skill_root))
    return sections


def _build_section(title: str, lines: Iterable[str], skill_root: Path) -> SkillSection:
    body = "\n".join(lines).strip()
    cues = _extract_keywords(body)
    if not cues:
        cues = [token for token in re.split(r"[^a-zA-Z0-9]+", title) if token]
    references = _extract_references(body, skill_root)
    return SkillSection(title=title, cues=_dedupe(cues), references=references, body=body)


def _extract_keywords(text: str) -> List[str]:
    cues: List[str] = []
    for line in text.splitlines():
        match = KEYWORDS_RE.search(line)
        if not match:
            continue
        raw = match.group(1)
        for token in re.split(r"[;,]", raw):
            cleaned = token.strip()
            if cleaned:
                cues.append(cleaned)
    return cues


def _extract_references(text: str, skill_root: Path) -> List[str]:
    candidates = set()
    for match in re.findall(r"\\(([^)]+)\\)", text):
        candidates.add(match.strip())
    for match in PATH_TOKEN_RE.findall(text):
        candidates.add(match.strip())

    refs: List[str] = []
    seen: set[str] = set()
    root = skill_root.resolve()

    for candidate in candidates:
        cleaned = candidate.strip().strip("`")
        if not cleaned or "://" in cleaned or cleaned.startswith("mailto:"):
            continue
        cleaned = cleaned.split("#", 1)[0].split("?", 1)[0].strip()
        if not cleaned:
            continue
        path = Path(cleaned)
        if path.is_absolute():
            continue
        resolved = (skill_root / path).resolve()
        if not resolved.exists() or not resolved.is_file():
            continue
        if not _is_within_root(resolved, root):
            continue
        rel = path.as_posix()
        if rel not in seen:
            seen.add(rel)
            refs.append(rel)
    return refs


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _dedupe(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    output: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def select_section(task: dict, sections: List[SkillSection]) -> SkillSection:
    if not sections:
        raise ValueError("No sections parsed from SKILL.md")
    task_text = " ".join([task.get("id", ""), task.get("goal", ""), task.get("input", "")]).lower()
    for section in sections:
        if any(cue.lower() in task_text for cue in section.cues):
            return section
    return sections[0]
