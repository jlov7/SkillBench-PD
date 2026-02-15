# SkillBench-PD v1

[![CI](https://github.com/jlov7/SkillBench-PD/actions/workflows/ci.yml/badge.svg)](https://github.com/jlov7/SkillBench-PD/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python >=3.10](https://img.shields.io/badge/python-3.10%2B-0A7BBB.svg)](pyproject.toml)
[![Open in Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/jlov7/SkillBench-PD)
[![Live Demo Hub](https://img.shields.io/badge/demo-live-00C7B7.svg)](https://showcase-murex-kappa.vercel.app)

SkillBench-PD benchmarks three prompting strategies for Agent Skills workflows:
- `baseline`: task instructions only.
- `naive`: task plus the entire Skill folder.
- `progressive`: task plus `SKILL.md` and only relevant referenced files.

It generates shareable static reports (`results/html/index.html`) plus CSV and Markdown outputs for deeper analysis.

## Disclaimer
This repository is a personal, independent research and passion project.
It is not an official product, position, or statement of my employer.
All views, conclusions, and implementation decisions here are solely my own and were produced in a personal capacity.

## v1 Highlights
- CLI-first benchmark runner (`skillbench-pd`) with output and provider overrides.
- Public demo hub for non-technical, technical, and evidence-first walkthroughs.
- Static HTML report with:
  - onboarding guidance,
  - empty-state and missing-baseline failure messaging,
  - aggregate/delta/task tables,
  - copied chart assets for portable sharing.
- Rule-based scoring by default; optional LLM judge.
- Quality gates in CI: lint (`ruff`), typecheck (`pyright`), tests (`pytest`), package build.
- Advanced orchestration mode for matrix experiments with:
  - parallel workers,
  - retries and global QPS rate limiting,
  - checkpoint/resume support,
  - statistical regression gate (CI + local fail-fast).

## Repository Layout
- `bench/`: benchmark harness, providers, judges, reporting.
- `skills/`: benchmark skill fixtures (`SKILL.md` + references).
- `tasks/`: benchmark task fixtures.
- `configs/bench.yaml`: default run configuration.
- `showcase/`: static demo hub (Vercel-ready) for shareability and live storytelling.
- `docs/SHOWCASE.md`: demo hub user journeys, refresh flow, and deploy runbook.
- `docs/DEMO_PLAYBOOK.md`: non-technical and technical demo script.
- `docs/ARCHITECTURE.md`: technical system overview.
- `docs/TRY_IT.md`: fastest paths for trying locally/Codespaces.
- `docs/HELP.md`: user-facing report interpretation and troubleshooting.
- `.github/workflows/ci.yml`: release quality pipeline.

## Project Standards
- This repository tracks source, tests, and sample fixtures only.
- Generated run outputs in `results/` are intentionally git-ignored.
- Internal session/history artifacts are not tracked.
- See `CONTRIBUTING.md` for contribution workflow.
- See `SECURITY.md` for responsible disclosure guidance.

## 60-Second Demo
```bash
uv venv .venv
uv sync --extra dev
uv run skillbench-pd --modes baseline progressive --repetitions 1 --open-report
```

This produces an immediately shareable HTML report at `results/html/index.html`.

## Live Demo Hub
- Public URL: <https://showcase-murex-kappa.vercel.app>
- Audience views:
  - `Demo Hub` for orientation and entry points.
  - `Why It Matters` for non-technical stakeholders.
  - `How It Works` for engineering deep dives.
  - `Evidence` for data-backed proof and quick start.
- Local preview:
```bash
uv run python scripts/build_showcase_data.py
uv run python -m http.server 8123 -d showcase
```
- If a scoped alias returns `401`, share the public project alias above.

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
- `regression_report.json`
- `regression_report.md`

For reproducible sample outputs committed in-repo, see `sample_results/`.

## Next-Level Experiment Orchestration
Run a matrix experiment over multiple models/judges with checkpoint/resume:

```bash
uv run skillbench-pd \
  --orchestrate \
  --modes baseline naive progressive \
  --tasks tasks/t1_rewrite_brand.json tasks/t2_format_policy.json \
  --repetitions 3 \
  --matrix-models mock-a mock-b \
  --matrix-judges rule \
  --max-workers 4 \
  --retry-attempts 2 \
  --rate-limit-qps 5 \
  --checkpoint-path results/checkpoint.jsonl \
  --output-dir results
```

Resume from the same checkpoint (default behavior when checkpoint exists):
```bash
uv run skillbench-pd --orchestrate --checkpoint-path results/checkpoint.jsonl
```

Force a fresh run:
```bash
uv run skillbench-pd --orchestrate --checkpoint-path results/checkpoint.jsonl --no-resume
```

## Regression Gate (Release Decision)
The CLI writes a statistical regression report for every run:
- JSON: `regression_report.json`
- Markdown: `regression_report.md`

Enable fail-fast gate:
```bash
uv run skillbench-pd \
  --orchestrate \
  --modes baseline progressive \
  --tasks tasks/t1_rewrite_brand.json \
  --repetitions 3 \
  --fail-on-regression \
  --latency-regression-pct 20 \
  --cost-regression-pct 100 \
  --rule-score-drop 0.2 \
  --regression-alpha 0.1 \
  --min-effect-size 0.1
```

When regressions are flagged, the process exits with code `2` (useful for CI).

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
Both outputs are static and can be hosted anywhere:
- benchmark report: `results/html/`
- demo hub: `showcase/`

### Recommended: Vercel
Vercel gives fast static hosting, preview links, and easy sharing.

1. Build/refresh demo data: `uv run python scripts/build_showcase_data.py`.
2. Deploy demo hub: `vercel deploy showcase --prod`.
3. (Optional) Publish benchmark report as a second static project from `results/html`.
4. Share the public Vercel URL.

### Alternative: GitHub Pages
1. Deploy `showcase/` or generated `results/html/` from a publish branch/folder.
2. In repository settings, enable GitHub Pages for that branch/folder.
3. Share the generated Pages URL.

## Help
See `docs/HELP.md` for:
- how to read aggregate and delta tables,
- how to handle empty reports and missing baseline mode,
- how to share reports safely.

For stakeholder demos and talk tracks, see `docs/DEMO_PLAYBOOK.md`.
For fastest onboarding paths, see `docs/TRY_IT.md`.

## Security Notes
- Do not commit secrets (`ANTHROPIC_API_KEY`, `.env` files).
- Benchmark tasks in this repo are synthetic; avoid adding sensitive production data.
- Provider output is rendered as escaped text in reports.

## License
Apache-2.0 (`LICENSE`).
