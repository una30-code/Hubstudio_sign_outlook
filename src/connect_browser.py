"""Phase-2：通过 CDP 连接 Hubstudio 浏览器。"""

from __future__ import annotations

import logging
from typing import Any

if __package__ in {None, ""}:
    from step_result import StepResult, step_result
else:
    from .step_result import StepResult, step_result


def connect_browser(
    pw: Any,
    cdp_url: str,
) -> tuple[StepResult, dict[str, Any] | None]:
    """
    通过 Playwright CDP WebSocket 连接现有浏览器。

    返回：
    - StepResult：success/error/screenshot_path
    - objects：{browser, context, page}
    """

    log = logging.getLogger(__name__)
    step = "connect_browser"
    try:
        log.info("%s: connecting over CDP", step)
        browser = pw.chromium.connect_over_cdp(cdp_url)

        context = browser.contexts[0] if getattr(browser, "contexts", []) else None
        page = None
        if context is not None:
            pages = getattr(context, "pages", [])
            if pages:
                page = pages[0]

        if page is None:
            # 兜底：尝试直接在浏览器上创建新页面
            page = browser.new_page()

        if page is None:
            return (
                step_result(
                    success=False,
                    step=step,
                    message="T-P2-001失败：未能获取 page",
                    error="NoPage",
                ),
                None,
            )

        return (
            step_result(
                success=True,
                step=step,
                message="T-P2-001完成：已连接并获取页面",
                data={
                    "has_context": context is not None,
                    "contexts_count": len(getattr(browser, "contexts", [])),
                },
            ),
            {"browser": browser, "context": context, "page": page},
        )
    except Exception as exc:
        return (
            step_result(
                success=False,
                step=step,
                message="T-P2-001失败：CDP 连接失败",
                error=f"{type(exc).__name__}: {exc}",
            ),
            None,
        )

