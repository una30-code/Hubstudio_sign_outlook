"""Phase-2：将 phase-1 用户信息填入 Outlook 注册流（邮箱→密码→人物信息→提交）。"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    from step_result import StepResult, step_result
else:
    from .step_result import StepResult, step_result

_MONTHS_EN = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _month_option_texts(m: int) -> tuple[str, ...]:
    """英文注册页：January / 缩写 / 数字（与 phase-1 birth_date 月一致）。"""
    en = _MONTHS_EN[m - 1]
    return (
        en,
        en[:3],
        str(m),
        f"{m:02d}",
    )


def _day_option_texts(d: int) -> tuple[str, ...]:
    return (str(d), f"{d:02d}")


def _try_screenshot(page: Any, screenshots_dir: Path, filename_prefix: str) -> str | None:
    try:
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        path = screenshots_dir / f"{filename_prefix}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)
    except Exception:
        return None


def _parse_birth_ymd(raw: str) -> tuple[int, int, int] | None:
    raw = raw.strip()
    if not raw:
        return None
    parts = raw.split("-")
    if len(parts) != 3:
        return None
    try:
        y, mo, da = int(parts[0]), int(parts[1]), int(parts[2])
        if not (1 <= mo <= 12 and 1 <= da <= 31 and 1900 <= y <= 2100):
            return None
        return y, mo, da
    except ValueError:
        return None


def _nav_settle(page: Any, timeout_ms: int) -> None:
    try:
        page.wait_for_load_state("domcontentloaded", timeout=min(5_000, timeout_ms))
    except Exception:
        pass


def _step_pause(page: Any, delay_ms: int) -> None:
    # 主步骤之间的固定间隔，缓和与页面的竞态（delay_ms 来自配置，0 则跳过）
    if delay_ms <= 0:
        return
    try:
        page.wait_for_timeout(delay_ms)
    except Exception:
        pass


def _try_chrome_password_prompt_keyboard_primary(page: Any, log: logging.Logger) -> None:
    # 原生「要更新密码吗？」对话框焦点常在蓝色主按钮上；DOM 不可见时回车一次作补偿（也可能 noop）
    try:
        page.wait_for_timeout(350)
        page.keyboard.press("Enter")
        log.info(
            "apply_signup_profile: keyboard Enter after password (guess: chrome prompt primary)"
        )
    except Exception:
        pass


def _try_chrome_password_prompt(
    page: Any,
    mode: str,
    *,
    timeout_ms: int,
    log: logging.Logger,
) -> None:
    """
    Chromium 系在密码步后可能弹出密码保存 UI。
    优先用页面内 button/role 命中；未命中且 mode=save 时再发送 Enter（部分环境下焦点在主按钮）。
    """
    if mode == "skip":
        return
    if mode not in {"save", "dismiss"}:
        return
    cap = min(4_000, max(1_000, timeout_ms))
    if mode == "save":
        patterns = (
            re.compile(r"更新密码|保存密码", re.I),
            re.compile(r"Save\s+password|Update\s+password", re.I),
        )
    else:
        patterns = (
            re.compile(r"一律不", re.I),
            re.compile(r"不用了", re.I),
            re.compile(r"Never|No\s+thanks|Not\s+now", re.I),
        )
    handled = False
    for pat in patterns:
        try:
            btn = page.get_by_role("button", name=pat)
            if btn.count() == 0:
                continue
            btn.first.click(timeout=cap)
            log.info("apply_signup_profile: chrome password prompt handled (%s)", mode)
            handled = True
            break
        except Exception:
            continue
    if not handled:
        try:
            for pat in patterns:
                loc = page.locator("button").filter(has_text=pat)
                if loc.count() == 0:
                    continue
                loc.first.click(timeout=cap)
                log.info("apply_signup_profile: chrome password prompt handled (%s)", mode)
                handled = True
                break
        except Exception:
            pass
    if not handled and mode == "save":
        log.debug(
            "apply_signup_profile: chrome password prompt not in DOM, trying keyboard Enter"
        )
        _try_chrome_password_prompt_keyboard_primary(page, log)
    elif not handled:
        log.debug(
            "apply_signup_profile: chrome password prompt not found in page DOM (mode=%s)",
            mode,
        )


def _fill_first_visible(
    page: Any,
    locators: list[Any],
    value: str,
    *,
    timeout_ms: int,
) -> bool:
    for loc in locators:
        try:
            loc.first.wait_for(state="visible", timeout=timeout_ms)
            loc.first.fill(value, timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def _click_first_match(page: Any, locators: list[Any], *, timeout_ms: int) -> bool:
    vis = min(timeout_ms, 8_000)
    for loc in locators:
        try:
            loc.first.wait_for(state="visible", timeout=vis)
            loc.first.click(timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def _select_option_try(locator: Any, *, timeout_ms: int, values: list[str]) -> bool:
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
    except Exception:
        return False
    for v in values:
        try:
            locator.select_option(value=v, timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def _select_option_try_values_or_labels(
    locator: Any, *, timeout_ms: int, values: list[str], labels: list[str]
) -> bool:
    """微软下拉既可能按 value，也可能按可见文案（label）匹配。"""
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
    except Exception:
        return False
    for v in values:
        try:
            locator.select_option(value=v, timeout=timeout_ms)
            return True
        except Exception:
            continue
    for lab in labels:
        try:
            locator.select_option(label=lab, timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def _month_target_locators(scope: Any) -> list[Any]:
    """仅原生 <select>（旧版）；Fluent 为 #BirthMonthDropdown，不走此列表。"""
    return [
        scope.locator("#BirthMonth select").first,
        scope.locator('select[name="BirthMonth" i]').first,
        scope.locator("#BirthMonth").first,
    ]


