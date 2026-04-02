"""Minimal standalone tester for Hubstudio env/create API.

Usage:
  python scripts/test_env_create_api.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from urllib import error, parse, request

from dotenv import load_dotenv
import os


def build_payload() -> dict:
    now = datetime.now()
    name = f"api_test_{now.year}{now.month:02d}{now.day:02d}_{now.hour:02d}{now.minute:02d}{now.second:02d}"
    return {
        "asDynamicType": 0,
        "containerName": name,
        "proxyTypeName": "不使用代理",
        "coreVersion": 112,
        "advancedBo": {
            "uaVersion": 112,
            "uiLanguage": "en",
            "languages": ["en", "en-US"],
        },
    }


def post_env_create(base_url: str, payload: dict) -> str:
    url = parse.urljoin(base_url.rstrip("/") + "/", "api/v1/env/create")
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return f"HTTP {resp.status}\n{body}"
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return f"HTTP ERROR {exc.code}\n{body}"
    except Exception as exc:
        return f"REQUEST ERROR\n{type(exc).__name__}: {exc}"


def main() -> int:
    load_dotenv()
    base_url = (os.getenv("HUBSTUDIO_API_BASE") or "").strip() or "http://127.0.0.1:58526"
    payload = build_payload()
    print("Target:", base_url)
    print("Payload:", json.dumps(payload, ensure_ascii=False))
    print("---- response ----")
    print(post_env_create(base_url, payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
