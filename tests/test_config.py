"""config.load_settings 行为（注入 environ，不依赖真实 .env）。"""

import pytest

from src.config import (
    DEFAULT_PAGE_LOAD_TIMEOUT_MS,
    DEFAULT_PHASE2_ACTION_DELAY_MS,
    DEFAULT_PHASE2_FORM_TIMEOUT_MS,
    DEFAULT_PHASE2_HOLD_LOCATOR_PROBE_MS,
    load_phase2_settings,
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


def test_load_phase2_settings_defaults_and_overrides() -> None:
    base = {
        "HUBSTUDIO_API_BASE": "http://127.0.0.1:1",
        "HUBSTUDIO_CONTAINER": "c1",
        "OUTLOOK_REGISTER_URL": "https://signup.example/",
    }
    s = load_phase2_settings(environ=base)
    assert s.page_load_timeout_ms == DEFAULT_PAGE_LOAD_TIMEOUT_MS
    assert s.phase2_form_timeout_ms == DEFAULT_PHASE2_FORM_TIMEOUT_MS
    assert s.phase2_action_delay_ms == DEFAULT_PHASE2_ACTION_DELAY_MS
    assert s.chrome_password_prompt == "skip"
    assert s.phase2_try_hold_challenge is True
    assert s.phase2_hold_prep_short_sleep_ms == 4_000
    assert s.phase2_hold_prep_poll_ms == 20_000
    assert s.phase2_hold_refind_root_before_press is True
    assert s.phase2_hold_warmup_viewport_click is True
    assert s.phase2_hold_warmup_settle_ms == 280
    assert s.phase2_hold_locator_probe_ms == DEFAULT_PHASE2_HOLD_LOCATOR_PROBE_MS

    s_hold_off = load_phase2_settings(environ={**base, "PHASE2_TRY_HOLD_CHALLENGE": "0"})
    assert s_hold_off.phase2_try_hold_challenge is False

    s_ref_off = load_phase2_settings(environ={**base, "MS_HOLD_REFIND_ROOT_BEFORE_PRESS": "0"})
    assert s_ref_off.phase2_hold_refind_root_before_press is False

    s_warm_off = load_phase2_settings(
        environ={**base, "PHASE2_HOLD_WARMUP_VIEWPORT_CLICK": "0"}
    )
    assert s_warm_off.phase2_hold_warmup_viewport_click is False

    assert s.phase2_behavior_simulation == "off"
    assert s.phase2_behavior_jitter_min_ms == 0
    assert s.phase2_behavior_jitter_max_ms == 0

    s_bh = load_phase2_settings(environ={**base, "PHASE2_BEHAVIOR_SIMULATION": "light"})
    assert s_bh.phase2_behavior_simulation == "light"
    assert s_bh.phase2_behavior_jitter_min_ms == 50
    assert s_bh.phase2_behavior_jitter_max_ms == 200

    s_bm = load_phase2_settings(environ={**base, "PHASE2_BEHAVIOR_SIMULATION": "medium"})
    assert s_bm.phase2_behavior_jitter_min_ms == 200
    assert s_bm.phase2_behavior_jitter_max_ms == 800

    s_bj = load_phase2_settings(
        environ={
            **base,
            "PHASE2_BEHAVIOR_SIMULATION": "light",
            "PHASE2_BEHAVIOR_JITTER_MIN_MS": "10",
            "PHASE2_BEHAVIOR_JITTER_MAX_MS": "20",
        }
    )
    assert s_bj.phase2_behavior_jitter_min_ms == 10
    assert s_bj.phase2_behavior_jitter_max_ms == 20

    s2 = load_phase2_settings(
        environ={
            **base,
            "PHASE2_ACTION_DELAY_MS": "250",
            "PHASE2_CHROME_PASSWORD_PROMPT": "dismiss",
        }
    )
    assert s2.phase2_action_delay_ms == 250
    assert s2.chrome_password_prompt == "dismiss"

    s3 = load_phase2_settings(
        environ={**base, "PHASE2_CHROME_PASSWORD_PROMPT": "save"}
    )
    assert s3.chrome_password_prompt == "save"