def _month_fluent_openers(scope: Any) -> tuple[Any, ...]:
    """signup.live.com：Fluent combobox；优先缩在 birthdateControls 内，避免点到其它 combobox 或顶栏。"""
    bc = scope.locator('[data-testid="birthdateControls"]')
    return (
        bc.locator("#BirthMonthDropdown"),
        scope.locator("#BirthMonthDropdown"),
        bc.get_by_role("combobox", name=re.compile(r"birth\s*month", re.I)),
        scope.get_by_role("combobox", name=re.compile(r"birth\s*month", re.I)),
        scope.locator('button[name="BirthMonth"]'),
    )


def _day_target_locators(scope: Any) -> list[Any]:
    return [
        scope.locator("#BirthDay select").first,
        scope.locator('select[name="BirthDay" i]').first,
        scope.locator("#BirthDay").first,
    ]


def _day_fluent_openers(scope: Any) -> tuple[Any, ...]:
    bc = scope.locator('[data-testid="birthdateControls"]')
    return (
        bc.locator("#BirthDayDropdown"),
        scope.locator("#BirthDayDropdown"),
        bc.get_by_role("combobox", name=re.compile(r"birth\s*day", re.I)),
        scope.get_by_role("combobox", name=re.compile(r"birth\s*day", re.I)),
        scope.locator('button[name="BirthDay"]'),
    )


def _year_target_locators(scope: Any) -> list[Any]:
    """Fluent：年份多为 fui-Input 内 `input[name=BirthYear]`，无 #BirthYear 包裹。"""
    return [
        scope.locator('[data-testid="birthdateControls"] input[name="BirthYear" i]').first,
        scope.locator('input[name="BirthYear" i]').first,
        scope.get_by_role("spinbutton", name=re.compile(r"birth\s*year", re.I)).first,
        scope.locator('input[aria-label="Birth year" i]').first,
        scope.locator("#BirthYear input").first,
        scope.locator("#BirthYear").first,
    ]


def _input_value_matches(locator: Any, expected: str, *, timeout_ms: int) -> bool:
    try:
        locator.wait_for(state="visible", timeout=min(3_000, timeout_ms))
        got = locator.input_value(timeout=timeout_ms)
        return got.strip() == expected.strip()
    except Exception:
        return False


