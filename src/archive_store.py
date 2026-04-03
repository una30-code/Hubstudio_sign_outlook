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

