"""Phase-2：解析 CDP 地址并附着浏览器（供分步脚本复用，非完整流水线）。"""

from __future__ import annotations

import logging
from typing import Any

if __package__ in {None, ""}:
    from config import Phase2Settings
    from connect_browser import connect_browser
    from start_hubstudio_browser import stop_then_start_browser
    from step_result import StepResult, step_result
else:
    from .config import Phase2Settings
    from .connect_browser import connect_browser
    from .start_hubstudio_browser import stop_then_start_browser
    from .step_result import StepResult, step_result

_LOG = logging.getLogger(__name__)


def resolve_phase2_cdp_url(p2: Phase2Settings) -> tuple[StepResult | None, str | None]:
    """
    返回 (失败时的 StepResult, 成功时的 cdp_http_url)。
    若设置了 p2.cdp_url_override，则不会调用 browser/stop→start。
    """

    if p2.cdp_url_override:
        return None, p2.cdp_url_override
    if not p2.hubstudio_api_base or not p2.container_code:
        return (
            step_result(
                success=False,
                step="hubstudio_browser_start",
                message="缺少 HUBSTUDIO_API_BASE 或环境 ID，且未设置 HUBSTUDIO_CDP_URL",
                error="MissingHubstudioConfig",
            ),
            None,
        )
    _LOG.warning(
        "phase2_attach: 将执行 browser/stop→start，会结束当前环境中的浏览器会话；"
        "若需保留已打开的人机验证页，请在 .env 设置 HUBSTUDIO_CDP_URL 直连 CDP。"
    )
    try:
        start_data = stop_then_start_browser(
            api_base=p2.hubstudio_api_base,
            container_code=p2.container_code,
        )
        port = start_data.get("debuggingPort")
        return None, f"http://127.0.0.1:{int(port)}"
    except Exception as exc:
        return (
            step_result(
                success=False,
                step="hubstudio_browser_start",
                message="按环境 ID 调用 browser/stop→start 未成功",
                data={"container_code": p2.container_code},
                error=f"{type(exc).__name__}: {exc}",
            ),
            None,
        )


def attach_phase2_session(
    pw: Any,
    p2: Phase2Settings,
    *,
    page_url_contains: str | None = None,
) -> tuple[StepResult, dict[str, Any] | None]:
    """CDP 连接并返回 browser/context/page（与 pipeline 前置步骤一致，不含 open_signup）。"""

    err, cdp_url = resolve_phase2_cdp_url(p2)
    if err is not None:
        return err, None
    assert cdp_url is not None
    connect_res, objs = connect_browser(
        pw, cdp_url, page_url_contains=page_url_contains
    )
    if not connect_res["success"]:
        return connect_res, None
    assert objs is not None
    page = objs["page"]
    page.set_default_navigation_timeout(p2.page_load_timeout_ms)
    page.set_default_timeout(p2.page_load_timeout_ms)
    return connect_res, objs
