"""read_latest_phase0_container_code 行为。"""

from pathlib import Path

from src.archive_store import read_latest_phase0_container_code


def test_read_latest_phase0_container_code_prefers_last_success(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    f = archive / "phase0_env_create_20260402.jsonl"
    f.write_text(
        '{"success": false, "containerCode": "111"}\n'
        '{"success": true, "containerCode": "222"}\n',
        encoding="utf-8",
    )
    assert read_latest_phase0_container_code(tmp_path) == "222"


def test_read_latest_phase0_container_code_accepts_container_code_key(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    f = archive / "phase0_env_create_20260402.jsonl"
    f.write_text('{"success": true, "container_code": "333"}\n', encoding="utf-8")
    assert read_latest_phase0_container_code(tmp_path) == "333"


def test_read_latest_phase0_missing_returns_none(tmp_path: Path) -> None:
    assert read_latest_phase0_container_code(tmp_path) is None