def _birth_month_matches_display(scope: Any, m: int, *, timeout_ms: int) -> bool:
    """若能读到已选月份（数字或英文月名），视为无需再选。"""
    month_names = _month_option_texts(m)
    # Fluent：选中项在 button 内 span[data-testid="truncatedSelectedText"]
    bc = scope.locator('[data-testid="birthdateControls"]')
    for loc in (
        bc.locator("#BirthMonthDropdown"),
        scope.locator("#BirthMonthDropdown"),
        bc.get_by_role("combobox", name=re.compile(r"birth\s*month", re.I)),
        scope.get_by_role("combobox", name=re.compile(r"birth\s*month", re.I)),
    ):
        try:
            btn = loc.first
            btn.wait_for(state="visible", timeout=min(2_500, timeout_ms))
            try:
                txt = btn.locator('[data-testid="truncatedSelectedText"]').inner_text(
                    timeout=1_000
                )
            except Exception:
                txt = btn.inner_text(timeout=1_000)
            t_s = (txt or "").strip()
            if not t_s or t_s.lower() == "month":
                try:
                    v_attr = (btn.get_attribute("value") or "").strip()
                    # Fluent combobox value 常为 1–12，与 birth_date 月份一致
                    if v_attr.isdigit() and int(v_attr) == m:
                        return True
                except Exception:
                    pass
                continue
            for cand in month_names:
                if cand.lower() in t_s.lower() or t_s.lower() in cand.lower():
                    return True
            try:
                v_attr = (btn.get_attribute("value") or "").strip()
                if v_attr.isdigit() and int(v_attr) == m:
                    return True
            except Exception:
                pass
        except Exception:
            continue
    for loc in _month_target_locators(scope):
        try:
            loc.wait_for(state="visible", timeout=min(2_000, timeout_ms))
            tag = loc.evaluate("e => e.tagName.toLowerCase()")
        except Exception:
            continue
        if tag == "select":
            try:
                v = loc.evaluate(
                    """el => el.options[el.selectedIndex]?.text?.trim() || el.value"""
                )
                if not v:
                    continue
                v_s = str(v).strip()
                for cand in month_names:
                    if v_s.lower() == cand.lower():
                        return True
            except Exception:
                continue
        else:
            try:
                txt = loc.inner_text(timeout=2_000)
                t_s = (txt or "").strip()
                if not t_s or t_s.lower() == "month":
                    continue
                for cand in month_names:
                    if cand.lower() in t_s.lower() or t_s.lower() in cand.lower():
                        return True
            except Exception:
                continue
    return False


def _birth_day_matches_display(scope: Any, d: int, *, timeout_ms: int) -> bool:
    want_labels = _day_option_texts(d)
    want_norm = {x.lower() for x in want_labels}
    bc = scope.locator('[data-testid="birthdateControls"]')
    for loc in (
        bc.locator("#BirthDayDropdown"),
        scope.locator("#BirthDayDropdown"),
        bc.get_by_role("combobox", name=re.compile(r"birth\s*day", re.I)),
        scope.get_by_role("combobox", name=re.compile(r"birth\s*day", re.I)),
    ):
        try:
            btn = loc.first
            btn.wait_for(state="visible", timeout=min(2_500, timeout_ms))
            try:
                txt = btn.locator('[data-testid="truncatedSelectedText"]').inner_text(
                    timeout=1_000
                )
            except Exception:
                txt = btn.inner_text(timeout=1_000)
            t_s = (txt or "").strip().lower()
            if not t_s or t_s == "day":
                continue
            if t_s in want_norm:
                return True
        except Exception:
            continue
    for loc in _day_target_locators(scope):
        try:
            loc.wait_for(state="visible", timeout=min(2_000, timeout_ms))
            tag = loc.evaluate("e => e.tagName.toLowerCase()")
        except Exception:
            continue
        if tag == "select":
            try:
                v = loc.evaluate(
                    """el => el.options[el.selectedIndex]?.text?.trim() || el.value"""
                )
                vs = str(v).strip()
                if vs in want_labels:
                    return True
            except Exception:
                continue
        else:
            try:
                txt = (loc.inner_text(timeout=2_000) or "").strip()
                if txt in want_labels:
                    return True
            except Exception:
                continue
    return False


def _birth_year_matches_display(scope: Any, y: int, *, timeout_ms: int) -> bool:
    exp = str(y)
    for loc in _year_target_locators(scope):
        if _input_value_matches(loc, exp, timeout_ms=min(timeout_ms, 4_000)):
            return True
    return False


def _wait_for_open_listbox(root: Any, timeout_ms: int) -> bool:
    try:
        root.locator('[role="listbox"]').first.wait_for(
            state="visible", timeout=timeout_ms
        )
        return True
    except Exception:
        return False


