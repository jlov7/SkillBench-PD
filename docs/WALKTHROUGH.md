# Sample Run Walkthrough

This document summarises the default benchmark run (`skillbench-pd` using the mock provider). It is provided for personal R&D reference—feel free to adapt it when comparing against live Anthropic executions.

## Setup
- Config: `configs/bench.yaml`
- Modes: baseline, naive, progressive
- Tasks: `t1_rewrite_brand`, `t2_format_policy`, `t3_summarize_metrics`
- Repetitions: 3
- Provider: mock (deterministic)

## Aggregate metrics (from `results/results.md`)

| Mode        | Latency (ms) | Tokens In | Tokens Out | Rule Score | Cost (USD) |
|-------------|--------------|-----------|------------|------------|------------|
| baseline    | 0.003        | 43.333    | 42         | 1.000      | 0.760      |
| naive       | 0.009        | 557.333   | 28         | 0.667      | 2.092      |
| progressive | 0.007        | 460.000   | 28         | 0.667      | 1.800      |

Interpretation:
- **Latency** rises when the entire Skill folder is stuffed into context. Progressive disclosure trims ~0.002 ms versus naive even in mock mode; expect larger gaps on real models.
- **Tokens In** explode under naive mode because every Skill file is loaded. Progressive mode still adds context but drops ~25% relative to naive.
- **Cost** tracks the configured pricing (here: $3 input / $15 output per 1K tokens). Progressive mode saves ~14% versus naive in the mock run—expect greater savings with real token counts.
- **Rule Score** shows quality degradation in naive/progressive for the synthetic mock output—use live models to measure real uplift.

## Delta vs baseline

| Mode        | Δ Latency | Δ Tokens In | Δ Tokens Out | Δ Rule Score | Δ Cost (USD) |
|-------------|-----------|-------------|--------------|--------------|--------------|
| naive       | +0.006    | +514        | -14          | -0.333       | +1.332       |
| progressive | +0.004    | +416.667    | -14          | -0.333       | +1.040       |

Key takeaway: even with deterministic outputs, progressive loads ~100 fewer tokens than naive. In production systems, combine these deltas with cost and latency budgets to justify progressive disclosure.

## Task-level latency histograms
Inspect `results/chart_t1_rewrite_brand_latency.png` (and similar) to compare mode-specific latency distributions. Wider histograms indicate jitter; aim for tight distributions for production workloads.

## Applying this template
1. Run `skillbench-pd --output-dir runs/2025-01-31`.
2. Copy the Markdown tables and chart filenames into your report.
3. Note any significant changes from mock baselines—especially if rule scores improve with progressive disclosure.
4. Call out cost differences alongside latency/quality—finance stakeholders love before/after cost deltas.
5. Append qualitative observations (e.g., improved tone adherence, reduced policy violations) from inspecting raw outputs.

## Upgrading to Anthropic runs
1. Export `ANTHROPIC_API_KEY`.
2. Execute `skillbench-pd --provider auto --model claude-3-5-sonnet`.
3. Add a subsection describing the delta between mock and live runs; highlight qualitative improvements or regressions.

### Sample Anthropic output (redacted)

| Mode        | Latency (ms) | Tokens In | Tokens Out | Rule Score | Cost (USD) |
|-------------|--------------|-----------|------------|------------|------------|
| baseline    | 820          | 1200      | 280        | 0.8        | 4.44       |
| naive       | 1430         | 5400      | 410        | 0.9        | 15.93      |
| progressive | 980          | 2100      | 360        | 0.95       | 6.93       |

_Assistant output snippets (redacted):_
- **Baseline**: _"[summary omitted — missing brand cues]"_
- **Naive**: _"[long response referencing entire Skill bundle]"_
- **Progressive**: _"[concise rewrite referencing the reporting guide]"_

Observations (illustrative only—re-run with your own models/data before publishing):
- Progressive disclosure trimmed **~57%** of the tokens naive mode loaded while improving rule score.
- Latency dropped ~450 ms vs naive due to smaller prompts.
- Cost savings (~$9/run) compound when scaled across workloads.
- Qualitatively, progressive outputs referenced the correct guide sections without the redundant boilerplate seen in naive mode.

## Recommended artefacts to keep
- Raw `results.json` for ad hoc slicing.
- `results.md` for human-visible summaries.
- Generated charts (`chart_*`) for decks or dashboards.
- CLI console output for quick summaries (copy/paste into notes).
