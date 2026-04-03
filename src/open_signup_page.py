"""Phase-2：打开 Outlook 注册页。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    from step_result import StepResult, step_result
else:
    from .step_result import StepResult, step_result


def _try_screenshot(page: Any, screenshots_dir: Path, filename_prefix: str) -> str | None:
    try:
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        # Windows 文件名不建议包含 ":" 等字符
        path = screenshots_dir / f"{filename_prefix}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)
    except Exception:
        return None


def open_signup_page(
    page: Any,
    url: str,
    timeout_ms: int,
    screenshots_dir: Path,
) -> StepResult:
    """导航到注册页；失败时保存截图。"""

    log = logging.getLogger(__name__)
    step = "open_signup_page"
    try:
        log.info("%s: goto %s (wait_until=load, timeout_ms=%s)", step, url, timeout_ms)
        # load 晚于 domcontentloaded，适合代理/指纹环境冷启动后页面资源仍在拉取的情况
        page.goto(url, timeout=timeout_ms, wait_until="load")
        current_url = getattr(page, "url", url)
        return step_result(
            success=True,
            step=step,
            message="T-P2-002完成：已导航到 Outlook 注册页",
            data={"current_url": current_url},
            error=None,
            screenshot_path=None,
        )
    except Exception as exc:
        screenshot_path = _try_screenshot(page, screenshots_dir, filename_prefix=step)
        return step_result(
            success=False,
            step=step,
            message="T-P2-002失败：注册页导航失败或超时",
            data={},
            error=f"{type(exc).__name__}: {exc}",
            screenshot_path=screenshot_path,
        )
