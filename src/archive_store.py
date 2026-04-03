"""Archive storage helpers (JSONL in logs/archive)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def append_archive_record(
    *,
    log_dir: Path,
    phase: str,
    payload: dict,
) -> tuple[str, str]:
    """
    Append one archive record and return (archive_path, archive_ref).

    Storage:
    - logs/archive/{phase}_{YYYYMMDD}.jsonl
    - one JSON object per line
    """

    now = datetime.now()
    archive_ref = f"{phase}-{now.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    archive_dir = log_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    file_path = archive_dir / f"{phase}_{now.strftime('%Y%m%d')}.jsonl"

    record = {
        "archive_ref": archive_ref,
        "archived_at": now.isoformat(timespec="seconds"),
        **payload,
    }
    with file_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False))
        fp.write("\n")
    return str(file_path), archive_ref


def read_latest_phase0_container_code(log_dir: Path) -> str | None:
    """
    从 phase-0 留档 JSONL 中取最近一条 success 且含环境 ID 的记录。
    匹配字段：containerCode（与 Hubstudio API 一致）或 container_code（pipeline data 键）。
    """

    archive_dir = log_dir / "archive"
    if not archive_dir.is_dir():
        return None
    paths = sorted(archive_dir.glob("phase0_env_create_*.jsonl"))
    last: str | None = None
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not obj.get("success"):
                continue
            code = obj.get("containerCode")
            if code is None:
                code = obj.get("container_code")
            if code is not None and str(code).strip():
                last = str(code).strip()
    return last


def read_latest_phase1_user_profile(log_dir: Path) -> dict[str, str] | None:
    """
    从 phase-1 留档 JSONL 中取最近一条 success 且含 account/password 的记录。
    用于 phase-2 按需求录入注册页（密码仅内存使用，勿写入日志）。
    """

    archive_dir = log_dir / "archive"
    if not archive_dir.is_dir():
        return None
    paths = sorted(archive_dir.glob("phase1_user_profile_*.jsonl"))
    last: dict[str, str] | None = None
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not obj.get("success"):
                continue
            account = obj.get("account")
            password = obj.get("password")
            if account is None or not str(account).strip():
                continue
            if password is None or not str(password):
                continue
            last = {
                "first_name": str(obj.get("first_name") or ""),
                "last_name": str(obj.get("last_name") or ""),
                "birth_date": str(obj.get("birth_date") or ""),
                "account": str(account).strip(),
                "password": str(password),
            }
    return last

