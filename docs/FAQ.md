# SkillBench-PD FAQ

## What is progressive disclosure?
Claude Skills load instructions and reference files on demand instead of dumping every document into the prompt. SkillBench-PD simulates that pattern by reading `SKILL.md`, mapping each topic to its referenced files, and only attaching those resources when a task matches the topic cues.

## Why compare baseline, naive, and progressive modes?
- **Baseline** shows the model’s performance with no extra context.
- **Naive** highlights the cost of loading the entire Skill folder—higher latency and token usage, with mixed quality.
- **Progressive** mirrors Claude’s loader: `SKILL.md` plus the files explicitly referenced for the relevant topic. Ideally it keeps quality high while trimming context.

## What do the scores mean?
- **Rule score (0.0–1.0)**: deterministic checks tailored to each task (banned words, heading format, bullet count).
- **LLM score (1–5)**: optional reviewer powered by a model provider; defaults to a mock scaling when no key is set.
- **Tokens**: estimated counts from the provider—only populated when the backend exposes usage metrics.
- **Latency**: wall-clock inference time in milliseconds.
- **Cost**: estimated USD spend based on `pricing.input_per_1k` and `pricing.output_per_1k` from the config (defaults to Claude Sonnet rates).

## I’m not a developer—how do I read the report?
Open `results/results.md` after a run. The first table shows average latency/tokens/quality for each mode. The delta tables explain how much naive/progressive differ from baseline. Scroll further to see the bar charts and task-specific latency histograms—“wide” histograms suggest unstable response times. No coding required.

## How can I customise the benchmark?
1. Add a new JSON task under `tasks/`.
2. Update `skills/<name>/SKILL.md` with a new topic and references.
3. Point `configs/bench.yaml` (or the CLI `--tasks`/`--skill-root` flags) to the additions.
4. Run `skillbench-pd` again to generate updated reports.
5. Update the `pricing` block if you want the cost estimates to reflect your provider/model choices.

## Can I run this with live Anthropic models?
Yes. Export `ANTHROPIC_API_KEY` and either set `provider: "anthropic"` in `configs/bench.yaml` or invoke `skillbench-pd --provider auto --model <model-name>`. The CLI will fall back to the mock provider if the key is missing.

## How should I cite or extend this work?
The repository is Apache-2.0 licensed and uses only synthetic data. Link back to the main README and include any new tasks or Skill references you add so others can reproduce your experiments.
