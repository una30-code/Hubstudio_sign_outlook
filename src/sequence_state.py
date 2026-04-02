"""Sequence state storage for phase-0 environment naming."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

STATE_FILE_NAME = "sequence_state.json"
STATE_ROOT_KEY = "next_sequence_by_site_region_date"
DEFAULT_SEQUENCE = 1


@dataclass(frozen=True)
class SequenceAllocation:
    key: str
    sequence: int


def build_sequence_key(site_name: str, region: str, now: datetime | None = None) -> str:
    dt = now or datetime.now()
    date_part = f"{dt.year}年{dt.month}月{dt.day}日"
    return f"{site_name}|{region}|{date_part}"


def build_environment_name(
    site_name: str, sequence: int, region: str, now: datetime | None = None
) -> str:
    dt = now or datetime.now()
    date_part = f"{dt.year}年{dt.month}月{dt.day}日"
    return f"{site_name}{sequence}_{region}_{date_part}"


def _state_file(log_dir: Path) -> Path:
    return log_dir / STATE_FILE_NAME


def _read_state(log_dir: Path) -> dict[str, Any]:
    path = _state_file(log_dir)
    if not path.exists():
        return {STATE_ROOT_KEY: {}}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {STATE_ROOT_KEY: {}}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("sequence state must be a JSON object")
    if STATE_ROOT_KEY not in data or not isinstance(data[STATE_ROOT_KEY], dict):
        data[STATE_ROOT_KEY] = {}
    return data


def _write_state(log_dir: Path, data: dict[str, Any]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = _state_file(log_dir)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def get_next_sequence(
    *, log_dir: Path, site_name: str, region: str, sequence_start: int
) -> SequenceAllocation:
    if sequence_start < 1:
        raise ValueError("name_sequence_start must be >= 1")

    state = _read_state(log_dir)
    by_key: dict[str, Any] = state[STATE_ROOT_KEY]
    key = build_sequence_key(site_name, region)
    raw_current = by_key.get(key)
    if raw_current is None:
        current = sequence_start
    else:
        current = int(raw_current)

    return SequenceAllocation(key=key, sequence=current)


def commit_sequence(*, log_dir: Path, key: str, used_sequence: int) -> None:
    state = _read_state(log_dir)
    by_key: dict[str, Any] = state[STATE_ROOT_KEY]
    current_raw = by_key.get(key)
    current = int(current_raw) if current_raw is not None else DEFAULT_SEQUENCE
    next_value = max(current, used_sequence + 1)
    by_key[key] = next_value
    _write_state(log_dir, state)


def allocate_sequence(
    *, log_dir: Path, site_name: str, region: str, sequence_start: int
) -> SequenceAllocation:
    """Backward-compatible helper: allocate and commit immediately."""
    alloc = get_next_sequence(
        log_dir=log_dir,
        site_name=site_name,
        region=region,
        sequence_start=sequence_start,
    )
    commit_sequence(log_dir=log_dir, key=alloc.key, used_sequence=alloc.sequence)
    return alloc
