# Release-ready v1

## Purpose / Big Picture
Ship a production-ready v1 of SkillBench-PD with a CLI-first workflow and a shareable static HTML report, plus onboarding/help, quality gates, and clear documentation so new users can run, interpret, and publish results confidently.

## Approach
- Generate a static HTML report alongside existing CSV/MD outputs, optimized for shareability and accessibility.
- Add CLI affordances (open report) and clear UX copy for onboarding/help.
- Introduce lint/typecheck/build/CI gates with minimal tooling overhead.
- Update documentation and release checklist to match v1 definition-of-done.

## Files To Modify
- `bench/report.py` (HTML report generator + asset handling).
- `bench/cli.py` (open report flag + output messaging).
- `tests/test_report.py` and new tests for HTML outputs.
- `README.md` + new help/deploy docs.
- CI workflow in `.github/workflows/`.

## Risks
- HTML report scope creep (avoid full web app behavior).
- CI/lint/typecheck additions causing false failures without calibration.
- Asset handling on GitHub Pages (ensure relative paths and offline loading).

## Validation Gates
- `uv run pytest -q`
- `uv run ruff check .`
- `uv run pyright`
- `python -m build` (or equivalent)
- CI green on main branch

## Progress
- [x] Milestone 1: Steering + baseline fixes (AGENTS.md, RELEASE_CHECKLIST.md, QUESTIONS.md, design + implementation plan, fix failing tests).
- [x] Milestone 2: HTML report generation (index + assets + charts copy) with onboarding/help/empty states.
- [x] Milestone 3: CLI UX polish (`--open-report`) and help/tooltips integration.
- [x] Milestone 4: Quality gates (ruff + pyright + build + CI) and update tests for HTML/CLI.
- [x] Milestone 5: Docs refresh (README setup/run/test/deploy/env vars, HELP.md, GitHub Pages guidance).
- [x] Milestone 6: Final verification, release checklist pass, and release report.

## Surprises & Discoveries
- Baseline tests failed in `tests/test_harness.py` due to regex patterns being double-escaped; fixed in `bench/harness.py`.
- `uv` is available (0.10.2) and used for env/test runs.
- Enabling lint/typecheck surfaced Python 3.10 f-string compatibility edges in HTML rendering; fixed with precomputed HTML fragments.
- Packaging builds cleanly but emits setuptools deprecation warnings for license metadata; non-blocking for v1.

## Decision Log
- Chose static HTML report (GitHub Pages-ready) instead of a full web UI to minimize risk and deliver shareability quickly.
- Standardized on GitHub Pages as the deployment target for reports.

## Outcomes & Retrospective
- [x] All v1 definition-of-done items satisfied.
- [x] CI green on pushed branch (`release-ready-v1`, run `22039375538`).
- [x] Release report prepared with run/test/deploy steps.

---

# Overnight Next-Level Feature

## Purpose / Big Picture
Add a high-complexity experiment platform on top of the benchmark so large matrix runs can be executed, resumed safely, and evaluated using statistical release gates.

## Scope
- Parallel matrix orchestrator (tasks x modes x models x judges x repetitions).
- Retry + global QPS limiter + checkpoint/resume support.
- Statistical regression engine (bootstrap CI, permutation p-value, Cohen's d).
- Pass/fail regression report artifacts and CLI non-zero gate mode.
- CI gate step and tests for orchestrator/statistics/CLI failure state.

## Progress
- [x] Add orchestrator module (`bench/experiment.py`) with checkpoint/resume.
- [x] Add regression module (`bench/regression.py`) with pass/fail verdict.
- [x] Integrate CLI orchestration and gate flags.
- [x] Add critical tests (`tests/test_experiment.py`, CLI gate tests).
- [x] Update docs and CI workflow for new feature.
- [x] Run full quality gates locally.

## Surprises & Discoveries
- Base project env was re-created without dev dependencies; resolved with `uv sync --extra dev`.
- Strict regression thresholds reliably trigger non-zero exit for gate validation using mock provider.

## Decision Log
- Kept regression thresholds configurable and defaulted conservatively to avoid brittle CI failures.
- Generated both machine (`.json`) and human (`.md`) regression outputs for release workflows.

## Outcomes & Retrospective
- [x] Feature set implemented end-to-end.
- [x] Quality gates passing locally (`pytest`, `ruff`, `pyright`, `build`).
- [x] Exhaustive execution tracker completed in `NEXT_LEVEL_TODO.md`.

---

# Demo Hub Shareability Polish

## Purpose / Big Picture
Make public onboarding/demo access world-class by shipping a lightweight static demo hub, integrating it across docs, and publishing to Vercel.

## Progress
- [x] Build `showcase/` static demo hub with stakeholder + technical + evidence journeys.
- [x] Add data build script (`scripts/build_showcase_data.py`) from committed sample artifacts.
- [x] Deploy demo hub to Vercel production alias.
- [x] Integrate live demo + runbook paths into README and docs.
- [x] Harden front-end basics (keyboard/focus + reduced-motion + safer rendering).

## Decision Log
- Kept demo hub static (no framework) to reduce runtime risk and maximize portability.
- Linked the demo hub to committed sample outputs so demos remain deterministic and reproducible.

## Outcomes & Retrospective
- [x] Public live demo URL available for stakeholder sharing.
- [x] Setup and try-it docs now support zero-setup, Codespaces, and local paths.

---

# Showcase UX Hardening

## Purpose / Big Picture
Increase demo usability and shareability by adding clearer onboarding, in-app help mechanics, and stronger accessibility semantics.

## Progress
- [x] Added explicit `Guide` journey page to bridge stakeholder and technical flows.
- [x] Added `Start Here (3 Steps)` onboarding section on the demo hub.
- [x] Added persistent in-app help drawer with keyboard-close/focus behavior.
- [x] Improved evidence UX with loading/status messaging and better table semantics.
- [x] Re-verified runtime behavior via Playwright smoke checks (desktop + mobile).

## Outcomes & Retrospective
- [x] Front-end flow is now more guided and first-run friendly.
- [x] Console/network smoke checks reported no runtime errors across showcase pages.
