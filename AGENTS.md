# AGENTS

## Working Agreements
- Keep changes small and reviewable; commit frequently with conventional commit messages.
- Use `uv` for Python setup and execution.
- Prefer minimal-risk changes; avoid refactors unless required for correctness or v1 UX.
- Keep generated artifacts out of commits (results, charts, caches).

## Commands
Setup:
- `uv venv .venv`
- `uv sync --extra dev`

Run:
- `uv run skillbench-pd`
- `uv run skillbench-pd --open-report`
- `uv run skillbench-pd --orchestrate --checkpoint-path results/checkpoint.jsonl`
- `uv run skillbench-pd --orchestrate --fail-on-regression`

Test:
- `uv run pytest -q`

Quality Gates (v1 target):
- Lint: `uv run ruff check .`
- Typecheck: `uv run pyright`
- Build: `uv run python -m build`

## Quality Bar
- All tests pass.
- Lint/typecheck/build succeed.
- CI is green.
- README includes setup/run/test/deploy and env vars.
- Accessibility and UX basics are addressed in the HTML report.
- `results/html/index.html` is ready to deploy to static hosting.
