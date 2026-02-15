from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from .harness import (
    BenchmarkConfig,
    build_prompt,
    build_record,
    load_skill_definition,
    load_task,
)
from .judges import evaluate_output
from .providers import ProviderFactory


@dataclass(frozen=True)
class ExperimentCase:
    task_path: str
    mode: str
    model: str
    judge: str
    iteration: int


@dataclass
class ExperimentOptions:
    models: List[str] = field(default_factory=list)
    judges: List[str] = field(default_factory=list)
    max_workers: int = 4
    retry_attempts: int = 2
    rate_limit_qps: float = 0.0
    checkpoint_path: str | None = None
    resume: bool = True


class _RateLimiter:
    def __init__(self, qps: float):
        self._interval = 1.0 / qps if qps > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        if self._interval <= 0:
            return
        sleep_for = 0.0
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                sleep_for = self._next_allowed - now
            self._next_allowed = max(now, self._next_allowed) + self._interval
        if sleep_for > 0:
            time.sleep(sleep_for)


def run_experiment(
    config: BenchmarkConfig,
    options: ExperimentOptions,
    *,
    base_dir: Path,
) -> Tuple[List[Dict], Dict[str, int]]:
    models = options.models or [config.model]
    judges = options.judges or [config.judge]
    max_workers = max(1, int(options.max_workers))

    skill_root = _resolve_path(config.skill_root, base_dir)
    skill = load_skill_definition(skill_root)
    task_cache = {
        task_path: load_task(_resolve_path(Path(task_path), base_dir))
        for task_path in config.tasks
    }

    all_cases = _expand_cases(config, models=models, judges=judges)

    checkpoint_path = _resolve_checkpoint_path(options.checkpoint_path, base_dir)
    existing_records: List[Dict] = []
    completed_keys: set[str] = set()

    if checkpoint_path and options.resume and checkpoint_path.exists():
        existing_records, completed_keys = _load_checkpoint(checkpoint_path)
    elif checkpoint_path and checkpoint_path.exists() and not options.resume:
        checkpoint_path.write_text("")

    pending_cases = [
        case
        for case in all_cases
        if _case_key(case.task_path, case.mode, case.model, case.judge, case.iteration) not in completed_keys
    ]

    rate_limiter = _RateLimiter(options.rate_limit_qps)
    checkpoint_lock = threading.Lock()
    writer = None
    if checkpoint_path:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        writer = checkpoint_path.open("a", encoding="utf-8")

    results = list(existing_records)
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _run_case,
                    case=case,
                    config=config,
                    task=task_cache[case.task_path],
                    skill_root=skill_root,
                    skill=skill,
                    rate_limiter=rate_limiter,
                    retry_attempts=options.retry_attempts,
                ): case
                for case in pending_cases
            }
            for future in as_completed(futures):
                record = future.result()
                results.append(record)
                completed_keys.add(_record_key(record))
                if writer is not None:
                    with checkpoint_lock:
                        writer.write(json.dumps(record))
                        writer.write("\n")
                        writer.flush()
    finally:
        if writer is not None:
            writer.close()

    results.sort(key=_sort_key)
    metadata = {
        "total_cases": len(all_cases),
        "executed_cases": len(pending_cases),
        "reused_cases": len(existing_records),
    }
    return results, metadata


def _expand_cases(config: BenchmarkConfig, *, models: List[str], judges: List[str]) -> List[ExperimentCase]:
    cases: List[ExperimentCase] = []
    for task_path in config.tasks:
        for mode in config.modes:
            for model in models:
                for judge in judges:
                    for iteration in range(config.repetitions):
                        cases.append(
                            ExperimentCase(
                                task_path=task_path,
                                mode=mode,
                                model=model,
                                judge=judge,
                                iteration=iteration,
                            )
                        )
    return cases


def _run_case(
    *,
    case: ExperimentCase,
    config: BenchmarkConfig,
    task: dict,
    skill_root: Path,
    skill,
    rate_limiter: _RateLimiter,
    retry_attempts: int,
) -> Dict:
    prompt = build_prompt(
        mode=case.mode,
        task=task,
        skill_root=skill_root,
        skill=skill,
    )
    for attempt in range(max(0, retry_attempts) + 1):
        try:
            provider = ProviderFactory.create(config.provider, case.model)
            rate_limiter.wait()
            provider_result = provider.infer(prompt)
            judges = evaluate_output(task, provider_result.output, case.judge, provider)
            return build_record(
                task_path=case.task_path,
                task=task,
                mode=case.mode,
                iteration=case.iteration,
                prompt=prompt,
                provider_result=provider_result,
                judges=judges,
                pricing=config.pricing,
                provider_name=config.provider,
                model_name=case.model,
                judge_name=case.judge,
            )
        except Exception as exc:  # pragma: no cover - network/provider dependent
            if attempt >= retry_attempts:
                raise RuntimeError(
                    f"Experiment case failed: task={case.task_path} mode={case.mode} "
                    f"model={case.model} judge={case.judge} iteration={case.iteration}"
                ) from exc
            backoff = min(2.0, 0.25 * (2**attempt))
            time.sleep(backoff)
    raise RuntimeError("Unreachable retry state")


def _load_checkpoint(path: Path) -> Tuple[List[Dict], set[str]]:
    records: List[Dict] = []
    keys: set[str] = set()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            payload = line.strip()
            if not payload:
                continue
            record = json.loads(payload)
            key = _record_key(record)
            if key in keys:
                continue
            keys.add(key)
            records.append(record)
    return records, keys


def _resolve_path(path_value: str | Path, base_dir: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _resolve_checkpoint_path(path_value: str | None, base_dir: Path) -> Path | None:
    if not path_value:
        return None
    return _resolve_path(path_value, base_dir)


def _case_key(task_path: str, mode: str, model: str, judge: str, iteration: int) -> str:
    return "|".join([task_path, mode, model, judge, str(iteration)])


def _record_key(record: Dict) -> str:
    task_path = str(record.get("task_path", ""))
    mode = str(record.get("mode", ""))
    model = str(record.get("model", ""))
    judge = str(record.get("judge", ""))
    iteration = int(record.get("iteration", 0))
    return _case_key(task_path, mode, model, judge, iteration)


def _sort_key(record: Dict) -> Tuple[str, str, str, str, int]:
    return (
        str(record.get("task_path", "")),
        str(record.get("mode", "")),
        str(record.get("model", "")),
        str(record.get("judge", "")),
        int(record.get("iteration", 0)),
    )
