# SkillBench-PD — Progressive Disclosure benchmark for Claude Skills

SkillBench-PD is a small, non-commercial benchmark that quantifies how **progressive disclosure** inside Claude Skills affects latency, context load, and quality. It runs tiny, synthetic tasks in three prompting modes:
- `baseline` — task instructions only.
- `naive` — task plus the entire Skill folder dumped into context.
- `progressive` — task plus `SKILL.md` and only the files referenced for the relevant section.

The harness records latency, token usage (when exposed by the provider), output length, and rule-based quality scores. Optional LLM judging can be enabled when you supply an Anthropic API key.

## Why progressive disclosure matters
Claude **Skills** dynamically load the minimal set of resources needed for a given request, which reduces context bloat and mitigates security risks associated with indiscriminate file ingestion. SkillBench-PD simulates that behaviour so practitioners can compare prompting strategies before investing in full automation.\
References: [Anthropic announcement][1], [engineering deep-dive][4], [Claude Code Skills guide][3], [Help Center guidance][6], [OpenTelemetry GenAI semantics][2], [anthropics/skills examples][5], [Simon Willison analysis][7].

## Repository layout
- `bench/` — provider abstractions, harness, judges, and reporting helpers.
- `skills/` — synthetic Skill content (`SKILL.md` plus referenced resources).
- `tasks/` — JSON tasks used in the benchmark.
- `configs/bench.yaml` — modes, tasks, repetitions, and provider configuration.
- `examples/demo_run.py` — runnable demo tying the pieces together.
- `tests/` — pytest coverage for prompt construction and rule-based judging.
- `results.csv` / `results.md` — generated artefacts summarising each run.

## At a glance
- Benchmark three prompting strategies—baseline, naive dump, progressive disclosure—on synthetic Claude Skill tasks.
- Measures latency, optional tokens, and rule-based quality; supports Anthropic runs when a key is present.
- Generates CSV + Markdown reports with aggregate tables, percentile latency, cost deltas, and per-task latency histograms.
- Ships with a CLI (`skillbench-pd`) so you can script experiments or drop into notebooks.
- Validates configs up front—catching missing tasks, unsupported modes, or absent Skill files before execution.
- Computes estimated cost when you supply per-1K token pricing.

## For non-technical readers
SkillBench-PD is a research playground. It feeds small, safe scenarios (rewriting copy, formatting policies, summarising metrics) to a simulated Claude Skill. We compare three ways of loading instructions: nothing extra, everything dumped at once, and the progressive style that Skills use in production. The outputs show how context size and quality shift when you load only the files referenced by `SKILL.md`. You can skim the Markdown report without writing code; the tables and charts highlight whether progressive disclosure helps.

## Quickstart
```bash
python -m pip install -e .
pytest -q
python examples/demo_run.py
# or invoke the packaged CLI
skillbench-pd --help
```

| Scenario | Command | Output |
| --- | --- | --- |
| See everything with defaults | `skillbench-pd` | CSV/Markdown/plots in `results/` + console summary |
| Minimal smoke test | `skillbench-pd --modes baseline progressive --repetitions 1` | Quick comparison of progressive vs baseline |
| Anthropic run (with key) | `skillbench-pd --provider auto --model claude-3-5-sonnet` | Uses live model if `ANTHROPIC_API_KEY` is set |

The demo now auto-detects `ANTHROPIC_API_KEY`—if present, it overrides the config to run with the Anthropic provider. You can also supply overrides manually:

```bash
python examples/demo_run.py --provider anthropic --model claude-3-5-sonnet
# or choose automatically based on env var
python examples/demo_run.py --provider auto
```

The demo loads `configs/bench.yaml`, runs the configured repetitions, and writes `results.csv` and `results.md` by default. Inspect the Markdown report for token and latency deltas alongside quality metrics.

## Command-line interface
`skillbench-pd` installs a CLI so you can script experiments without touching the demo helper.

```bash
# run default config (mock provider, full task suite)
skillbench-pd

# compare progressive vs baseline on one task with a single repetition
skillbench-pd \
  --modes baseline progressive \
  --tasks tasks/t1_rewrite_brand.json \
  --repetitions 1 \
  --output-dir tmp/results

# delegate provider choice to environment (mock fallback if no key)
skillbench-pd --provider auto --model claude-3-5-sonnet

# include additional percentile latencies in the console summary
skillbench-pd --percentiles 50 90 99
```

