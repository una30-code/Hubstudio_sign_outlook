"""步骤 02：连接 CDP 后，仅点击人机验证卡片的「Accessible challenge / 无障碍」入口。

用法：
  python scripts/ms_step02_click_accessibility.py

成功时可再执行 ms_step03_wait.py → ms_step04_press_hold.py。
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
from ms_hold_challenge import click_ms_challenge_accessibility_only
from phase2_attach import attach_phase2_session
from playwright.sync_api import sync_playwright


def _page_url_filter() -> str | None:
    raw = os.getenv("PHASE2_PAGE_URL_CONTAINS", "signup.live.com").strip()
    return raw if raw else None


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("ms_step02")
    p2 = load_phase2_settings()
    with sync_playwright() as pw:
        res, objs = attach_phase2_session(pw, p2, page_url_contains=_page_url_filter())
        if not res["success"]:
            log.error("连接失败: %s", res)
            return 1
        assert objs is not None
        noop = (os.getenv("MS_ACCESSIBILITY_NOOP_IF_NO_BUTTON") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        r = click_ms_challenge_accessibility_only(
            objs["page"],
            form_step_timeout_ms=p2.phase2_form_timeout_ms,
            chrome_password_prompt=p2.chrome_password_prompt,
            screenshots_dir=p2.screenshots_dir,
            noop_if_accessibility_missing=noop,
            locator_probe_timeout_ms=p2.phase2_hold_locator_probe_ms,
        )
        log.info("结果: %s", r)
        return 0 if r["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
