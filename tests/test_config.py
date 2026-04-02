"""config.load_settings 行为（注入 environ，不依赖真实 .env）。"""

import pytest

from src.config import (
    DEFAULT_PAGE_LOAD_TIMEOUT_MS,
    load_settings,
)


def test_load_settings_required_missing() -> None:
    with pytest.raises(ValueError, match="HUBSTUDIO_CDP_URL"):
        load_settings(environ={"OUTLOOK_REGISTER_URL": "https://example.com"})


def test_load_settings_minimal_mapping() -> None:
    s = load_settings(
        environ={
            "HUBSTUDIO_CDP_URL": "ws://127.0.0.1:9222/test",
            "OUTLOOK_REGISTER_URL": "https://signup.example/register",
        }
    )
    assert s.hubstudio_cdp_url == "ws://127.0.0.1:9222/test"
    assert s.outlook_register_url == "https://signup.example/register"
    assert s.page_load_timeout_ms == DEFAULT_PAGE_LOAD_TIMEOUT_MS


def test_load_settings_custom_timeout_and_paths() -> None:
    s = load_settings(
        environ={
            "HUBSTUDIO_CDP_URL": "ws://127.0.0.1:1",
            "OUTLOOK_REGISTER_URL": "https://a.example/",
            "PAGE_LOAD_TIMEOUT_MS": "12000",
            "SCREENSHOTS_DIR": "custom_shots",
            "LOG_DIR": "custom_logs",
        }
    )
    assert s.page_load_timeout_ms == 12_000
    assert s.screenshots_dir.name == "custom_shots"
    assert s.log_dir.name == "custom_logs"
