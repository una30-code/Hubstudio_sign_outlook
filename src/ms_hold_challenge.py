"""Microsoft 注册流中「无障碍挑战 + Press and hold」可选自动化。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    from apply_signup_profile import _try_chrome_password_prompt
    from step_result import StepResult, step_result
else:
    from .apply_signup_profile import _try_chrome_password_prompt
    from .step_result import StepResult, step_result


def _try_screenshot(page: Any, screenshots_dir: Path, filename_prefix: str) -> str | None:
    try:
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        path = screenshots_dir / f"{filename_prefix}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)
    except Exception:
        return None


def _body_text_lower(root: Any, *, timeout_ms: int) -> str:
    try:
        return root.locator("body").inner_text(timeout=timeout_ms).lower()
    except Exception:
        return ""


def _page_looks_like_press_hold_challenge(page: Any) -> bool:
    t = _body_text_lower(page, timeout_ms=3_000)
    if "press and hold" in t or "prove you" in t or "prove you're" in t:
        return True
    if "按住" in t or "长按" in t:
        return True
    return False


def _find_challenge_root(page: Any) -> tuple[Any, str] | None:
    """主文档或子 frame（微软验证常在 iframe）；未识别到则 None。"""
    if _page_looks_like_press_hold_challenge(page):
        return page, "main"
    for fr in page.frames:
        try:
            if fr == page.main_frame:
                continue
        except Exception:
            continue
        t = _body_text_lower(fr, timeout_ms=2_500)
        if "press and hold" in t or "prove you" in t or "按住" in t or "长按" in t:
            return fr, "iframe"
    return None


def _escape_burst(page: Any) -> None:
    try:
        for _ in range(5):
            page.keyboard.press("Escape")
            page.wait_for_timeout(280)
    except Exception:
        pass


def _aggressive_dismiss_password_save(
    page: Any,
    *,
    timeout_ms: int,
    log: logging.Logger,
) -> None:
    """
    「要保存密码吗？」类条/气泡可能挡在微软卡片上方，导致后续点击落到错误层。
    多轮尝试：has-text 按钮、role、Escape。
    """
    cap = min(5_000, max(1_000, timeout_ms))

    # 纯文本按钮（部分 Chromium 实现非标准 role）
    has_text_buttons = (
        "一律不",
        "Never",
        "不用了",
        "Not now",
        "No thanks",
    )
    role_patterns = (
        re.compile(r"一律不", re.I),
        re.compile(r"Never", re.I),
        re.compile(r"不用了", re.I),
        re.compile(r"No\s+thanks|Not\s+now", re.I),
    )

    for round_i in range(3):
        for tx in has_text_buttons:
            try:
                loc = page.locator(f'button:has-text("{tx}")')
                if loc.count() == 0:
                    continue
                loc.first.click(timeout=cap, force=True)
                log.info(
                    "ms_hold_challenge: dismissed password UI (round=%s, has-text=%s)",
                    round_i + 1,
                    tx,
                )
                page.wait_for_timeout(400)
                return
            except Exception:
                continue

        for pat in role_patterns:
            try:
                btn = page.get_by_role("button", name=pat)
                if btn.count() == 0:
                    continue
                btn.first.click(timeout=cap, force=True)
                log.info(
                    "ms_hold_challenge: dismissed password UI (round=%s, role=%s)",
                    round_i + 1,
                    pat.pattern,
                )
                page.wait_for_timeout(400)
                return
            except Exception:
                continue

        # 两按钮对话框：第二个常为「不保存」
        for sel in ('[role="dialog"]', '[class*="password" i]'):
            try:
                dlg = page.locator(sel).filter(
                    has_text=re.compile(r"保存密码|Save password", re.I)
                )
                if dlg.count() == 0:
                    continue
                btns = dlg.first.locator("button")
                if btns.count() >= 2:
                    btns.nth(1).click(timeout=cap, force=True)
                    log.info(
                        "ms_hold_challenge: dismissed password UI (2nd button in %s)",
                        sel,
                    )
                    page.wait_for_timeout(400)
                    return
            except Exception:
                continue

        _escape_burst(page)
        page.wait_for_timeout(500)

    log.warning(
        "ms_hold_challenge: password-save UI may still be visible (not found in DOM or is native chrome)"
    )


def _accessibility_entry_locators(root: Any) -> list[Any]:
    return [
        root.get_by_role("button", name=re.compile(r"Accessible challenge", re.I)),
        root.get_by_role("button", name=re.compile(r"accessible", re.I)),
        root.locator('[aria-label*="Accessible challenge" i]'),
        root.locator('[aria-label*="Accessible" i]'),
        root.locator('[title*="Accessible challenge" i]'),
        root.locator('[title*="Accessible" i]'),
        root.locator('button[aria-label*="accessibility" i]'),
        root.locator("button").filter(has_text=re.compile(r"accessible|无障碍", re.I)),
    ]


def _press_hold_button_locators(root: Any) -> list[Any]:
    return [
        root.get_by_role("button", name=re.compile(r"press\s+and\s+hold", re.I)),
        root.locator("button").filter(has_text=re.compile(r"press\s+and\s+hold", re.I)),
        root.get_by_role("button", name=re.compile(r"按住|长按", re.I)),
    ]


def _click_locator_first(
    loc: Any,
    *,
    timeout_ms: int,
    delay_ms: int | None = None,
    force: bool = False,
) -> bool:
    try:
        el = loc.first
        el.wait_for(state="visible", timeout=min(12_000, timeout_ms))
        if delay_ms is not None:
            el.click(delay=delay_ms, timeout=timeout_ms, force=force)
        else:
            el.click(timeout=timeout_ms, force=force)
        return True
    except Exception:
        return False


def try_ms_accessible_hold_challenge(
    page: Any,
    *,
    enabled: bool,
    form_step_timeout_ms: int,
    after_accessible_wait_ms: int,
    hold_press_ms: int,
    chrome_password_prompt: str,
    screenshots_dir: Path,
) -> StepResult:
    """
    若当前为微软「Press and hold」类验证：先尽量关掉「保存密码」遮挡，再在主页面或 iframe 内点小人文、长按。
    """

    log = logging.getLogger(__name__)
    step = "ms_hold_challenge"

    if not enabled:
        return step_result(
            success=True,
            step=step,
            message="未启用人机验证自动化（PHASE2_TRY_HOLD_CHALLENGE）",
            data={"skipped": True},
            error=None,
            screenshot_path=None,
        )

    found = _find_challenge_root(page)
    if found is None:
        return step_result(
            success=True,
            step=step,
            message="当前页面未识别为 Press-and-hold 人机验证，已跳过",
            data={"skipped": True},
            error=None,
            screenshot_path=None,
        )
    root, root_kind = found

    t = max(2_000, min(form_step_timeout_ms, 60_000))
    hold_ms = max(1_500, min(hold_press_ms, 25_000))
    wait_after = max(0, min(after_accessible_wait_ms, 60_000))

    try:
        # 先关密码条（始终在 Page 上找；该条多挂在顶层文档）
        mode = chrome_password_prompt if chrome_password_prompt in {"save", "dismiss"} else "dismiss"
        _try_chrome_password_prompt(page, mode, timeout_ms=t, log=log)
        _aggressive_dismiss_password_save(page, timeout_ms=t, log=log)

        clicked_access = False
        for loc in _accessibility_entry_locators(root):
            if _click_locator_first(loc, timeout_ms=t, force=False):
                clicked_access = True
                log.info("ms_hold_challenge: clicked accessibility entry (root=%s)", root_kind)
                break
        if not clicked_access:
            for loc in _accessibility_entry_locators(root):
                if _click_locator_first(loc, timeout_ms=t, force=True):
                    clicked_access = True
                    log.info(
                        "ms_hold_challenge: clicked accessibility entry (force, root=%s)",
                        root_kind,
                    )
                    break

        if not clicked_access:
            log.warning(
                "ms_hold_challenge: accessibility control not found (root=%s), try hold only",
                root_kind,
            )

        if wait_after > 0:
            page.wait_for_timeout(wait_after)

        hold_ok = False
        for loc in _press_hold_button_locators(root):
            if _click_locator_first(loc, timeout_ms=t, delay_ms=hold_ms, force=False):
                hold_ok = True
                log.info("ms_hold_challenge: press-and-hold (root=%s, delay_ms=%s)", root_kind, hold_ms)
                break
        if not hold_ok:
            for loc in _press_hold_button_locators(root):
                if _click_locator_first(loc, timeout_ms=t, delay_ms=hold_ms, force=True):
                    hold_ok = True
                    log.info(
                        "ms_hold_challenge: press-and-hold force (root=%s, delay_ms=%s)",
                        root_kind,
                        hold_ms,
                    )
                    break

        if not hold_ok:
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="人机验证：未找到或未命中「Press and hold」按钮（若存在「保存密码」遮挡，请设 PHASE2_CHROME_PASSWORD_PROMPT=dismiss 或关闭浏览器密码保存）",
                data={
                    "hold_press_ms": hold_ms,
                    "after_accessible_wait_ms": wait_after,
                    "challenge_root": root_kind,
                },
                error="PressHoldButtonNotFound",
                screenshot_path=shot,
            )

        return step_result(
            success=True,
            step=step,
            message="人机验证：已尝试无障碍入口与长按提交",
            data={
                "skipped": False,
                "accessibility_clicked": clicked_access,
                "hold_press_ms": hold_ms,
                "after_accessible_wait_ms": wait_after,
                "challenge_root": root_kind,
            },
            error=None,
            screenshot_path=None,
        )
    except Exception as exc:
        shot = _try_screenshot(page, screenshots_dir, step)
        return step_result(
            success=False,
            step=step,
            message="人机验证步骤异常",
            data={},
            error=f"{type(exc).__name__}: {exc}",
            screenshot_path=shot,
        )
