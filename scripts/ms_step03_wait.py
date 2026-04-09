"""步骤 03：连接 CDP 后等待（固定时长或直到「Press and hold」可见），并截图。

用法：
  python scripts/ms_step03_wait.py

环境变量：
  MS_STEP03_WAIT_MODE=sleep（默认） | until_press
  MS_STEP03_WAIT_MS — sleep 模式下毫秒数，默认 PHASE2_HOLD_AFTER_ACCESSIBLE_MS
  MS_STEP03_UNTIL_PRESS_TIMEOUT_MS — until_press 模式上限，默认 15000
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from config import load_phase2_settings
from ms_hold_challenge import wait_ms_challenge_step03
from phase2_attach import attach_phase2_session
from playwright.sync_api import sync_playwright


def _page_url_filter() -> str | None:
    raw = os.getenv("PHASE2_PAGE_URL_CONTAINS", "signup.live.com").strip()
    return raw if raw else None


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("ms_step03")
    p2 = load_phase2_settings()
    mode = (os.getenv("MS_STEP03_WAIT_MODE") or "sleep").strip().lower()
    extra = os.getenv("MS_STEP03_WAIT_MS", "").strip()
    if extra:
        wait_ms = max(0, int(extra))
    else:
        wait_ms = max(0, int(p2.phase2_hold_after_accessible_ms))
    until_raw = (os.getenv("MS_STEP03_UNTIL_PRESS_TIMEOUT_MS") or "").strip()
    until_ms = max(1_000, int(until_raw)) if until_raw else 15_000

    with sync_playwright() as pw:
        res, objs = attach_phase2_session(pw, p2, page_url_contains=_page_url_filter())
        if not res["success"]:
            log.error("连接失败: %s", res)
            return 1
        assert objs is not None
        r = wait_ms_challenge_step03(
            objs["page"],
            mode=mode,
            sleep_ms=wait_ms,
            until_press_timeout_ms=until_ms,
            form_step_timeout_ms=p2.phase2_form_timeout_ms,
            screenshots_dir=p2.screenshots_dir,
        )
        log.info("结果: %s", r)
        return 0 if r["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
