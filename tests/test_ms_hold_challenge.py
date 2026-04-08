"""`ms_hold_challenge`：人机页文案检测与「Press and hold」长按点击（pytest）。

- 无浏览器：Mock `page` 校验 `_page_looks_like_press_hold_challenge`。
- 有浏览器：`playwright install chromium` 后，用 `set_content` 模拟微软卡片结构，调用 `try_ms_accessible_hold_challenge` 验证能定位并执行带 delay 的点击。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.ms_hold_challenge import (
    _page_looks_like_press_hold_challenge,
    try_ms_accessible_hold_challenge,
)

# 贴近当前「Let's prove you're human / Press and hold」卡片的最小 DOM（非真实微软页面）
_PRESS_HOLD_FIXTURE_HTML = """
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/></head>
<body>
  <div>michaelramirez20619@outlook.com</div>
  <h1>Let's prove you're human</h1>
  <p>Press and hold the button.</p>
  <button type="button" aria-label="Accessible challenge">◇</button>
  <button type="button">Press and hold</button>
</body></html>
"""


def _mock_page_with_body_text(text: str) -> MagicMock:
    page = MagicMock()
    body_loc = MagicMock()
    body_loc.inner_text.return_value = text
    page.locator.return_value = body_loc
    return page


def test_page_looks_like_press_hold_positive() -> None:
    page = _mock_page_with_body_text("Let's prove you're human\nPress and hold the button.")
    assert _page_looks_like_press_hold_challenge(page) is True


def test_page_looks_like_press_hold_negative() -> None:
    page = _mock_page_with_body_text("Sign in to your account")
    assert _page_looks_like_press_hold_challenge(page) is False


def test_page_looks_like_press_hold_chinese_keywords() -> None:
    page = _mock_page_with_body_text("请按住按钮")
    assert _page_looks_like_press_hold_challenge(page) is True


def test_try_ms_accessible_hold_challenge_disabled_skips() -> None:
    page = MagicMock()
    r = try_ms_accessible_hold_challenge(
        page,
        enabled=False,
        form_step_timeout_ms=5_000,
        after_accessible_wait_ms=0,
        hold_press_ms=2_000,
        chrome_password_prompt="skip",
        screenshots_dir=Path("/tmp"),
    )
    assert r["success"] is True
    assert r["data"].get("skipped") is True


@pytest.fixture
def playwright_chromium_page():
    """本机需已安装浏览器：`playwright install chromium`。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        pytest.skip(f"playwright 未安装: {e}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            pytest.skip(f"无法启动 Chromium（是否已执行 playwright install chromium？）: {e}")
        page = browser.new_page()
        yield page
        browser.close()


def test_try_ms_accessible_hold_challenge_clicks_press_and_hold(
    playwright_chromium_page, tmp_path: Path
) -> None:
    """在可控 HTML 上应能识别为人机页，并完成无障碍入口 + 长按主按钮。"""
    page = playwright_chromium_page
    page.set_content(_PRESS_HOLD_FIXTURE_HTML)

    r = try_ms_accessible_hold_challenge(
        page,
        enabled=True,
        form_step_timeout_ms=15_000,
        after_accessible_wait_ms=150,
        # 实现内 clamp 为 [1500, 25000]，取 2000 便于断言
        hold_press_ms=2_000,
        chrome_password_prompt="skip",
        screenshots_dir=tmp_path,
    )
    assert r["success"] is True, f"期望成功，实际: {r}"
    assert r["data"].get("skipped") is False
    assert r["data"].get("hold_press_ms") == 2_000