Key flags:
- `--tasks`, `--modes`, `--repetitions` scope the benchmark run.
- `--provider` accepts `mock`, `anthropic`, or `auto` (detects `ANTHROPIC_API_KEY`).
- `--judge llm` flips on the optional LLM-as-judge path.
- `--output-dir` / `--results-json` control where artefacts land.
- `--percentiles` customises which latency percentiles are shown in the console summary (default `50 95`).

## Included synthetic tasks
- `t1_rewrite_brand` — rewrite hype-heavy marketing copy to match the brand voice guidelines.
- `t2_format_policy` — convert policy snippets into sentence-case headings with bullet points.
- `t3_summarize_metrics` — turn raw quarterly metrics into a headline plus three analytical bullets using the reporting style reference.

## Provider configuration
- **Mock (default)** — deterministic echo that simulates latency; returns `None` for token counts.
- **Anthropic** — set `provider: "anthropic"` in `configs/bench.yaml` and export `ANTHROPIC_API_KEY`. The harness handles missing keys by falling back to mock behaviour.
- **Pricing** — optionally set `pricing.input_per_1k` / `pricing.output_per_1k` in the config to estimate USD cost per run.

You can also invoke the harness programmatically:
```python
from bench.harness import run_benchmark, load_config

cfg = load_config("configs/bench.yaml")
results = run_benchmark(cfg)
```

## Reports
`bench/report.py` aggregates the collected metrics, emits a CSV, and builds a Markdown summary with small bar charts (matplotlib) comparing latency, tokens, and scores across modes. It also calculates per-mode and per-task deltas relative to the baseline to highlight how naive and progressive strategies diverge. Both the CLI and the demo script call it automatically, and the CLI echoes the aggregate tables to stdout for quick inspection.

### Interpreting the Markdown report
- **Aggregated metrics** — average latency/tokens/quality by mode across the full run.
- **Delta tables** — how each non-baseline mode differs from baseline overall and per task (positive numbers indicate increases).
- **Charts** — compact bar plots for latency and rule-based quality, plus per-task latency histograms to spot jitter.
- **Raw record count** — sanity check for repetitions × tasks × modes.

Pair the CSV with a notebook or BI tool if you need further analysis (e.g. percentile latency, per-mode regressions).
Additional CSV outputs:
- `aggregates_by_mode.csv` — per-mode averages (latency, percentiles, tokens, cost, quality).
- `deltas_by_mode.csv` — delta vs baseline for each metric.
- `aggregates_by_task.csv` — task/mode aggregates, useful for slicing in spreadsheets.

## Customising Skills & tasks
- Edit `skills/brand_voice/SKILL.md` to point to new references; the progressive loader automatically picks them up.
- Add JSON task files under `tasks/` and update `configs/bench.yaml` (or feed them via `--tasks`).
- Adjust repetitions, judges, or modes either in the config or through CLI flags.
- Switch to a live provider by flipping `provider`/`model`—the harness gracefully falls back to mock if credentials are absent.
- Config files are validated on load; if you introduce new tasks or Skill roots, keep paths accurate and ensure each Skill has a `SKILL.md`.
- Update the optional `pricing` block to match your provider’s rates so cost deltas reflect reality.

### Further reading
- `docs/CONFIG_REFERENCE.md` — field-by-field YAML specification and validation rules.
- `docs/WALKTHROUGH.md` — example run analysis template with interpretation guidance.
- `docs/FAQ.md` — answers for non-technical collaborators.

## Limitations
- The benchmark simulates progressive disclosure using declarative file references; Claude’s internal loader logic remains proprietary.
- Token accounting is available only when the provider exposes usage metadata.
- The LLM judge is optional and currently tuned for deterministic heuristic prompts; calibrate the rubric before using the scores for research claims.

## Roadmap
- TODO: Expand LLM-as-judge calibration sets and scale to additional Skill archetypes.
- TODO: Add richer report templates (HTML, interactive dashboards) alongside the Markdown + CSV exports.

For additional context and FAQs, see `docs/FAQ.md`.

## License
Apache License 2.0 — see `LICENSE`.

[1]: https://www.anthropic.com/news/skills?utm_source=chatgpt.com
[2]: https://opentelemetry.io/docs/specs/semconv/gen-ai/?utm_source=chatgpt.com
[3]: https://docs.claude.com/en/docs/claude-code/skills?utm_source=chatgpt.com
[4]: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills?utm_source=chatgpt.com
[5]: https://github.com/anthropics/skills?utm_source=chatgpt.com
[6]: https://support.claude.com/en/articles/12512180-using-skills-in-claude?utm_source=chatgpt.com
[7]: https://simonwillison.net/2025/Oct/16/claude-skills/?utm_source=chatgpt.com
