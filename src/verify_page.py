"""Phase-2：验证是否为 Outlook 注册页面。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    from step_result import StepResult, step_result
else:
    from .step_result import StepResult, step_result


def _try_locator_visible(page: Any, locator: Any, timeout_ms: int) -> bool:
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
        return True
    except Exception:
        return False


def verify_page(
    page: Any,
    expected_url_pattern: str | None,
    timeout_ms: int,
    screenshots_dir: Path,
) -> StepResult:
    """URL 与“注册相关元素”双条件：满足任一即判定为成功。"""

    log = logging.getLogger(__name__)
    step = "verify_page"

    def _try_screenshot() -> str | None:
        try:
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            path = screenshots_dir / f"{step}.png"
            page.screenshot(path=str(path), full_page=True)
            return str(path)
        except Exception:
            return None

    try:
        current_url = getattr(page, "url", "")

        url_ok = False
        if expected_url_pattern:
            try:
                url_ok = re.search(expected_url_pattern, current_url, flags=re.I) is not None
            except re.error:
                # 若传入字符串无法作为正则处理，退化为子串匹配
                url_ok = expected_url_pattern.lower() in current_url.lower()

        # 注册相关元素：不追求字段名完全精确，尽量用“页面语义中立”的元素
        # 选择器目标：至少命中标题/输入框/按钮之一（满足任一即可成功）
        candidate_locators = [
            ("input[type=email]", page.locator('input[type="email"]').first),
            ("input[name*=email]", page.locator('[name*=email i]').first),
            ("textbox (generic)", page.locator('[role="textbox"]').first),
            ("heading", page.get_by_role("heading").first),
            ("submit button", page.locator('button[type="submit"], input[type="submit"]').first),
            ("button (generic)", page.get_by_role("button").first),
        ]

        element_ok = False
        element_hit = None
        # 首屏往往已随 goto(load) 就绪：单次候选元素不必等满导航超时，避免 open→填邮箱前空等过久
        element_budget = min(6_000, max(2_500, timeout_ms // 15))
        for name, loc in candidate_locators:
            if _try_locator_visible(page, loc, timeout_ms=element_budget):
                element_ok = True
                element_hit = name
                break

        success = url_ok or element_ok
        if success:
            msg = "T-P2-003完成：URL 或注册相关元素校验通过"
            if not url_ok:
                msg = f"T-P2-003完成：元素校验通过（命中={element_hit}）但 URL 不完全匹配"
            if not element_ok:
                msg = "T-P2-003完成：URL 校验通过（元素未命中但页面可判定）"
            return step_result(
                success=True,
                step=step,
                message=msg,
                data={
                    "current_url": current_url,
                    "url_ok": url_ok,
                    "element_ok": element_ok,
                    "element_hit": element_hit,
                },
                error=None,
                screenshot_path=None,
            )

        # 失败：至少保存截图，方便你后续抓 DOM
        screenshot_path = _try_screenshot()
        return step_result(
            success=False,
            step=step,
            message="T-P2-003失败：URL 与注册相关元素校验未通过",
            data={
                "current_url": current_url,
                "url_ok": url_ok,
                "element_ok": element_ok,
                "element_hit": element_hit,
            },
            error="NotRegisteredPage",
            screenshot_path=screenshot_path,
        )
    except Exception as exc:
        screenshot_path = _try_screenshot()
        return step_result(
            success=False,
            step=step,
            message="T-P2-003失败：验证过程抛异常",
            data={},
            error=f"{type(exc).__name__}: {exc}",
            screenshot_path=screenshot_path,
        )
