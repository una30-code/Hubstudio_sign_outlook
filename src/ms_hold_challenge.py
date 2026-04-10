"""Microsoft 注册流中「无障碍挑战 + Press and hold」可选自动化。"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    from apply_signup_profile import _try_chrome_password_prompt
    from step_result import StepResult, step_result
else:
    from .apply_signup_profile import _try_chrome_password_prompt
    from .step_result import StepResult, step_result


def _ms_since(t0: float) -> tuple[int, float]:
    t1 = time.perf_counter()
    return int((t1 - t0) * 1000), t1


def _log_timing_segment(log: logging.Logger, segment: str, elapsed_ms: int) -> None:
    log.info("[MS_HOLD] stage=timing segment=%s elapsed_ms=%s", segment, elapsed_ms)


def _try_screenshot(page: Any, screenshots_dir: Path, filename_prefix: str) -> str | None:
    try:
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        path = screenshots_dir / f"{filename_prefix}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)
    except Exception:
        return None


def _try_screenshot_timestamped(page: Any, screenshots_dir: Path, base_name: str) -> str | None:
    """带 UTC 时间戳的文件名，避免多次跳过时互相覆盖。"""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return _try_screenshot(page, screenshots_dir, f"{base_name}_{stamp}")


def _text_indicates_hold_challenge(text_lower: str) -> bool:
    """与主文档、iframe 内正文共用的人机页特征（小写文本）。"""
    if "press and hold" in text_lower:
        return True
    if "let's prove" in text_lower or "lets prove" in text_lower:
        return True
    if "prove you're human" in text_lower or "prove you’re human" in text_lower:
        return True
    if "prove you" in text_lower or "prove you're" in text_lower:
        return True
    if "按住" in text_lower or "长按" in text_lower:
        return True
    return False


def _body_text_lower(root: Any, *, timeout_ms: int) -> str:
    try:
        return root.locator("body").inner_text(timeout=timeout_ms).lower()
    except Exception:
        return ""


def _page_looks_like_press_hold_challenge(page: Any) -> bool:
    t = _body_text_lower(page, timeout_ms=3_000)
    return _text_indicates_hold_challenge(t)


def _frame_url_safe(fr: Any) -> str:
    try:
        return fr.url or ""
    except Exception:
        return ""


def _is_main_frame(page: Any, fr: Any) -> bool:
    try:
        mf = page.main_frame
        return mf is not None and fr == mf
    except Exception:
        return False


def _human_challenge_detected_anywhere(page: Any) -> bool:
    """prep 轮询用：任一文本人机特征或已出现 hsprotect 挑战 iframe 即视为「人机流程已开始」。"""
    if _page_looks_like_press_hold_challenge(page):
        return True
    for fr in page.frames:
        if _is_main_frame(page, fr):
            continue
        if "hsprotect" in _frame_url_safe(fr).lower():
            return True
        if _text_indicates_hold_challenge(_body_text_lower(fr, timeout_ms=2_500)):
            return True
    return False


def _ordered_challenge_roots(page: Any) -> list[tuple[Any, str]]:
    """
    交互用 root 候选顺序（路线 A）：
    - hsprotect 相关 frame **逆序**（子 frame 常在 `page.frames` 中靠后，内层挑战页优先）
    - 其余含人机正文的 iframe 逆序
    - 最后主文档（避免主页面仅有说明文字却抢先于真实挑战 iframe）
    """
    non_main: list[Any] = []
    for fr in page.frames:
        if _is_main_frame(page, fr):
            continue
        non_main.append(fr)

    tier_a = [f for f in non_main if "hsprotect" in _frame_url_safe(f).lower()]
    tier_a_rev = list(reversed(tier_a))

    seen_ids = {id(f) for f in tier_a}
    tier_b: list[Any] = []
    for f in non_main:
        if id(f) in seen_ids:
            continue
        if _text_indicates_hold_challenge(_body_text_lower(f, timeout_ms=2_500)):
            tier_b.append(f)
            seen_ids.add(id(f))
    # 主文档已像人机页但子 frame 尚未读出正文时，仍把同源 srcdoc 等挑战 iframe 排在 main 之前
    if _page_looks_like_press_hold_challenge(page):
        for f in non_main:
            if id(f) in seen_ids:
                continue
            u = _frame_url_safe(f).lower()
            if "about:srcdoc" in u or u.startswith("data:"):
                tier_b.append(f)
                seen_ids.add(id(f))
        # 仅一个子 frame 时（常见单验证码 iframe），即使 url 尚未变为 about:srcdoc 也优先于 main
        if len(non_main) == 1:
            f0 = non_main[0]
            if id(f0) not in seen_ids:
                tier_b.append(f0)
                seen_ids.add(id(f0))

    tier_b_rev = list(reversed(tier_b))

    out: list[tuple[Any, str]] = []
    for f in tier_a_rev:
        out.append((f, "iframe_hsprotect"))
    for f in tier_b_rev:
        out.append((f, "iframe"))
    if _page_looks_like_press_hold_challenge(page):
        out.append((page, "main"))
    return out


def _root_has_actionable_challenge(root: Any, *, timeout_ms: int) -> bool:
    locs = _accessibility_entry_locators(root) + _press_hold_button_locators(root)
    return _locator_list_any_visible(locs, timeout_ms=timeout_ms)


def _find_challenge_root(
    page: Any,
    *,
    actionable_timeout_ms: int = 2_500,
    list_visible_timeout_ms: int | None = None,
) -> tuple[Any, str] | None:
    """
    选择将要点击的 document（Page 或 Frame）：
    1) 按 _ordered_challenge_roots 顺序，找「无障碍或 Press and hold 任一可见」的 root；
    2) 否则回退到同顺序下「hsprotect URL 或正文仍像人机」的第一个 root。
    """
    ordered = _ordered_challenge_roots(page)
    if not ordered:
        return None

    list_cap = (
        list_visible_timeout_ms
        if list_visible_timeout_ms is not None
        else max(500, min(3_000, actionable_timeout_ms))
    )
    list_cap = max(400, min(8_000, list_cap))
    for root, kind in ordered:
        if _root_has_actionable_challenge(root, timeout_ms=list_cap):
            return root, kind

    for root, kind in ordered:
        if kind == "main":
            if _page_looks_like_press_hold_challenge(page):
                return root, kind
        else:
            u = _frame_url_safe(root).lower()
            if "hsprotect" in u:
                return root, kind
            if _text_indicates_hold_challenge(_body_text_lower(root, timeout_ms=2_500)):
                return root, kind
    return None


def _debug_challenge_frame_hints(page: Any) -> dict[str, Any]:
    """失败时脱敏摘要（无完整 query，避免 session 泄漏）。"""
    hs_bases: list[str] = []
    for fr in page.frames:
        u = _frame_url_safe(fr)
        if "hsprotect" not in u.lower():
            continue
        base = u.split("?", 1)[0]
        if len(base) > 96:
            base = base[:96] + "…"
        hs_bases.append(base)
    return {
        "frame_count": len(page.frames),
        "hsprotect_frame_count": len(hs_bases),
        "hsprotect_url_bases": hs_bases[:6],
    }


def _prep_wait_for_human_challenge_page(
    page: Any,
    *,
    short_sleep_ms: int,
    max_poll_ms: int,
    log: logging.Logger,
) -> None:
    """
    填表刚结束时人机卡片可能尚未渲染：先短睡再轮询，最多消耗 max_poll_ms 毫秒（不含短睡）。
    """
    if short_sleep_ms > 0:
        log.info("[MS_HOLD] stage=prep action=sleep_ms value=%s", short_sleep_ms)
        page.wait_for_timeout(short_sleep_ms)
    if max_poll_ms <= 0:
        return
    interval = 400
    elapsed = 0
    while elapsed < max_poll_ms:
        if _human_challenge_detected_anywhere(page):
            log.info(
                "[MS_HOLD] stage=prep result=detected poll_elapsed_ms=%s",
                elapsed,
            )
            return
        step = min(interval, max_poll_ms - elapsed)
        page.wait_for_timeout(step)
        elapsed += step


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
        "不保存",
        "否",
        "跳过",
        "以后再说",
        "稍后",
        "Skip",
    )
    role_patterns = (
        re.compile(r"一律不", re.I),
        re.compile(r"Never", re.I),
        re.compile(r"不用了", re.I),
        re.compile(r"No\s+thanks|Not\s+now", re.I),
        re.compile(r"不保存|跳过|以后再说|稍后", re.I),
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
        "[MS_HOLD] stage=password result=uncertain reason=not_in_dom_or_native_chrome"
    )


def _accessibility_entry_locators(root: Any) -> list[Any]:
    """与 hsprotect 内页一致：优先精确匹配 `a[aria-label=Accessible challenge]`，宽泛规则置后。"""
    return [
        root.locator('a[role="button"][aria-label="Accessible challenge"]'),
        root.get_by_role("button", name=re.compile(r"^Accessible challenge$", re.I)),
        root.locator('a[role="button"][aria-label*="Accessible challenge" i]'),
        root.locator('[aria-label*="Accessible challenge" i]'),
        root.get_by_role("button", name=re.compile(r"Accessible challenge", re.I)),
        root.locator('a[role="button"][aria-label*="Accessible" i]'),
        root.locator('[aria-label*="Accessible" i]'),
        root.locator('[title*="Accessible challenge" i]'),
        root.locator('[title*="Accessible" i]'),
        root.locator('button[aria-label*="accessibility" i]'),
        root.locator("button").filter(has_text=re.compile(r"accessible|无障碍", re.I)),
        root.get_by_role("button", name=re.compile(r"\baccessible\b", re.I)),
    ]


_HOLD_LABEL_RE = re.compile(r"press\s+(&|and)\s*hold", re.I)
# 外层 div role=button aria-label="Press & Hold Human Challenge"；勿用 `.?` 只匹配一字节，否则漏掉「Press and hold」
_PRESS_HOLD_WIDGET_RE = re.compile(
    r"Press\s+(&|and)\s*hold|Press\s*[&＆]\s*Hold|Hold\s+Human\s+Challenge",
    re.I,
)


def _press_hold_button_locators(root: Any) -> list[Any]:
    """含 Press & Hold Human Challenge 整块按钮、<p>Press and hold</p> 等。"""
    return [
        root.get_by_role("button", name=_PRESS_HOLD_WIDGET_RE),
        root.locator('[role="button"][aria-label*="Hold Human Challenge"]'),
        root.get_by_role("button", name=_HOLD_LABEL_RE),
        root.get_by_role("button", name=re.compile(r"press\s+and\s+hold", re.I)),
        root.locator("button").filter(has_text=_HOLD_LABEL_RE),
        root.locator('[role="button"]').filter(has_text=_HOLD_LABEL_RE),
        root.get_by_text(_HOLD_LABEL_RE),
        root.locator("p").filter(has_text=_HOLD_LABEL_RE),
        root.get_by_role("button", name=re.compile(r"按住|长按", re.I)),
    ]


def _locator_list_any_visible(locators: list[Any], *, timeout_ms: int) -> bool:
    cap = max(500, min(3_000, timeout_ms))
    for loc in locators:
        try:
            loc.first.wait_for(state="visible", timeout=cap)
            return True
        except Exception:
            continue
    return False


def _warmup_viewport_click(page: Any, *, settle_ms: int, log: logging.Logger) -> None:
    """
    人机子流程前在**顶层 Page 视口**做一次轻点（不切换 frame），模拟「先点页面再找控件」。
    坐标取视口左下偏上，降低点到「保存密码」类条（多在右上）的概率；失败则忽略。
    """
    try:
        vp = page.viewport_size
        if vp and vp.get("width") and vp.get("height"):
            w, h = int(vp["width"]), int(vp["height"])
            x = max(16, min(w - 16, w // 6))
            y = max(16, min(h - 16, int(h * 0.72)))
        else:
            x, y = 80, 520
        page.mouse.click(x, y)
        log.info("[MS_HOLD] stage=warmup result=viewport_click x=%s y=%s", x, y)
    except Exception as exc:
        log.debug("warmup viewport click skipped: %s", exc)
    sm = max(0, min(2_000, settle_ms))
    if sm:
        page.wait_for_timeout(sm)


def _click_locator_first(
    loc: Any,
    *,
    timeout_ms: int,
    delay_ms: int | None = None,
    force: bool = False,
    visibility_timeout_ms: int | None = None,
) -> tuple[bool, bool]:
    """返回 (是否点击成功, 本次是否使用 force 参数)。

    visibility_timeout_ms：仅用于 wait_for(visible) 的探测上限；点击仍使用 timeout_ms。
    """
    try:
        el = loc.first
        if visibility_timeout_ms is not None:
            vis_cap = max(400, min(visibility_timeout_ms, timeout_ms))
        else:
            vis_cap = min(12_000, timeout_ms)
        el.wait_for(state="visible", timeout=vis_cap)
        if delay_ms is not None:
            el.click(delay=delay_ms, timeout=timeout_ms, force=force)
        else:
            el.click(timeout=timeout_ms, force=force)
        return True, force
    except Exception:
        return False, force


def try_ms_accessible_hold_challenge(
    page: Any,
    *,
    enabled: bool,
    form_step_timeout_ms: int,
    after_accessible_wait_ms: int,
    hold_press_ms: int,
    chrome_password_prompt: str,
    screenshots_dir: Path,
    refind_challenge_root_before_hold: bool = True,
    prep_short_sleep_ms: int = 2_000,
    prep_poll_ms: int = 30_000,
    warmup_viewport_click: bool = True,
    warmup_settle_ms: int = 280,
    locator_probe_timeout_ms: int = 2_000,
) -> StepResult:
    """
    若当前为微软「Press and hold」类验证：先尽量关掉「保存密码」遮挡，再在主页面或 iframe 内点小人文、长按。
    填表结束后可先短睡再轮询等人机页出现（prep_short_sleep_ms / prep_poll_ms）。
    进入本步且关完密码条后，默认在顶层视口做一次轻点（warmup_viewport_click）再点小人文。
    locator_probe_timeout_ms：各候选 locator 的 wait_for(visible) 上限；点击仍使用 form_step_timeout_ms。
    """

    log = logging.getLogger(__name__)
    step = "ms_hold_challenge"

    if not enabled:
        return step_result(
            success=True,
            step=step,
            message="已关闭人机验证自动化（设置 PHASE2_TRY_HOLD_CHALLENGE=0/false/off 可保持关闭；默认未设置时为开启）",
            data={"skipped": True, "skip_reason": "disabled"},
            error=None,
            screenshot_path=None,
        )

    probe_v = max(400, min(8_000, locator_probe_timeout_ms))
    timing_ms: dict[str, int] = {}
    t_mark = time.perf_counter()

    _prep_wait_for_human_challenge_page(
        page,
        short_sleep_ms=prep_short_sleep_ms,
        max_poll_ms=prep_poll_ms,
        log=log,
    )
    prep_elapsed, t_mark = _ms_since(t_mark)
    timing_ms["prep_ms"] = prep_elapsed
    _log_timing_segment(log, "prep", prep_elapsed)

    found = _find_challenge_root(page, list_visible_timeout_ms=probe_v)
    resolve_elapsed, t_mark = _ms_since(t_mark)
    timing_ms["resolve_root_ms"] = resolve_elapsed
    _log_timing_segment(log, "resolve_root", resolve_elapsed)

    if found is None:
        shot = _try_screenshot_timestamped(
            page, screenshots_dir, "ms_hold_challenge_skipped"
        )
        url_snap = ""
        try:
            url_snap = page.url
        except Exception:
            pass
        return step_result(
            success=True,
            step=step,
            message="人机验证：短暂等待与轮询后仍未识别到人机页（页面可能仍在加载或文案已改版），已跳过",
            data={
                "skipped": True,
                "skip_reason": "not_detected_after_wait",
                "prep_short_sleep_ms": prep_short_sleep_ms,
                "prep_poll_ms": prep_poll_ms,
                "page_url": url_snap,
                "timing_ms": timing_ms,
            },
            error=None,
            screenshot_path=shot,
        )
    root, root_kind = found
    log.info("[MS_HOLD] stage=resolve_root kind=%s", root_kind)

    t = max(2_000, min(form_step_timeout_ms, 60_000))
    hold_ms = max(1_500, min(hold_press_ms, 25_000))
    wait_after = max(0, min(after_accessible_wait_ms, 60_000))

    try:
        # 先关密码条（始终在 Page 上找；该条多挂在顶层文档）
        mode = chrome_password_prompt if chrome_password_prompt in {"save", "dismiss"} else "dismiss"
        _try_chrome_password_prompt(page, mode, timeout_ms=t, log=log)
        _aggressive_dismiss_password_save(page, timeout_ms=t, log=log)
        pwd_elapsed, t_mark = _ms_since(t_mark)
        timing_ms["password_dismiss_ms"] = pwd_elapsed
        _log_timing_segment(log, "password_dismiss", pwd_elapsed)

        if warmup_viewport_click:
            _warmup_viewport_click(page, settle_ms=warmup_settle_ms, log=log)
        warm_elapsed, t_mark = _ms_since(t_mark)
        timing_ms["warmup_ms"] = warm_elapsed
        _log_timing_segment(log, "warmup", warm_elapsed)

        clicked_access = False
        access_used_force = False
        t_acc = time.perf_counter()
        for loc in _accessibility_entry_locators(root):
            ok, used_f = _click_locator_first(
                loc,
                timeout_ms=t,
                force=False,
                visibility_timeout_ms=probe_v,
            )
            if ok:
                clicked_access = True
                access_used_force = used_f
                log.info("[MS_HOLD] stage=accessibility result=clicked root=%s", root_kind)
                break
        if not clicked_access:
            for loc in _accessibility_entry_locators(root):
                ok, used_f = _click_locator_first(
                    loc,
                    timeout_ms=t,
                    force=True,
                    visibility_timeout_ms=probe_v,
                )
                if ok:
                    clicked_access = True
                    access_used_force = used_f
                    log.info(
                        "[MS_HOLD] stage=accessibility result=clicked_force root=%s",
                        root_kind,
                    )
                    break
        acc_elapsed, t_mark = _ms_since(t_acc)
        timing_ms["accessibility_ms"] = acc_elapsed
        _log_timing_segment(log, "accessibility", acc_elapsed)

        if not clicked_access:
            log.warning(
                "[MS_HOLD] stage=accessibility result=skip reason=no_control root=%s",
                root_kind,
            )

        t_wa = time.perf_counter()
        if wait_after > 0:
            page.wait_for_timeout(wait_after)
        wa_elapsed, t_mark = _ms_since(t_wa)
        timing_ms["wait_after_accessible_ms"] = wa_elapsed
        _log_timing_segment(log, "wait_after_accessible", wa_elapsed)

        t_ref = time.perf_counter()
        if refind_challenge_root_before_hold:
            found2 = _find_challenge_root(page, list_visible_timeout_ms=probe_v)
            if found2 is not None:
                new_root, new_kind = found2
                # 主文档常残留「证明你是人类」类文案，refind 勿把已锁定的挑战 iframe 降回 main
                if root_kind in ("iframe", "iframe_hsprotect") and new_kind == "main":
                    log.info(
                        "[MS_HOLD] stage=refind result=keep kind=%s (skip main)",
                        root_kind,
                    )
                else:
                    root, root_kind = new_root, new_kind
        ref_elapsed, t_mark = _ms_since(t_ref)
        timing_ms["refind_ms"] = ref_elapsed
        _log_timing_segment(log, "refind", ref_elapsed)

        hold_ok = False
        hold_used_force = False
        t_hold = time.perf_counter()
        for loc in _press_hold_button_locators(root):
            ok, used_f = _click_locator_first(
                loc,
                timeout_ms=t,
                delay_ms=hold_ms,
                force=False,
                visibility_timeout_ms=probe_v,
            )
            if ok:
                hold_ok = True
                hold_used_force = used_f
                log.info(
                    "[MS_HOLD] stage=hold result=clicked root=%s delay_ms=%s",
                    root_kind,
                    hold_ms,
                )
                break
        if not hold_ok:
            for loc in _press_hold_button_locators(root):
                ok, used_f = _click_locator_first(
                    loc,
                    timeout_ms=t,
                    delay_ms=hold_ms,
                    force=True,
                    visibility_timeout_ms=probe_v,
                )
                if ok:
                    hold_ok = True
                    hold_used_force = used_f
                    log.info(
                        "[MS_HOLD] stage=hold result=clicked_force root=%s delay_ms=%s",
                        root_kind,
                        hold_ms,
                    )
                    break
        hold_elapsed, t_mark = _ms_since(t_hold)
        timing_ms["hold_ms"] = hold_elapsed
        _log_timing_segment(log, "hold", hold_elapsed)

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
                    "accessibility_used_force": access_used_force,
                    "timing_ms": timing_ms,
                    "locator_probe_timeout_ms": probe_v,
                    **_debug_challenge_frame_hints(page),
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
                "warmup_viewport_click": warmup_viewport_click,
                "accessibility_clicked": clicked_access,
                "accessibility_used_force": access_used_force,
                "hold_used_force": hold_used_force,
                "hold_press_ms": hold_ms,
                "after_accessible_wait_ms": wait_after,
                "challenge_root": root_kind,
                "timing_ms": timing_ms,
                "locator_probe_timeout_ms": probe_v,
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
            data={"timing_ms": timing_ms, "locator_probe_timeout_ms": probe_v},
            error=f"{type(exc).__name__}: {exc}",
            screenshot_path=shot,
        )


def click_ms_challenge_accessibility_only(
    page: Any,
    *,
    form_step_timeout_ms: int,
    chrome_password_prompt: str,
    screenshots_dir: Path,
    noop_if_accessibility_missing: bool = False,
    locator_probe_timeout_ms: int = 2_000,
) -> StepResult:
    """仅点击「无障碍 / Accessible challenge」入口（分步脚本；不执行长按）。"""

    log = logging.getLogger(__name__)
    step = "ms_hold_step_accessibility"
    probe_v = max(400, min(8_000, locator_probe_timeout_ms))

    found = _find_challenge_root(page, list_visible_timeout_ms=probe_v)
    if found is None:
        return step_result(
            success=False,
            step=step,
            message="未识别为人机验证页，未点击无障碍按钮",
            data={},
            error="ChallengeRootNotFound",
            screenshot_path=_try_screenshot(page, screenshots_dir, step),
        )
    root, root_kind = found
    t = max(2_000, min(form_step_timeout_ms, 60_000))

    try:
        mode = chrome_password_prompt if chrome_password_prompt in {"save", "dismiss"} else "dismiss"
        _try_chrome_password_prompt(page, mode, timeout_ms=t, log=log)
        _aggressive_dismiss_password_save(page, timeout_ms=t, log=log)

        if noop_if_accessibility_missing:
            acc_vis = _locator_list_any_visible(
                _accessibility_entry_locators(root), timeout_ms=probe_v
            )
            hold_vis = _locator_list_any_visible(
                _press_hold_button_locators(root), timeout_ms=probe_v
            )
            if not acc_vis and hold_vis:
                log.info(
                    "ms_hold_step_accessibility: noop (no accessibility control, root=%s)",
                    root_kind,
                )
                return step_result(
                    success=True,
                    step=step,
                    message="无障碍入口已不可用，跳过点击（幂等）",
                    data={
                        "challenge_root": root_kind,
                        "skipped": True,
                        "noop_accessibility": True,
                    },
                    error=None,
                    screenshot_path=None,
                )

        clicked = False
        used_force = False
        for loc in _accessibility_entry_locators(root):
            ok, used_f = _click_locator_first(
                loc, timeout_ms=t, force=False, visibility_timeout_ms=probe_v
            )
            if ok:
                clicked = True
                used_force = used_f
                log.info("ms_hold_step_accessibility: clicked (root=%s)", root_kind)
                break
        if not clicked:
            for loc in _accessibility_entry_locators(root):
                ok, used_f = _click_locator_first(
                    loc, timeout_ms=t, force=True, visibility_timeout_ms=probe_v
                )
                if ok:
                    clicked = True
                    used_force = used_f
                    log.info("ms_hold_step_accessibility: clicked force (root=%s)", root_kind)
                    break

        if not clicked:
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="未找到或未命中无障碍入口按钮",
                data={"challenge_root": root_kind},
                error="AccessibilityButtonNotFound",
                screenshot_path=shot,
            )

        return step_result(
            success=True,
            step=step,
            message="已点击无障碍入口",
            data={
                "challenge_root": root_kind,
                "accessibility_used_force": used_force,
            },
            error=None,
            screenshot_path=None,
        )
    except Exception as exc:
        shot = _try_screenshot(page, screenshots_dir, step)
        return step_result(
            success=False,
            step=step,
            message="无障碍点击步骤异常",
            data={},
            error=f"{type(exc).__name__}: {exc}",
            screenshot_path=shot,
        )


def press_ms_challenge_hold_only(
    page: Any,
    *,
    form_step_timeout_ms: int,
    hold_press_ms: int,
    chrome_password_prompt: str,
    screenshots_dir: Path,
    refind_root_before_press: bool = True,
    locator_probe_timeout_ms: int = 2_000,
) -> StepResult:
    """仅对「Press and hold」主按钮执行长按点击（分步脚本）。"""

    log = logging.getLogger(__name__)
    step = "ms_hold_step_press"
    probe_v = max(400, min(8_000, locator_probe_timeout_ms))

    found = _find_challenge_root(page, list_visible_timeout_ms=probe_v)
    if found is None:
        return step_result(
            success=False,
            step=step,
            message="未识别为人机验证页，未执行长按",
            data={},
            error="ChallengeRootNotFound",
            screenshot_path=_try_screenshot(page, screenshots_dir, step),
        )
    root, root_kind = found
    t = max(2_000, min(form_step_timeout_ms, 60_000))
    hold_ms = max(1_500, min(hold_press_ms, 25_000))

    try:
        mode = chrome_password_prompt if chrome_password_prompt in {"save", "dismiss"} else "dismiss"
        _try_chrome_password_prompt(page, mode, timeout_ms=t, log=log)
        _aggressive_dismiss_password_save(page, timeout_ms=t, log=log)

        if refind_root_before_press:
            found2 = _find_challenge_root(page, list_visible_timeout_ms=probe_v)
            if found2 is not None:
                new_root, new_kind = found2
                if root_kind in ("iframe", "iframe_hsprotect") and new_kind == "main":
                    log.info(
                        "ms_hold_step_press: refind keep iframe kind=%s (skip main)",
                        root_kind,
                    )
                else:
                    root, root_kind = new_root, new_kind

        hold_ok = False
        hold_used_force = False
        for loc in _press_hold_button_locators(root):
            ok, used_f = _click_locator_first(
                loc,
                timeout_ms=t,
                delay_ms=hold_ms,
                force=False,
                visibility_timeout_ms=probe_v,
            )
            if ok:
                hold_ok = True
                hold_used_force = used_f
                log.info(
                    "ms_hold_step_press: press-and-hold (root=%s, delay_ms=%s)",
                    root_kind,
                    hold_ms,
                )
                break
        if not hold_ok:
            for loc in _press_hold_button_locators(root):
                ok, used_f = _click_locator_first(
                    loc,
                    timeout_ms=t,
                    delay_ms=hold_ms,
                    force=True,
                    visibility_timeout_ms=probe_v,
                )
                if ok:
                    hold_ok = True
                    hold_used_force = used_f
                    log.info(
                        "ms_hold_step_press: press-and-hold force (root=%s, delay_ms=%s)",
                        root_kind,
                        hold_ms,
                    )
                    break

        if not hold_ok:
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="未找到或未命中 Press and hold 按钮",
                data={
                    "hold_press_ms": hold_ms,
                    "challenge_root": root_kind,
                    "locator_probe_timeout_ms": probe_v,
                },
                error="PressHoldButtonNotFound",
                screenshot_path=shot,
            )

        return step_result(
            success=True,
            step=step,
            message="已对 Press and hold 执行长按点击",
            data={
                "hold_press_ms": hold_ms,
                "challenge_root": root_kind,
                "hold_used_force": hold_used_force,
            },
            error=None,
            screenshot_path=None,
        )
    except Exception as exc:
        shot = _try_screenshot(page, screenshots_dir, step)
        return step_result(
            success=False,
            step=step,
            message="长按步骤异常",
            data={},
            error=f"{type(exc).__name__}: {exc}",
            screenshot_path=shot,
        )


def wait_ms_challenge_step03(
    page: Any,
    *,
    mode: str,
    sleep_ms: int,
    until_press_timeout_ms: int,
    form_step_timeout_ms: int,
    screenshots_dir: Path,
    locator_probe_timeout_ms: int = 2_000,
) -> StepResult:
    """
    分步脚本 Step03：sleep 固定毫秒，或轮询直到「Press and hold」在挑战根内可见。
    mode: \"sleep\" | \"until_press\"
    """

    log = logging.getLogger(__name__)
    step = "ms_hold_step_wait"
    mode_n = (mode or "sleep").strip().lower().replace("-", "_")
    t = max(2_000, min(form_step_timeout_ms, 60_000))
    probe_v = max(400, min(8_000, locator_probe_timeout_ms))

    try:
        if mode_n == "until_press":
            cap = max(1_000, min(until_press_timeout_ms, 120_000))
            poll = 400
            elapsed = 0
            press_visible = False
            root_kind: str | None = None
            while elapsed < cap:
                found = _find_challenge_root(page, list_visible_timeout_ms=probe_v)
                if found is not None:
                    root, root_kind = found
                    if _locator_list_any_visible(
                        _press_hold_button_locators(root), timeout_ms=probe_v
                    ):
                        press_visible = True
                        break
                page.wait_for_timeout(poll)
                elapsed += poll
            if not press_visible:
                log.warning(
                    "ms_hold_step_wait: until_press 超时 (%sms, challenge_root=%s)",
                    cap,
                    root_kind,
                )
            data: dict[str, Any] = {
                "mode": "until_press",
                "elapsed_ms": elapsed,
                "press_visible": press_visible,
                "challenge_root": root_kind,
            }
        else:
            sm = max(0, sleep_ms)
            page.wait_for_timeout(sm)
            data = {"mode": "sleep", "sleep_ms": sm}

        screenshots_dir.mkdir(parents=True, exist_ok=True)
        path = screenshots_dir / f"{step}.png"
        page.screenshot(path=str(path), full_page=True)
        return step_result(
            success=True,
            step=step,
            message="等待步骤完成并已截图",
            data={**data, "screenshot_path": str(path)},
            error=None,
            screenshot_path=str(path),
        )
    except Exception as exc:
        shot = _try_screenshot(page, screenshots_dir, step)
        return step_result(
            success=False,
            step=step,
            message="等待步骤异常",
            data={},
            error=f"{type(exc).__name__}: {exc}",
            screenshot_path=shot,
        )
