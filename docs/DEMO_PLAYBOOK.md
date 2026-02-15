# Demo Playbook

This playbook helps you present SkillBench-PD clearly to both non-technical and technical audiences.

## Demo Goals
- Show why progressive disclosure matters.
- Show that results are reproducible and measurable.
- Show that release decisions can be gated with statistical checks.

## Audience-Specific Positioning
### Non-technical framing
- Problem: dumping all context into prompts increases latency/cost and can reduce consistency.
- Solution: progressive disclosure loads only relevant Skill context.
- Outcome: cleaner tradeoff between speed, cost, and quality, with evidence.

### Technical framing
- Controlled benchmark harness across modes/tasks/models/judges.
- Matrix orchestration with retry, QPS throttling, checkpoint/resume.
- Regression gate with bootstrap CI, permutation p-values, and effect size.

## Live Demo Script (5-7 minutes)
1. Open the live demo hub: <https://showcase-murex-kappa.vercel.app>.
2. Explain the three modes (`baseline`, `naive`, `progressive`) from `Demo Hub` and `Why It Matters`.
3. Move to `Evidence` and show aggregated metrics and charts.
4. Run a quick benchmark:
```bash
uv run skillbench-pd --modes baseline naive progressive --repetitions 1 --open-report
```
5. In the generated HTML report, show:
- Overview cards.
- Aggregated metrics.
- Delta vs baseline.
- Per-task breakdown.
6. Run orchestration + regression gate:
```bash
uv run skillbench-pd \
  --orchestrate \
  --modes baseline progressive \
  --tasks tasks/t1_rewrite_brand.json \
  --repetitions 3 \
  --matrix-models mock-a mock-b \
  --matrix-judges rule \
  --checkpoint-path results/checkpoint.jsonl \
  --fail-on-regression \
  --latency-regression-pct 20 \
  --cost-regression-pct 100 \
  --rule-score-drop 0.2
```
7. Show generated gate outputs:
- `results/regression_report.json`
- `results/regression_report.md`

## Technical Deep-Dive Narrative
1. `bench/harness.py`: prompt construction + scoring records.
2. `bench/experiment.py`: matrix execution engine.
3. `bench/regression.py`: statistical decision layer.
4. `bench/report.py`: human-readable HTML/Markdown outputs.
5. `.github/workflows/ci.yml`: release quality and regression checks.

## Presentation Assets
- Use `sample_results/` when offline or when you need deterministic slides.
- Keep one screenshot each for:
  - aggregate table,
  - delta table,
  - regression summary.

## Demo Quality Checklist
- Run all quality gates before presenting.
- Use fresh output directory for each demo run.
- Keep `ANTHROPIC_API_KEY` unset unless you intentionally demo live models.
- Do not include sensitive data in tasks or Skill references.
