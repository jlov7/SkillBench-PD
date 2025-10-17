# Configuration Reference

SkillBench-PD reads YAML files such as `configs/bench.yaml`. Each field is validated before runs begin so errors surface early.

## Top-level keys

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `modes` | list[str] | Yes | Prompt construction modes to run. Allowed values: `baseline`, `naive`, `progressive`. |
| `tasks` | list[str] | Yes | Paths (relative to the config file or repo root) to task JSON files. |
| `repetitions` | int | Yes | Number of times each task/mode pair is executed. Must be ≥ 1. |
| `provider` | str | Yes | Model provider. `mock` or `anthropic`. |
| `model` | str | Yes | Model identifier; used for logging and Anthropic calls. |
| `judge` | str | No | Quality evaluation path. `rule` (default) or `llm`. |
| `output_dir` | str | No | Directory (relative or absolute) for CSV/Markdown/plots. Defaults to `results`. |
| `skill_root` | str | No | Root folder of the Skill to load; must contain `SKILL.md`. Defaults to `skills/brand_voice`. |
| `pricing` | mapping | No | Optional cost settings with `input_per_1k` / `output_per_1k` (USD per 1K tokens). |

## Relative path resolution
- Paths are resolved relative to the config file first. If not found, parent directories (toward the repo root) are checked.
- Absolute paths are respected as-is.

## Validation errors
When loading a config, the harness raises:
- `ValueError` for unsupported modes, invalid judge values, or repetitions `< 1`.
- `ValueError` if `pricing` contains negative numbers.
- `FileNotFoundError` if task files or the Skill root / `SKILL.md` are missing.

## Extending configs
You can add custom keys to your YAML for downstream tooling. The loader ignores unknown fields but will not map them to the `BenchmarkConfig`. For more advanced scenarios (e.g., weighting tasks), adjust `BenchmarkConfig` and validation logic accordingly.

## Tips
- Keep task paths short and descriptive (`tasks/t4_security_review.json`).
- Maintain per-Skill subfolders (e.g., `skills/support_updates/`) and point `skill_root` to them to benchmark multiple Skills.
- Version your configs (e.g., `configs/bench_v2.yaml`) when running experiments to keep results reproducible.
- Use CLI overrides (`--pricing-input`, `--pricing-output`, `--no-pricing`) for quick experiments without editing YAML.