def _fluent_listbox_from_combobox(
    scope: Any,
    root: Any,
    combobox_selector: str | tuple[str, ...],
    timeout_ms: int,
) -> Any | None:
    """
    Fluent UI V9：combobox 的 aria-controls 指向 listbox id；列表常 portal 到
    document.body，须在 **Page（root）** 上按 id 查找，仅用 Frame.scope 会找不到。
    """
    selectors: tuple[str, ...] = (
        (combobox_selector,)
        if isinstance(combobox_selector, str)
        else tuple(combobox_selector)
    )
    cap = min(max(timeout_ms, 3_000), 8_000)
    deadline = time.monotonic() + cap / 1000.0
    while time.monotonic() < deadline:
        for sel in selectors:
            btn = scope.locator(sel).first
            try:
                cid = (btn.get_attribute("aria-controls", timeout=800) or "").strip()
            except Exception:
                cid = ""
            if cid:
                lb = root.locator(f'[id="{cid}"]')
                try:
                    lb.wait_for(state="visible", timeout=900)
                    return lb
                except Exception:
                    pass
        try:
            root.wait_for_timeout(200)
        except Exception:
            break
    try:
        lb = root.locator('[id^="fluent-listbox"]').last
        lb.wait_for(state="visible", timeout=min(cap, 5_000))
        return lb
    except Exception:
        pass
    return None


def _click_text_in_fluent_listbox(
    box: Any, texts: tuple[str, ...], *, timeout_ms: int
) -> bool:
    """在已定位的 listbox 内点月份名或日期数字。"""
    for text in texts:
        pat_loose = re.compile(re.escape(text), re.I)
        pat_exact = re.compile(r"^\s*" + re.escape(text) + r"\s*$", re.I)
        candidates = (
            box.locator('[id^="fluent-option"]').filter(has_text=pat_loose).first,
            box.get_by_role("option", name=pat_loose).first,
            box.locator('[id^="fluent-option"]').filter(has_text=pat_exact).first,
            box.get_by_text(text, exact=True).first,
            box.get_by_text(text, exact=False).first,
        )
        for target in candidates:
            try:
                target.click(timeout=timeout_ms)
                return True
            except Exception:
                continue
    return False


def _click_month_in_open_listbox(root: Any, m: int, timeout_ms: int) -> bool:
    """兼容旧路径：任意可见 listbox。"""
    try:
        box = root.locator('[role="listbox"]').first
        box.wait_for(state="visible", timeout=min(2_500, timeout_ms))
        return _click_text_in_fluent_listbox(
            box, _month_option_texts(m), timeout_ms=timeout_ms
        )
    except Exception:
        return False


def _click_month_in_open_listbox_smart(
    scope: Any, root: Any, m: int, timeout_ms: int
) -> bool:
    """优先 BirthMonthDropdown 的 aria-controls，再退 generic listbox。"""
    lb = _fluent_listbox_from_combobox(
        scope,
        root,
        (
            '[data-testid="birthdateControls"] #BirthMonthDropdown',
            "#BirthMonthDropdown",
        ),
        timeout_ms,
    )
    if lb is not None:
        if _click_text_in_fluent_listbox(
            lb, _month_option_texts(m), timeout_ms=timeout_ms
        ):
            return True
    return _click_month_in_open_listbox(root, m, timeout_ms)


def _click_day_in_open_listbox(
    root: Any, labels: tuple[str, ...], timeout_ms: int
) -> bool:
    try:
        box = root.locator('[role="listbox"]').first
        box.wait_for(state="visible", timeout=min(2_500, timeout_ms))
        return _click_text_in_fluent_listbox(box, labels, timeout_ms=timeout_ms)
    except Exception:
        return False


def _click_day_in_open_listbox_smart(
    scope: Any, root: Any, labels: tuple[str, ...], timeout_ms: int
) -> bool:
    lb = _fluent_listbox_from_combobox(
        scope,
        root,
        (
            '[data-testid="birthdateControls"] #BirthDayDropdown',
            "#BirthDayDropdown",
        ),
        timeout_ms,
    )
    if lb is not None:
        if _click_text_in_fluent_listbox(lb, labels, timeout_ms=timeout_ms):
            return True
    return _click_day_in_open_listbox(root, labels, timeout_ms)


def _keyboard_target(scope: Any) -> Any:
    """Frame 上用 scope.page.keyboard，主页面直接用 scope.keyboard。"""
    return getattr(scope, "page", scope)


def _iter_scopes(root: Any) -> list[Any]:
    """主 document + 子 frame（生日块偶发在 iframe 内）。"""
    scopes: list[Any] = [root]
    try:
        main = root.main_frame
        for fr in root.frames:
            if fr != main:
                scopes.append(fr)
    except Exception:
        pass
    return scopes


