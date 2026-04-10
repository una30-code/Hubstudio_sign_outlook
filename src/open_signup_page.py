"""Phase-2：打开 Outlook 注册页。"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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


def _navigation_aborted(exc: BaseException) -> bool:
    return "err_aborted" in f"{exc}".lower()


def _current_url_safe(page: Any) -> str:
    try:
        return getattr(page, "url", "") or ""
    except Exception:
        return ""


def _likely_reached_target(page_url: str, target_url: str) -> bool:
    """ERR_ABORTED 后主文档可能已停在目标或微软注册/ OAuth 链路上。"""
    pu = (page_url or "").lower()
    if not pu or pu.startswith("about:"):
        return False
    try:
        host = (urlparse(target_url).hostname or "").lower()
    except Exception:
        host = ""
    if host and host in pu:
        return True
    if "signup.live.com" in pu:
        return True
    if "login.live.com" in pu and ("signup" in pu or "oauth" in pu):
        return True
    return False


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
        # 首次 CDP 连上时 wait_until=load 易与重定向/二次导航竞争，触发 net::ERR_ABORTED
        # 而页面实际已渲染。先用 domcontentloaded，再尽力等 load（不 satisfied 不判失败）。
        log.info(
            "%s: goto %s (wait_until=domcontentloaded, timeout_ms=%s)",
            step,
            url,
            timeout_ms,
        )
        for attempt in range(2):
            try:
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                break
            except Exception as exc:
                if not _navigation_aborted(exc):
                    raise
                if _likely_reached_target(_current_url_safe(page), url):
                    log.info(
                        "%s: goto ERR_ABORTED but URL already usable: %s",
                        step,
                        _current_url_safe(page),
                    )
                    break
                if attempt == 0:
                    log.info("%s: goto ERR_ABORTED; retry once after short delay", step)
                    time.sleep(0.6)
                else:
                    raise
        try:
            page.wait_for_load_state("load", timeout=min(timeout_ms, 120_000))
        except Exception as load_exc:
            log.info(
                "%s: wait_for_load_state(load) skipped: %s",
                step,
                load_exc,
            )
        current_url = _current_url_safe(page) or url
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
