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
    click_ms_challenge_accessibility_only,
    press_ms_challenge_hold_only,
    try_ms_accessible_hold_challenge,
    wait_ms_challenge_step03,
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

# 仅有主按钮、无无障碍入口（用于幂等 noop）
_PRESS_HOLD_NO_ACCESS_HTML = """
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/></head>
<body>
  <h1>Let's prove you're human</h1>
  <p>Press and hold the button.</p>
  <button type="button">Press and hold</button>
</body></html>
"""

# 主文档仅有说明、可操作控件在同源 iframe（模拟 hsprotect 外仅文案、内层才有点击目标）
_NESTED_IFRAME_HOLD_HTML = """
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>outer</title></head>
<body>
  <h1>Let's prove you're human</h1>
  <p>Please complete verification in the frame below.</p>
  <iframe srcdoc="<!DOCTYPE html><html><head><meta charset=&quot;utf-8&quot;/></head>
  <body>
    <p>Extra text so outer heuristics differ.</p>
    <button type=&quot;button&quot; aria-label=&quot;Accessible challenge&quot;>◇</button>
    <p>Press and hold</p>
  </body></html>"></iframe>
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


def test_page_looks_like_press_hold_lets_prove_heading() -> None:
    page = _mock_page_with_body_text("Let's prove you're human\nPress and hold the button.")
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
    assert r["data"].get("skip_reason") == "disabled"


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


def test_try_ms_accessible_hold_challenge_nested_iframe_prefers_inner(
    playwright_chromium_page, tmp_path: Path
) -> None:
    """主文档无真实按钮、挑战在 iframe 内且文案为 <p>Press and hold</p> 时应仍能成功。"""
    page = playwright_chromium_page
    page.set_content(_NESTED_IFRAME_HOLD_HTML)

    r = try_ms_accessible_hold_challenge(
        page,
        enabled=True,
        form_step_timeout_ms=15_000,
        after_accessible_wait_ms=150,
        hold_press_ms=2_000,
        chrome_password_prompt="skip",
        screenshots_dir=tmp_path,
        prep_short_sleep_ms=0,
        prep_poll_ms=2_000,
    )
    assert r["success"] is True, f"期望成功，实际: {r}"
    assert r["data"].get("challenge_root") in {"iframe", "iframe_hsprotect"}, r
    assert r["data"].get("skipped") is False


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
        prep_short_sleep_ms=0,
        prep_poll_ms=2_000,
    )
    assert r["success"] is True, f"期望成功，实际: {r}"
    assert r["data"].get("skipped") is False
    assert r["data"].get("hold_press_ms") == 2_000
    assert r["data"].get("accessibility_used_force") is False
    assert r["data"].get("hold_used_force") is False


def test_click_accessibility_only_on_fixture(playwright_chromium_page, tmp_path: Path) -> None:
    page = playwright_chromium_page
    page.set_content(_PRESS_HOLD_FIXTURE_HTML)
    r = click_ms_challenge_accessibility_only(
        page,
        form_step_timeout_ms=15_000,
        chrome_password_prompt="skip",
        screenshots_dir=tmp_path,
    )
    assert r["success"] is True, r
    assert r["data"].get("accessibility_used_force") is False


def test_click_accessibility_noop_when_only_press_visible(
    playwright_chromium_page, tmp_path: Path
) -> None:
    page = playwright_chromium_page
    page.set_content(_PRESS_HOLD_NO_ACCESS_HTML)
    r = click_ms_challenge_accessibility_only(
        page,
        form_step_timeout_ms=15_000,
        chrome_password_prompt="skip",
        screenshots_dir=tmp_path,
        noop_if_accessibility_missing=True,
    )
    assert r["success"] is True, r
    assert r["data"].get("noop_accessibility") is True


def test_press_hold_only_on_fixture(playwright_chromium_page, tmp_path: Path) -> None:
    page = playwright_chromium_page
    page.set_content(_PRESS_HOLD_FIXTURE_HTML)
    r = press_ms_challenge_hold_only(
        page,
        form_step_timeout_ms=15_000,
        hold_press_ms=2_000,
        chrome_password_prompt="skip",
        screenshots_dir=tmp_path,
    )
    assert r["success"] is True, r
    assert r["data"].get("hold_press_ms") == 2_000
    assert r["data"].get("hold_used_force") is False


def test_wait_step03_sleep(playwright_chromium_page, tmp_path: Path) -> None:
    page = playwright_chromium_page
    page.set_content(_PRESS_HOLD_FIXTURE_HTML)
    r = wait_ms_challenge_step03(
        page,
        mode="sleep",
        sleep_ms=50,
        until_press_timeout_ms=1_000,
        form_step_timeout_ms=5_000,
        screenshots_dir=tmp_path,
    )
    assert r["success"] is True, r
    assert r["data"].get("mode") == "sleep"
    assert (tmp_path / "ms_hold_step_wait.png").is_file()


def test_wait_step03_until_press(playwright_chromium_page, tmp_path: Path) -> None:
    page = playwright_chromium_page
    page.set_content(_PRESS_HOLD_FIXTURE_HTML)
    r = wait_ms_challenge_step03(
        page,
        mode="until_press",
        sleep_ms=0,
        until_press_timeout_ms=5_000,
        form_step_timeout_ms=15_000,
        screenshots_dir=tmp_path,
    )
    assert r["success"] is True, r
    assert r["data"].get("press_visible") is True
