"""Hubstudio：按环境 ID 停止/启动浏览器（browser/stop、browser/start）。"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib import error, request

_LOG = logging.getLogger(__name__)


def _stop_browser_best_effort(
    *,
    api_base: str,
    container_code: str,
    timeout_s: float = 60.0,
) -> None:
    """
    POST /api/v1/browser/stop。不抛异常：环境未开或接口返回非 0 时仍继续，避免阻断后续 start。
    文档：https://support-orig.hubstudio.cn/0379/7beb/fbb0/6964
    """

    endpoint = f"{api_base.rstrip('/')}/api/v1/browser/stop"
    payload = {"containerCode": str(container_code)}
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            err_body = ""
        _LOG.info(
            "hubstudio browser/stop HTTP %s (ignored for best-effort): %s",
            exc.code,
            err_body[:200] if err_body else "",
        )
        return
    except error.URLError as exc:
        _LOG.info("hubstudio browser/stop URLError (ignored): %s", exc.reason)
        return
    except OSError as exc:
        _LOG.info("hubstudio browser/stop OS error (ignored): %s", exc)
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _LOG.info("hubstudio browser/stop: non-JSON body, ignored")
        return
    if isinstance(data, dict) and data.get("code") != 0:
        _LOG.info("hubstudio browser/stop code!=0 (ignored): %s", data.get("msg", data))


def stop_then_start_browser(
    *,
    api_base: str,
    container_code: str,
    stop_timeout_s: float = 60.0,
    start_timeout_s: float = 120.0,
) -> dict[str, Any]:
    """
    先 best-effort 关闭环境，再 start，尽量拿到**新的** debuggingPort。
    官方 start 成功体中无 reliably 的「已在运行」标志；环境已开时常报 -10013 等，故用 stop→start 统一策略。
    """

    _stop_browser_best_effort(
        api_base=api_base,
        container_code=container_code,
        timeout_s=stop_timeout_s,
    )
    return start_browser_by_container_code(
        api_base=api_base,
        container_code=container_code,
        timeout_s=start_timeout_s,
    )


def start_browser_by_container_code(
    *,
    api_base: str,
    container_code: str,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """
    启动指定环境，返回 data 对象（含 debuggingPort 等）。
    文档：https://support-orig.hubstudio.cn/0379/7beb/fbb0/6964
    """

    endpoint = f"{api_base.rstrip('/')}/api/v1/browser/start"
    payload: dict[str, Any] = {
        "containerCode": str(container_code),
        "isHeadless": False,
        "isWebDriverReadOnlyMode": False,
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            err_body = ""
        err_body = err_body.strip()
        if len(err_body) > 500:
            err_body = err_body[:500] + "...(truncated)"
        detail = f"Hubstudio HTTP error: {exc.code}"
        if err_body:
            detail += f" body={err_body}"
        raise RuntimeError(detail) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Hubstudio connection failed: {exc.reason}") from exc

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("Hubstudio response is not JSON object")
    if data.get("code") != 0:
        raise RuntimeError(f"Hubstudio browser/start failed: {data}")
    inner = data.get("data") or {}
    if not isinstance(inner, dict):
        raise RuntimeError("Hubstudio response data is invalid")
    if inner.get("debuggingPort") is None:
        raise RuntimeError("Hubstudio browser/start response missing debuggingPort")
    return inner
