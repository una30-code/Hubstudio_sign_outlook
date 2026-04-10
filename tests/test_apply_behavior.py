"""apply_signup_profile：行为模拟（主步骤间抖动）。"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from src.apply_signup_profile import _step_pause_with_behavior


def test_step_pause_with_behavior_adds_jitter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.apply_signup_profile.random.randint", lambda a, b: 77)
    page = MagicMock()
    log = logging.getLogger("test_apply_behavior")
    _step_pause_with_behavior(
        page,
        0,
        behavior_simulation="light",
        behavior_jitter_min_ms=10,
        behavior_jitter_max_ms=100,
        log=log,
    )
    page.wait_for_timeout.assert_called_once_with(77)


def test_step_pause_with_behavior_off_skips_jitter() -> None:
    page = MagicMock()
    log = logging.getLogger("test_apply_behavior")
    _step_pause_with_behavior(
        page,
        0,
        behavior_simulation="off",
        behavior_jitter_min_ms=50,
        behavior_jitter_max_ms=200,
        log=log,
    )
    page.wait_for_timeout.assert_not_called()
