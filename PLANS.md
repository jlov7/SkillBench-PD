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
- [ ] Milestone 6: Final verification, release checklist pass, and release report.

## Surprises & Discoveries
- Baseline tests failed in `tests/test_harness.py` due to regex patterns being double-escaped; fixed in `bench/harness.py`.
- `uv` is available (0.10.2) and used for env/test runs.
- Enabling lint/typecheck surfaced Python 3.10 f-string compatibility edges in HTML rendering; fixed with precomputed HTML fragments.
- Packaging builds cleanly but emits setuptools deprecation warnings for license metadata; non-blocking for v1.

## Decision Log
- Chose static HTML report (GitHub Pages-ready) instead of a full web UI to minimize risk and deliver shareability quickly.
- Standardized on GitHub Pages as the deployment target for reports.

## Outcomes & Retrospective
- [ ] All v1 definition-of-done items satisfied.
- [ ] CI green on main branch after push.
- [ ] Release report published with run/test/deploy steps.
