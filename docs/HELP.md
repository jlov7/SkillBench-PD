# SkillBench-PD Help

## What the Modes Mean
- `baseline`: no Skill context, task only.
- `naive`: entire Skill folder is injected.
- `progressive`: `SKILL.md` + selected references for the matched section.

## Reading the HTML Report
1. Start with **Overview** for row count, tasks, modes, and baseline latency.
2. Check **Aggregated metrics** to compare average latency, tokens, rule score, and cost.
3. Check **Delta vs baseline**:
   - Positive values mean increases versus baseline.
   - Negative values mean reductions versus baseline.
4. Use **Per-task breakdown** to identify localized regressions.
5. Use **Charts** for fast visual comparison.

## Regression Reports
Every run also generates:
- `regression_report.json` (machine-readable gate output)
- `regression_report.md` (human-readable summary)

Regression checks compare each non-baseline mode against baseline per task/model/judge, with:
- bootstrap confidence intervals for deltas,
- permutation-test p-values,
- effect size (Cohen's d).

A regression is flagged only when threshold + significance + effect-size conditions are all met.

## Key Failure States
### Empty report
If no rows were produced, the report shows:
- "No benchmark results were recorded"
- a starter command to run a minimal benchmark.

### Missing baseline mode
If baseline was excluded, delta sections show:
- "Baseline mode is required to compute deltas."

Run again including baseline:
```bash
uv run skillbench-pd --modes baseline progressive --repetitions 1
```

### Gate failed (`exit code 2`)
If `--fail-on-regression` is enabled and regressions are flagged, the CLI exits non-zero.

Common fixes:
1. Increase repetitions for better statistical power.
2. Adjust thresholds for your workload and SLOs.
3. Inspect `regression_report.md` for flagged metrics and tasks.

## Shareability
- Best-practice default: publish `results/html/` to Vercel.
- Alternative: publish `results/html/` via GitHub Pages.
- Keep chart assets together with `index.html` under `html/assets/`.

## Accessibility Notes
- Report supports keyboard navigation with a skip link and focus styles.
- Navigation links jump to primary report sections.
- Tables include captions and semantic headers.

## Troubleshooting
### `--provider auto` used mock unexpectedly
Set `ANTHROPIC_API_KEY` in your shell and rerun.

### Lint/typecheck/build commands fail locally
Re-sync dev dependencies:
```bash
uv sync --extra dev
```

### Checkpoint resume confusion
If you need a clean orchestration run:
```bash
uv run skillbench-pd --orchestrate --checkpoint-path results/checkpoint.jsonl --no-resume
```
