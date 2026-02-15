# AGENTS

## Working Agreements
- Keep changes small and reviewable; commit frequently with conventional commit messages.
- Use `uv` for Python setup and execution.
- Prefer minimal-risk changes; avoid refactors unless required for correctness or v1 UX.
- Keep generated artifacts out of commits (results, charts, caches).

## Commands
Setup:
- `uv venv .venv`
- `uv pip install -e '.[dev]'`

Run:
- `skillbench-pd`
- `python examples/demo_run.py`

Test:
- `uv run pytest -q`

Quality Gates (v1 target):
- Lint: `uv run ruff check .`
- Typecheck: `uv run pyright`
- Build: `python -m build`

## Quality Bar
- All tests pass.
- Lint/typecheck/build succeed.
- CI is green.
- README includes setup/run/test/deploy and env vars.
- Accessibility and UX basics are addressed in the HTML report.
