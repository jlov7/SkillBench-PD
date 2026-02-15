# Contributing

Thanks for contributing to SkillBench-PD.

## Development Setup
```bash
uv venv .venv
uv sync --extra dev
```

## Quality Gates
Run all gates before opening a PR:
```bash
uv run pytest -q
uv run ruff check .
uv run pyright
uv run python -m build
```

## Pull Request Guidelines
- Keep changes scoped and reviewable.
- Add or update tests for behavior changes.
- Update docs when flags, config behavior, or outputs change.
- Do not commit generated run outputs (`results/`), local caches, or secrets.

## Commit Style
- Use clear, imperative commit messages.
- Prefer one logical change per commit.

## Reporting Issues
- Include reproduction steps and expected vs actual behavior.
- For benchmark behavior, include command used and relevant output artifact paths.
