from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_showcase_module() -> Any:
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "build_showcase_data.py"
    spec = importlib.util.spec_from_file_location("build_showcase_data", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_showcase_data_generates_expected_payload(tmp_path):
    module = _load_showcase_module()

    showcase_root = tmp_path / "showcase"
    module.SHOWCASE_DIR = showcase_root
    module.SHOWCASE_DATA = showcase_root / "data" / "evidence.json"
    module.SHOWCASE_CHARTS = showcase_root / "assets" / "charts"

    payload = module.build_showcase_data()
    written = json.loads(module.SHOWCASE_DATA.read_text(encoding="utf-8"))

    assert payload["generated_from"] == "sample_results"
    assert written["summary"]["mode_count"] == 3
    assert written["summary"]["task_count"] == 3
    assert written["summary"]["record_count"] == 9
    assert len(written["aggregates"]) == 3

    copied_charts = sorted(path.name for path in module.SHOWCASE_CHARTS.glob("*.png"))
    assert copied_charts == sorted(module.CHART_FILES)
