# Next-Level Overnight Build Tracker

## Goal
Ship a production-grade experiment orchestration and regression analysis system that can run matrix experiments, recover from failures, and gate releases with statistical evidence.

## Scope
- Parallel experiment orchestrator with rate limiting, retries, checkpointing, and resume.
- Statistical engine (confidence intervals, permutation significance, effect size).
- Regression detector and pass/fail gate output.
- CLI integration for orchestration + gate enforcement.
- Report artifacts (JSON + Markdown) for release decisions.
- Tests for core logic and critical CLI flow.
- Docs updates for setup, usage, and CI behavior.

## Milestones

### M1. Planning + Tracking
- [x] Create exhaustive execution tracker.
- [x] Keep this tracker current at each milestone.

### M2. Orchestrator Core
- [x] Add experiment case model and option model.
- [x] Add matrix expansion over tasks/modes/models/judges/repetitions.
- [x] Add threadpool execution with configurable max workers.
- [x] Add shared rate limiter (QPS).
- [x] Add retry loop with bounded backoff.
- [x] Add checkpoint writer (append JSONL).
- [x] Add resume logic (skip completed case keys).
- [x] Add deterministic result ordering.

### M3. Statistics + Regression Engine
- [x] Add bootstrap confidence interval helper.
- [x] Add permutation significance helper.
- [x] Add effect size helper (Cohen's d).
- [x] Add baseline-vs-candidate comparison model.
- [x] Add regression threshold model.
- [x] Add regression flagging logic for latency/rule-score/cost.
- [x] Add overall pass/fail verdict.
- [x] Add JSON + Markdown regression report generation.

### M4. CLI Integration
- [x] Add orchestration flags (matrix, workers, retries, rate-limit, checkpoint/resume).
- [x] Add regression gate flags (thresholds + fail-on-regression + output path).
- [x] Add orchestrated execution path in `skillbench-pd`.
- [x] Add console summary of regression status and flagged findings.
- [x] Exit non-zero when `--fail-on-regression` and verdict fails.

### M5. Quality + Tests
- [x] Add orchestrator tests (matrix size, checkpoint resume behavior).
- [x] Add stats/regression tests (significance/effect/regression verdict).
- [x] Add CLI orchestration test (artifacts + report generation).
- [x] Add CLI gate-failure test (`--fail-on-regression` exits non-zero).
- [x] Ensure all existing tests still pass.

### M6. Docs + CI
- [x] Update README with orchestration and regression gate usage.
- [x] Update help docs with troubleshooting and recommended thresholds.
- [x] Ensure CI still passes with new feature set.
- [x] Capture final verification evidence and close tracker.

## Verification Commands
- [x] `uv run pytest -q`
- [x] `uv run ruff check .`
- [x] `uv run pyright`
- [x] `uv run python -m build`

## Verification Evidence
- Full suite: `27 passed` (includes new orchestrator/regression tests).
- Orchestration smoke run: generated checkpoint + HTML + regression artifacts in `/tmp/skillbench-next-level-1771174980`.
- Gate behavior validation: strict regression thresholds triggered `Regression gate: FAIL` and exit code `2`.
- Build: sdist + wheel generated successfully.

## Notes / Risks
- Parallel provider calls may stress external APIs; keep retries/rate-limits conservative.
- Statistical tests must be deterministic in CI; use deterministic seeds.
- Gate thresholds should be configurable to avoid brittle defaults.
