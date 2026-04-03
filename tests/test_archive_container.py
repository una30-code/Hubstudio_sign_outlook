"""read_latest_phase0_container_code / read_latest_phase1_user_profile 行为。"""

from pathlib import Path

from src.archive_store import read_latest_phase0_container_code, read_latest_phase1_user_profile


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


def test_read_latest_phase1_prefers_last_success(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    f = archive / "phase1_user_profile_20260403.jsonl"
    f.write_text(
        '{"success": false, "account": "a1", "password": "x"}\n'
        '{"success": true, "first_name": "A", "last_name": "B", "birth_date": "1990-01-01", '
        '"account": "ab12345", "password": "Ab1cdEfgh2"}\n',
        encoding="utf-8",
    )
    p = read_latest_phase1_user_profile(tmp_path)
    assert p is not None
    assert p["account"] == "ab12345"
    assert p["password"] == "Ab1cdEfgh2"
    assert p["first_name"] == "A"


def test_read_latest_phase1_missing_returns_none(tmp_path: Path) -> None:
    assert read_latest_phase1_user_profile(tmp_path) is None
