# Release-ready v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship v1 with a shareable static HTML report, CLI polish, quality gates, and docs.

**Architecture:** Generate `results/html/` from `bench/report.py` with server-rendered HTML tables and copied chart assets. CLI optionally opens the report. Add CI + lint/typecheck/build and update docs for setup/run/test/deploy.

**Tech Stack:** Python (uv, pytest), static HTML/CSS/JS, GitHub Actions.

---

### Task 1: Add HTML report output structure

**Files:**
- Modify: `bench/report.py`
- Create: `bench/report_assets/style.css`
- Create: `bench/report_assets/app.js`
- Test: `tests/test_report.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
from bench.report import generate_reports

def test_generate_reports_creates_html_assets(tmp_path):
    artifacts = generate_reports(sample_results(), tmp_path)
    html_root = Path(tmp_path) / "html"
    assert html_root.exists()
    assert (html_root / "index.html").exists()
    assert (html_root / "assets" / "style.css").exists()
    assert (html_root / "assets" / "app.js").exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_report.py::test_generate_reports_creates_html_assets -q`
Expected: FAIL with missing HTML assets.

**Step 3: Write minimal implementation**

```python
# In bench/report.py
html_root = output_path / "html"
assets_dir = html_root / "assets"
assets_dir.mkdir(parents=True, exist_ok=True)
(html_root / "index.html").write_text("<html>...</html>")
shutil.copyfile(assets_source / "style.css", assets_dir / "style.css")
shutil.copyfile(assets_source / "app.js", assets_dir / "app.js")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_report.py::test_generate_reports_creates_html_assets -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add bench/report.py bench/report_assets/style.css bench/report_assets/app.js tests/test_report.py
git commit -m "feat: add html report scaffold" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Render HTML report content (tables, charts, help, empty state)

**Files:**
- Modify: `bench/report.py`
- Test: `tests/test_report.py`

**Step 1: Write the failing test**

```python
def test_html_report_contains_sections(tmp_path):
    artifacts = generate_reports(sample_results(), tmp_path)
    html_text = (Path(tmp_path) / "html" / "index.html").read_text()
    assert "Overview" in html_text
    assert "Aggregated metrics" in html_text
    assert "Delta vs baseline" in html_text
    assert "Help & Methodology" in html_text
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_report.py::test_html_report_contains_sections -q`
Expected: FAIL (missing sections).

**Step 3: Write minimal implementation**

```python
# Add helper functions to render tables and sections.
# Include empty-state copy when results are empty.
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_report.py::test_html_report_contains_sections -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add bench/report.py tests/test_report.py
git commit -m "feat: render html report sections" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Copy chart images into HTML assets

**Files:**
- Modify: `bench/report.py`
- Test: `tests/test_report.py`

**Step 1: Write the failing test**

```python
def test_html_report_copies_charts(tmp_path):
    artifacts = generate_reports(sample_results(), tmp_path)
    html_assets = Path(tmp_path) / "html" / "assets"
    assert (html_assets / "chart_latency.png").exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_report.py::test_html_report_copies_charts -q`
Expected: FAIL (chart not copied).

**Step 3: Write minimal implementation**

```python
# Copy charts produced in output_path into html/assets
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_report.py::test_html_report_copies_charts -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add bench/report.py tests/test_report.py
git commit -m "feat: include charts in html report" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Add CLI flag to open report

**Files:**
- Modify: `bench/cli.py`
- Test: `tests/test_cli.py`

**Step 1: Write the failing test**

```python
def test_cli_open_report_invokes_browser(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr("bench.cli._open_report", lambda path: opened.append(path))
    args = [
        "--config", "configs/bench.yaml",
        "--output-dir", str(tmp_path),
        "--repetitions", "1",
        "--modes", "baseline",
        "--tasks", "tasks/t1_rewrite_brand.json",
        "--provider", "mock",
        "--open-report",
    ]
    cli.main(args)
    assert opened
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_cli_open_report_invokes_browser -q`
Expected: FAIL (flag missing).

**Step 3: Write minimal implementation**

```python
# Add --open-report flag, _open_report helper using webbrowser.open
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py::test_cli_open_report_invokes_browser -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add bench/cli.py tests/test_cli.py
git commit -m "feat: add open report flag" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Add lint/typecheck/build tooling and CI

**Files:**
- Modify: `pyproject.toml`
- Create: `pyrightconfig.json`
- Create: `.github/workflows/ci.yml`

**Step 1: Write the failing test**

```text
# Not a unit test. Validate by running CI commands locally once configs exist.
```

**Step 2: Run command to verify it fails**

Run: `uv run ruff check .`
Expected: FAIL (ruff not installed).

**Step 3: Write minimal implementation**

```toml
# Add ruff and pyright to [project.optional-dependencies].dev
```

**Step 4: Run commands to verify they pass**

Run: `uv run ruff check .`
Expected: PASS.
Run: `uv run pyright`
Expected: PASS (configure pyright for permissive mode initially).
Run: `python -m build`
Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml pyrightconfig.json .github/workflows/ci.yml
git commit -m "chore: add lint typecheck build and ci" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Docs refresh + help page

**Files:**
- Modify: `README.md`
- Create: `docs/HELP.md`
- Modify: `AGENTS.md`

**Step 1: Write the failing test**

```text
# Not a unit test. Validate manually by reading docs.
```

**Step 2: Run manual check**

Open `README.md` and verify it includes setup/run/test/deploy/env vars + HTML report info.

**Step 3: Write minimal implementation**

```markdown
# docs/HELP.md
- What each mode means
- How to read deltas
- How to share via GitHub Pages
```

**Step 4: Verify**

Ensure README and HELP are consistent and reference `results/html/index.html`.

**Step 5: Commit**

```bash
git add README.md docs/HELP.md AGENTS.md
git commit -m "docs: add help and deployment guidance" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```