def _wait_for_birth_controls(root: Any, timeout_ms: int, log: logging.Logger) -> None:
    """密码步/弹窗后生日区可能晚就绪；在任意 frame 等到 #BirthMonth 或等价控件。"""
    log.info(
        "%s: waiting for birth UI (timeout_ms=%s)",
        "apply_signup_profile",
        timeout_ms,
    )
    deadline = time.monotonic() + timeout_ms / 1000.0
    selectors = (
        "[data-testid='birthdateControls']",
        "#BirthMonthDropdown",
        "#BirthDayDropdown",
        "#BirthMonth",
        "#BirthDay",
        'input[name="BirthYear" i]',
        'select[name="BirthMonth" i]',
    )
    sel_str = ", ".join(selectors)
    while time.monotonic() < deadline:
        for s in _iter_scopes(root):
            try:
                s.locator(sel_str).first.wait_for(state="visible", timeout=700)
                log.info(
                    "apply_signup_profile: birth control visible in frame url=%s",
                    getattr(s, "url", "?"),
                )
                return
            except Exception:
                continue
        try:
            root.wait_for_timeout(220)
        except Exception:
            break
    log.warning(
        "apply_signup_profile: birth UI not detected within %sms (current_url=%s)",
        timeout_ms,
        root.url,
    )


def _dismiss_sticky_overlays_before_birth(scope: Any) -> None:
    # 国家/地区列表常挡在生日控件之上；单次 Escape 关浮层。连按多次在部分向导里会像「返回」。
    try:
        tgt = _keyboard_target(scope)
        tgt.keyboard.press("Escape")
        tgt.wait_for_timeout(120)
    except Exception:
        pass


def _open_fluent_combobox(op: Any, scope: Any, timeout_ms: int) -> bool:
    """先滚入视口再点击，避免顶栏/侧栏截获；失败则 focus + Enter（Fluent combobox）。"""
    tgt = _keyboard_target(scope)
    cap = min(8_000, timeout_ms)
    try:
        el = op.first
        el.wait_for(state="visible", timeout=cap)
        el.scroll_into_view_if_needed(timeout=min(3_000, cap))
        tgt.wait_for_timeout(120)
        el.click(timeout=cap)
        return True
    except Exception:
        try:
            el = op.first
            el.focus(timeout=min(2_000, cap))
            tgt.keyboard.press("Enter")
            tgt.wait_for_timeout(220)
            return True
        except Exception:
            return False


def _click_option_in_any_scope(
    root: Any, texts: tuple[str, ...], *, timeout_ms: int
) -> bool:
    """Fluent 下拉选项：option / menuitem / 带文案的 gridcell。"""
    for text in texts:
        pat = re.compile(re.escape(text), re.I)
        for s in _iter_scopes(root):
            for role in ("option", "menuitem"):
                try:
                    s.get_by_role(role, name=pat).first.click(timeout=timeout_ms)
                    return True
                except Exception:
                    pass
            try:
                s.locator('[role="option"]').filter(has_text=pat).first.click(
                    timeout=timeout_ms
                )
                return True
            except Exception:
                pass
    return False


