# Release Checklist (v1)

## Definition of Done
- [x] Core user journeys are coherent end-to-end (happy path + key failure states) with clear UX and copy.
- [x] Onboarding is implemented (first-run, empty states, progressive disclosure).
- [x] Help is implemented (in-app help/tooltips + a minimal docs/help page).
- [x] Quality gates: tests exist for critical logic and key UI flows, lint/typecheck/build pass, and CI is green.
- [x] Accessibility basics: keyboard navigation for primary flows, sensible focus states, labels/aria where needed.
- [x] Performance basics: no obvious slow pages, avoid unnecessary re-renders, reasonable bundle size for stack.
- [x] Security hygiene: no secrets in repo, validate inputs, safe error handling, auth boundaries respected (if applicable).
- [x] Docs: README includes local setup + run + test + deploy notes + env vars.

## Verification Snapshot
- Local gates passing: `uv run pytest -q`, `uv run ruff check .`, `uv run pyright`, `uv run python -m build`.
- CI passing: GitHub Actions run `22039375538` on `release-ready-v1`.
