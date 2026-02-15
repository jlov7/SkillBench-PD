# SkillBench-PD v1

SkillBench-PD benchmarks three prompting strategies for Agent Skills workflows:
- `baseline`: task instructions only.
- `naive`: task plus the entire Skill folder.
- `progressive`: task plus `SKILL.md` and only relevant referenced files.

It generates shareable static reports (`results/html/index.html`) plus CSV and Markdown outputs for deeper analysis.

## v1 Highlights
- CLI-first benchmark runner (`skillbench-pd`) with output and provider overrides.
- Static HTML report with:
  - onboarding guidance,
  - empty-state and missing-baseline failure messaging,
  - aggregate/delta/task tables,
  - copied chart assets for portable sharing.
- Rule-based scoring by default; optional LLM judge.
- Quality gates in CI: lint (`ruff`), typecheck (`pyright`), tests (`pytest`), package build.

## Repository Layout
- `bench/`: benchmark harness, providers, judges, reporting.
- `skills/`: benchmark skill fixtures (`SKILL.md` + references).
- `tasks/`: benchmark task fixtures.
- `configs/bench.yaml`: default run configuration.
- `docs/HELP.md`: user-facing report interpretation and troubleshooting.
- `.github/workflows/ci.yml`: release quality pipeline.

## Local Setup
```bash
uv venv .venv
uv sync --extra dev
```

## Run
```bash
# default config
uv run skillbench-pd

# fast smoke run
uv run skillbench-pd \
  --modes baseline progressive \
  --repetitions 1 \
  --tasks tasks/t1_rewrite_brand.json \
  --open-report
```

Output files are written to `results/` by default:
- `results.csv`
- `results.md`
- `results.json`
- `aggregates_by_mode.csv`
- `deltas_by_mode.csv`
- `aggregates_by_task.csv`
- `chart_*.png`
- `html/index.html` and `html/assets/*`

## Test / Lint / Typecheck / Build
```bash
uv run pytest -q
uv run ruff check .
uv run pyright
uv run python -m build
```

## Environment Variables
| Variable | Required | Description |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | No | Enables Anthropic provider and optional `--judge llm`. |

If `ANTHROPIC_API_KEY` is not set, `--provider auto` falls back to `mock`.

## Deploy (Static Report Sharing)
The generated report is static and can be hosted anywhere.

### Recommended: Vercel
Vercel gives fast static hosting, preview links, and easy sharing.

1. Run benchmark locally: `uv run skillbench-pd`.
2. In Vercel, create/import a project from this repo.
3. Configure output directory to `results/html`.
4. Deploy to get a public report URL.

### Alternative: GitHub Pages
1. Commit/push generated `results/html` artifacts to a publish branch or folder.
2. In repository settings, enable GitHub Pages for that branch/folder.
3. Share the generated Pages URL.

## Help
See `docs/HELP.md` for:
- how to read aggregate and delta tables,
- how to handle empty reports and missing baseline mode,
- how to share reports safely.

## Security Notes
- Do not commit secrets (`ANTHROPIC_API_KEY`, `.env` files).
- Benchmark tasks in this repo are synthetic; avoid adding sensitive production data.
- Provider output is rendered as escaped text in reports.

## License
Apache-2.0 (`LICENSE`).
