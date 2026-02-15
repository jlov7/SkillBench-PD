# Release-Ready v1 Design

## Summary
SkillBench-PD v1 remains CLI-first, with a GitHub Pages-ready HTML report generated alongside CSV/MD output. The HTML report becomes the primary user-facing artifact, providing onboarding, help, and shareability without introducing a full web app. Quality gates add lint/typecheck/build/CI while keeping the codebase lightweight.

## Goals
- Provide a static HTML report (`results/html/index.html`) with clear onboarding, help, and interpretation guidance.
- Keep core CLI workflow intact while adding an optional `--open-report` convenience.
- Add CI and quality gates (tests, lint, typecheck, build).
- Improve docs (setup/run/test/deploy/env vars, help page, release checklist).
- Preserve minimal risk and avoid broad refactors.

## Non-goals
- No live web app, backend, or authentication.
- No new data collection or non-synthetic tasks.
- No refactor of provider/judge logic beyond what is needed for reporting.

## Architecture
- HTML report generator lives in `bench/report.py`, producing:
  - `results/html/index.html`
  - `results/html/assets/style.css`
  - `results/html/assets/app.js` (minimal behavior only)
  - chart images copied into `results/html/assets/`.
- The report uses semantic HTML, minimal JS, and high-contrast CSS with focus states.
- Report sections:
  - Overview (summary cards, first-run/empty-state messaging)
  - Aggregates + deltas (tables)
  - Per-task breakdowns (tables)
  - Charts (latency + quality, per-task latency)
  - Help/Methodology (in-app help + tooltips)
  - Sharing instructions (GitHub Pages)
- CLI updates:
  - Always generates HTML reports.
  - Adds `--open-report` to open `index.html` after completion.

## Data Flow
- Benchmark run -> results list -> `generate_reports` -> CSV/MD/charts -> HTML report.
- HTML uses aggregates computed in `bench/report.py`; no runtime JS data fetching.

## Error Handling
- If results are empty, HTML renders a friendly empty-state with a command to run.
- CLI prints clear error messages when config is invalid or provider is unavailable.

## Testing
- Unit tests for HTML report generation (file creation, key sections, asset paths).
- CLI test for `--open-report` (mocking open command).
- Existing report tests updated to cover HTML artifacts.

## Accessibility
- Semantic headings, skip-link, keyboard focus styles, aria labels for charts where needed.
- Tooltips via `title` on small info badges.

## Deployment
- GitHub Pages from `results/html/` (documented in README).

