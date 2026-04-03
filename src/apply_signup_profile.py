"""Phase-2：将 phase-1 用户信息填入 Outlook 注册流（邮箱→密码→人物信息→提交）。"""

from __future__ import annotations

import logging
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


def _fill_birth(
    page: Any,
    y: int,
    m: int,
    d: int,
    *,
    timeout_ms: int,
) -> bool:
    t = timeout_ms
    try:
        di = page.locator('input[type="date"]').first
        di.wait_for(state="visible", timeout=min(4_000, t))
        di.fill(f"{y:04d}-{m:02d}-{d:02d}", timeout=t)
        return True
    except Exception:
        pass

    month_vals = [str(m), f"{m:02d}", _MONTHS_EN[m - 1], _MONTHS_EN[m - 1][:3]]
    day_vals = [str(d), f"{d:02d}"]
    year_vals = [str(y)]

    month_ok = _select_option_try(
        page.locator("#BirthMonth").first,
        timeout_ms=t,
        values=month_vals,
    ) or _select_option_try(
        page.locator('select[name="BirthMonth" i]').first,
        timeout_ms=t,
        values=month_vals,
    )

    day_ok = _select_option_try(
        page.locator("#BirthDay").first,
        timeout_ms=t,
        values=day_vals,
    ) or _select_option_try(
        page.locator('select[name="BirthDay" i]').first,
        timeout_ms=t,
        values=day_vals,
    )

    year_ok = _select_option_try(
        page.locator("#BirthYear").first,
        timeout_ms=t,
        values=year_vals,
    ) or _select_option_try(
        page.locator('select[name="BirthYear" i]').first,
        timeout_ms=t,
        values=year_vals,
    )

    return month_ok and day_ok and year_ok


def _primary_action_locators(page: Any) -> list[Any]:
    return [
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
    screenshots_dir: Path,
) -> StepResult:
    """
    已通过页面校验后：填邮箱 → 下一步 → 密码 → 提交 → 姓名/生日 → 再提交。
    使用较短 form_step_timeout_ms 控制单步等待，与整页 PAGE_LOAD_TIMEOUT_MS 解耦。
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

        if _click_first_match(page, _primary_action_locators(page), timeout_ms=t):
            steps_done_list.append("next_after_email")
            _nav_settle(page, t)

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

        if _click_first_match(page, _primary_action_locators(page), timeout_ms=t):
            steps_done_list.append("next_after_password")
            _nav_settle(page, t)

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
        if not _fill_first_visible(page, fn_locs, first_name, timeout_ms=t):
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：未找到名字输入框",
                data={"steps_completed": steps_done_list},
                error="FirstNameFieldNotFound",
                screenshot_path=shot,
            )
        steps_done_list.append("first_name_filled")

        if not _fill_first_visible(page, ln_locs, last_name, timeout_ms=t):
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：未找到姓氏输入框",
                data={"steps_completed": steps_done_list},
                error="LastNameFieldNotFound",
                screenshot_path=shot,
            )
        steps_done_list.append("last_name_filled")

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
        if not _fill_birth(page, y, mo, da, timeout_ms=t):
            shot = _try_screenshot(page, screenshots_dir, step)
            return step_result(
                success=False,
                step=step,
                message="phase-2失败：生日控件填写失败（页面结构可能已变）",
                data={"steps_completed": steps_done_list},
                error="BirthFieldsNotFound",
                screenshot_path=shot,
            )
        steps_done_list.append("birth_filled")

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
