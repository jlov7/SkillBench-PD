from pathlib import Path

import pytest

from bench.harness import BenchmarkConfig, PricingConfig, validate_config


def test_validate_config_rejects_unknown_mode():
    config = BenchmarkConfig(
        modes=["baseline", "unknown"],
        tasks=["tasks/t1_rewrite_brand.json"],
        repetitions=1,
        provider="mock",
        model="mock-model",
    )
    with pytest.raises(ValueError) as exc:
        validate_config(config, base_dir=Path("."))
    assert "Unsupported modes" in str(exc.value)


def test_validate_config_checks_task_exists(tmp_path):
    config = BenchmarkConfig(
        modes=["baseline"],
        tasks=[str(tmp_path / "missing.json")],
        repetitions=1,
        provider="mock",
        model="mock-model",
    )
    with pytest.raises(FileNotFoundError):
        validate_config(config)


def test_validate_config_accepts_valid_setup(tmp_path):
    skill_root = tmp_path / "skill"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: skill\ndescription: Synthetic skill for validation tests.\n---\n\n# Skill\n"
    )
    task_file = tmp_path / "task.json"
    task_file.write_text("{}")
    config = BenchmarkConfig(
        modes=["baseline"],
        tasks=[str(task_file)],
        repetitions=1,
        provider="mock",
        model="mock-model",
        skill_root=skill_root,
    )
    validate_config(config)


def test_validate_config_rejects_negative_pricing(tmp_path):
    task_file = tmp_path / "task.json"
    task_file.write_text("{}")
    skill_root = tmp_path / "skill"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: skill\ndescription: Synthetic skill for validation tests.\n---\n\n# Skill\n"
    )
    config = BenchmarkConfig(
        modes=["baseline"],
        tasks=[str(task_file)],
        repetitions=1,
        provider="mock",
        model="mock-model",
        skill_root=skill_root,
        pricing=PricingConfig(input_per_1k=-1.0),
    )
    with pytest.raises(ValueError):
        validate_config(config)