def _try_fill_birth_year_input(scope: Any, y: int, timeout_ms: int) -> bool:
    """Fluent `type=number` 的 Birth year；优先 name/aria，再 fill。"""
    caps = min(5_000, timeout_ms)
    text = str(y)
    candidates = (
        scope.locator('[data-testid="birthdateControls"] input[name="BirthYear" i]'),
        scope.locator('input[name="BirthYear" i]'),
        scope.get_by_role("spinbutton", name=re.compile(r"birth\s*year", re.I)),
        scope.locator('input[aria-label="Birth year" i]'),
        scope.locator("#BirthYear input"),
        scope.locator("#BirthYear"),
        scope.get_by_placeholder(re.compile(r"Year", re.I)),
        scope.locator('[aria-label*="year" i]'),
    )
    for loc in candidates:
        try:
            el = loc.first
            el.wait_for(state="visible", timeout=caps)
            el.click(timeout=min(3_000, timeout_ms))
            el.fill(text, timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def _pick_month_combobox_fallback(scope: Any, root: Any, m: int, timeout_ms: int) -> bool:
    month_try = _month_option_texts(m)
    openers = _month_fluent_openers(scope) + (
        scope.locator("#BirthMonth"),
        scope.get_by_role("combobox", name=re.compile(r"^Month$", re.I)),
        scope.locator("#BirthMonth button"),
    )
    for op in openers:
        if not _open_fluent_combobox(op, scope, timeout_ms):
            continue
        try:
            root.wait_for_timeout(500)
        except Exception:
            pass
        if _click_month_in_open_listbox_smart(scope, root, m, timeout_ms):
            return True
        if _click_option_in_any_scope(root, month_try, timeout_ms=timeout_ms):
            return True
        for lbl in month_try:
            pat = re.compile(re.escape(lbl), re.I)
            for choice in (
                scope.get_by_role("option", name=pat),
                scope.get_by_text(lbl, exact=True),
            ):
                try:
                    choice.first.click(timeout=timeout_ms)
                    return True
                except Exception:
                    continue
        try:
            _keyboard_target(scope).keyboard.press("Escape")
            root.wait_for_timeout(80)
        except Exception:
            pass
    return False


def _pick_day_combobox_fallback(scope: Any, root: Any, d: int, timeout_ms: int) -> bool:
    labels = _day_option_texts(d)
    openers = _day_fluent_openers(scope) + (
        scope.locator("#BirthDay"),
        scope.get_by_role("combobox", name=re.compile(r"^Day$", re.I)),
        scope.locator("#BirthDay button"),
    )
    for op in openers:
        if not _open_fluent_combobox(op, scope, timeout_ms):
            continue
        try:
            root.wait_for_timeout(500)
        except Exception:
            pass
        if _click_day_in_open_listbox_smart(scope, root, labels, timeout_ms):
            return True
        if _click_option_in_any_scope(root, labels, timeout_ms=timeout_ms):
            return True
        for label in labels:
            for choice in (
                scope.get_by_role("option", name=label),
                scope.get_by_text(label, exact=True),
            ):
                try:
                    choice.first.click(timeout=timeout_ms)
                    return True
                except Exception:
                    continue
        try:
            _keyboard_target(scope).keyboard.press("Escape")
            root.wait_for_timeout(80)
        except Exception:
            pass
    return False


def _fill_birth_on_scope(
    scope: Any,
    root: Any,
    y: int,
    m: int,
    d: int,
    *,
    timeout_ms: int,
) -> dict[str, bool]:
    t = timeout_ms
    parts = {"month": False, "day": False, "year": False}
    _dismiss_sticky_overlays_before_birth(scope)

    try:
        di = scope.locator('input[type="date"]').first
        di.wait_for(state="visible", timeout=min(4_000, t))
        di.fill(f"{y:04d}-{m:02d}-{d:02d}", timeout=t)
        parts["month"] = parts["day"] = parts["year"] = True
        return parts
    except Exception:
        pass

    month_vals = [str(m), f"{m:02d}", _MONTHS_EN[m - 1], _MONTHS_EN[m - 1][:3]]
    month_labels = [_MONTHS_EN[m - 1], _MONTHS_EN[m - 1][:3]]
    day_vals = [str(d), f"{d:02d}"]
    year_vals = [str(y)]

    if _birth_month_matches_display(scope, m, timeout_ms=t):
        parts["month"] = True
    else:
        parts["month"] = False
        # Fluent UI 现版无 #BirthMonth 内层 select，先走 combobox 避免对不存在元素长超时
        if _pick_month_combobox_fallback(scope, root, m, t):
            parts["month"] = True
        if not parts["month"]:
            for loc in _month_target_locators(scope):
                if _select_option_try_values_or_labels(
                    loc,
                    timeout_ms=min(t, 4_000),
                    values=month_vals,
                    labels=month_labels,
                ):
                    parts["month"] = True
                    break

    if _birth_day_matches_display(scope, d, timeout_ms=t):
        parts["day"] = True
    else:
        parts["day"] = False
        if _pick_day_combobox_fallback(scope, root, d, t):
            parts["day"] = True
        if not parts["day"]:
            for loc in _day_target_locators(scope):
                if _select_option_try_values_or_labels(
                    loc,
                    timeout_ms=min(t, 4_000),
                    values=day_vals,
                    labels=day_vals,
                ):
                    parts["day"] = True
                    break

    if _birth_year_matches_display(scope, y, timeout_ms=t):
        parts["year"] = True
    else:
        parts["year"] = _try_fill_birth_year_input(scope, y, t) or _select_option_try(
            scope.locator("#BirthYear").first,
            timeout_ms=t,
            values=year_vals,
        ) or _select_option_try(
            scope.locator('select[name="BirthYear" i]').first,
            timeout_ms=t,
            values=year_vals,
        )

    return parts


def _fill_birth(
    page: Any,
    y: int,
    m: int,
    d: int,
    *,
    timeout_ms: int,
    log: logging.Logger,
) -> tuple[bool, dict[str, bool]]:
    """在主 frame 与子 frame 中尝试填写生日，返回 (是否全部成功, 各段结果)。"""
    last_parts: dict[str, bool] = {"month": False, "day": False, "year": False}
    for scope in _iter_scopes(page):
        parts = _fill_birth_on_scope(
            scope, page, y, m, d, timeout_ms=timeout_ms
        )
        last_parts = parts
        if parts["month"] and parts["day"] and parts["year"]:
            log.info(
                "apply_signup_profile: birth ok frame_url=%s",
                getattr(scope, "url", "?"),
            )
            return True, parts
    log.warning(
        "apply_signup_profile: birth failed partial=%s page_url=%s",
        last_parts,
        page.url,
    )
    return False, last_parts


def _primary_action_locators(page: Any) -> list[Any]:
    return [
        page.get_by_test_id("primaryButton"),
        page.locator("#iSignupAction"),
        page.locator('input[type="submit"][id="iSignupAction"]'),
        page.get_by_role("button", name="Next"),
        page.get_by_role("button", name="Continue"),
    ]


def apply_outlook_signup_profile(
    page: Any,
    profile: dict[str, str],
    *,
    email_domain: str,
    form_step_timeout_ms: int,
    action_delay_ms: int = 0,
    chrome_password_prompt: str = "skip",
    screenshots_dir: Path,
) -> StepResult:
    """
    已通过页面校验后：填邮箱 → 下一步 → 密码 → 提交 → （可选）Chrome 密码提示 →
    **先填生日**（与「Add some info」类页面一致）→ 再填姓名（若当前屏无姓名则先点 Next 再找）。
    使用较短 form_step_timeout_ms 控制单步等待，与整页 PAGE_LOAD_TIMEOUT_MS 解耦。
    action_delay_ms 为各主步骤之间的额外 pause；chrome_password_prompt 为 save/dismiss/skip。
    """

    log = logging.getLogger(__name__)
    step = "apply_signup_profile"
    t = max(2_000, min(form_step_timeout_ms, 120_000))

    account = profile.get("account", "").strip()
    password = profile.get("password", "")
    first_name = (profile.get("first_name") or "").strip()
    last_name = (profile.get("last_name") or "").strip()
    birth_raw = profile.get("birth_date") or ""

    if not account or not password:
        return step_result(
            success=False,
            step=step,
            message="phase-2失败：phase-1 资料缺少 account 或 password",
            data={},
            error="MissingAccountOrPassword",
        )

    domain = (email_domain or "outlook.com").strip().lstrip("@")
    email = f"{account}@{domain}"
    steps_done_list: list[str] = []

    try:
        log.info("%s: fill email (step_timeout_ms=%s)", step, t)

        email_locators = [
            page.locator("#MemberName"),
            page.locator('input[name="MemberName" i]'),
            page.locator('input[type="email"]'),
        ]
        if not _fill_first_visible(page, email_locators, email, timeout_ms=t):
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：未找到可用的邮箱/用户名输入框",
                data={"steps_completed": steps_done_list, "attempted_email": email},
                error="EmailFieldNotFound",
                screenshot_path=shot,
            )
        steps_done_list.append("email_filled")
        _step_pause(page, action_delay_ms)

        if _click_first_match(page, _primary_action_locators(page), timeout_ms=t):
            steps_done_list.append("next_after_email")
            _nav_settle(page, t)
        _step_pause(page, action_delay_ms)

        pwd_locators = [
            page.locator("#PasswordInput"),
            page.locator('input[name="Password" i]'),
            page.locator('input[type="password"]'),
        ]
        if not _fill_first_visible(page, pwd_locators, password, timeout_ms=t):
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：未找到密码输入框或填写失败",
                data={"steps_completed": steps_done_list},
                error="PasswordFieldNotFound",
                screenshot_path=shot,
            )
        steps_done_list.append("password_filled")
        _step_pause(page, action_delay_ms)

        if _click_first_match(page, _primary_action_locators(page), timeout_ms=t):
            steps_done_list.append("next_after_password")
            _nav_settle(page, t)
        # 间隔后尝试命中页面内的密码保存按钮（若为浏览器外壳 UI 则可能不在 DOM）
        _step_pause(page, action_delay_ms)
        _try_chrome_password_prompt(
            page, chrome_password_prompt, timeout_ms=t, log=log
        )
        _step_pause(page, action_delay_ms)

        if not first_name or not last_name:
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：phase-1 留档缺少 first_name 或 last_name，无法填写人物信息",
                data={"steps_completed": steps_done_list},
                error="MissingNameInProfile",
                screenshot_path=shot,
            )

        parsed = _parse_birth_ymd(birth_raw)
        if not parsed:
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：birth_date 无法解析为 YYYY-MM-DD",
                data={"steps_completed": steps_done_list, "birth_date_raw": birth_raw},
                error="BirthDateInvalid",
                screenshot_path=shot,
            )
        y, mo, da = parsed
        # 密码/原生弹窗后生日区异步出现；与 PHASE2_FORM_TIMEOUT_MS 成比例但单独 capped
        _wait_for_birth_controls(page, min(45_000, max(12_000, t * 4)), log)
        birth_ok, birth_parts = _fill_birth(page, y, mo, da, timeout_ms=t, log=log)
        if not birth_ok:
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：生日控件填写失败（页面结构可能已变）",
                data={
                    "steps_completed": steps_done_list,
                    "birth_partial": birth_parts,
                    "page_url": page.url,
                },
                error="BirthFieldsNotFound",
                screenshot_path=shot,
            )
        steps_done_list.append("birth_filled")
        _step_pause(page, action_delay_ms)

        fn_locs = [
            page.locator("#FirstName"),
            page.locator('input[name="FirstName" i]'),
            page.get_by_role("textbox", name="First name"),
        ]
        ln_locs = [
            page.locator("#LastName"),
            page.locator('input[name="LastName" i]'),
            page.get_by_role("textbox", name="Last name"),
        ]

        fn_ok = _fill_first_visible(page, fn_locs, first_name, timeout_ms=t)
        if fn_ok:
            steps_done_list.append("first_name_filled")
        _step_pause(page, action_delay_ms)

        ln_ok = _fill_first_visible(page, ln_locs, last_name, timeout_ms=t)
        if ln_ok:
            steps_done_list.append("last_name_filled")
        _step_pause(page, action_delay_ms)

        # 当前屏可能仅有国家/生日（「Add some info」）；姓名在下一屏
        if not fn_ok or not ln_ok:
            if _click_first_match(page, _primary_action_locators(page), timeout_ms=t):
                steps_done_list.append("next_after_birth_only")
                _nav_settle(page, t)
            _step_pause(page, action_delay_ms)
            if not fn_ok:
                fn_ok = _fill_first_visible(page, fn_locs, first_name, timeout_ms=t)
                if fn_ok:
                    steps_done_list.append("first_name_filled")
            _step_pause(page, action_delay_ms)
            if not ln_ok:
                ln_ok = _fill_first_visible(page, ln_locs, last_name, timeout_ms=t)
                if ln_ok:
                    steps_done_list.append("last_name_filled")
            _step_pause(page, action_delay_ms)

        if not fn_ok:
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：未找到名字输入框",
                data={"steps_completed": steps_done_list},
                error="FirstNameFieldNotFound",
                screenshot_path=shot,
            )
        if not ln_ok:
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：未找到姓氏输入框",
                data={"steps_completed": steps_done_list},
                error="LastNameFieldNotFound",
                screenshot_path=shot,
            )

        if _click_first_match(page, _primary_action_locators(page), timeout_ms=t):
            steps_done_list.append("next_after_profile")
            _nav_settle(page, t)

        return step_result(
            success=True,
            step=step,
            message="phase-2完成：邮箱/密码/人物信息已填写并已尝试提交后续步骤",
            data={
                "steps_completed": steps_done_list,
                "email_used": email,
            },
            error=None,
            screenshot_path=None,
        )
    except Exception as exc:
        shot = _try_screenshot(page, screenshots_dir, step)
        return step_result(
            success=False,
            step=step,
            message="phase-2失败：录入用户信息时异常",
            data={"steps_completed": steps_done_list},
            error=f"{type(exc).__name__}: {exc}",
            screenshot_path=shot,
        )
