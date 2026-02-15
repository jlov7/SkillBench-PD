# Try SkillBench-PD

## Instant Demo (No setup)
- Open live demo hub: <https://showcase-jlov7s-projects.vercel.app>
- Navigate:
  - `Why It Matters` for stakeholder pitch copy.
  - `How It Works` for architecture summary.
  - `Evidence` for sample benchmark outputs and repro command.

## Fastest Path (No local setup)
- Open in browser: [Codespaces](https://codespaces.new/jlov7/SkillBench-PD)
- In the Codespaces terminal run:

```bash
uv sync --extra dev
uv run skillbench-pd --modes baseline progressive --repetitions 1 --open-report
```

## Local Path (60 seconds)
```bash
uv venv .venv
uv sync --extra dev
uv run skillbench-pd --modes baseline progressive --repetitions 1 --open-report
```

## What You’ll See
- `results/html/index.html`: shareable report with onboarding and deltas.
- `results/regression_report.md`: pass/fail regression summary.

## Build Demo Hub Locally
```bash
uv run python scripts/build_showcase_data.py
uv run python -m http.server 8123 -d showcase
```

Then open <http://localhost:8123>.

## Deeper Evaluation
Run a matrix benchmark with checkpointing and regression gating:

```bash
uv run skillbench-pd \
  --orchestrate \
  --modes baseline naive progressive \
  --tasks tasks/t1_rewrite_brand.json tasks/t2_format_policy.json \
  --repetitions 3 \
  --matrix-models mock-model \
  --matrix-judges rule \
  --checkpoint-path results/checkpoint.jsonl \
  --fail-on-regression
```

## Interpreting Success
- Progressive mode should generally reduce token load vs naive.
- Regression gate should remain PASS for expected-safe changes.
- If it fails, inspect `results/regression_report.md` and tune thresholds deliberately.
