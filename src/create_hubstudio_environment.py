"""Call Hubstudio API to create environment (T-005)."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request

if __package__ in {None, ""}:
    from config import HubstudioEnvCreateConfig
else:
    from .config import HubstudioEnvCreateConfig


def _build_payload(cfg: HubstudioEnvCreateConfig, environment_name: str) -> dict[str, Any]:
    return {
        "containerName": environment_name,
        "asDynamicType": 1,
        "proxyTypeName": "Socks5",
        "proxyServer": cfg.proxy.host,
        "proxyPort": cfg.proxy.port,
        "proxyAccount": cfg.proxy.username,
        "proxyPassword": cfg.proxy.password,
        "type": "windows",
        "browser": "chrome",
        "coreVersion": 124,
        "advancedBo": {
            "uaVersion": cfg.fingerprint.ua_version,
            "ua": cfg.fingerprint.ua,
            "languages": ["en", "en-US"],
        },
    }


def create_hubstudio_environment(
    cfg: HubstudioEnvCreateConfig, environment_name: str
) -> dict[str, Any]:
    endpoint = f"{cfg.hubstudio_api_base.rstrip('/')}/api/v1/env/create"
    payload = _build_payload(cfg, environment_name)
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        body = body.strip()
        if len(body) > 500:
            body = body[:500] + "...(truncated)"
        detail = f"Hubstudio HTTP error: {exc.code}"
        if body:
            detail += f" body={body}"
        raise RuntimeError(detail) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Hubstudio connection failed: {exc.reason}") from exc

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("Hubstudio response is not JSON object")
    if data.get("code") != 0:
        raise RuntimeError(f"Hubstudio create env failed: {data}")
    inner = data.get("data") or {}
    if not isinstance(inner, dict):
        raise RuntimeError("Hubstudio response data is invalid")
    if "containerCode" not in inner:
        raise RuntimeError("Hubstudio response missing containerCode")
    return inner
