"""步骤 04：连接 CDP 后，仅对「Press and hold」按钮做长按点击（时长见 PHASE2_HOLD_PRESS_DURATION_MS）。

用法：
  python scripts/ms_step04_press_hold.py

若尚未点过无障碍入口，可能仍有旧版主按钮；脚本会按当前 DOM 重新解析人机卡片根节点。
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
from ms_hold_challenge import press_ms_challenge_hold_only
from phase2_attach import attach_phase2_session
from playwright.sync_api import sync_playwright


def _page_url_filter() -> str | None:
    raw = os.getenv("PHASE2_PAGE_URL_CONTAINS", "signup.live.com").strip()
    return raw if raw else None


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("ms_step04")
    p2 = load_phase2_settings()
    with sync_playwright() as pw:
        res, objs = attach_phase2_session(pw, p2, page_url_contains=_page_url_filter())
        if not res["success"]:
            log.error("连接失败: %s", res)
            return 1
        assert objs is not None
        r = press_ms_challenge_hold_only(
            objs["page"],
            form_step_timeout_ms=p2.phase2_form_timeout_ms,
            hold_press_ms=p2.phase2_hold_press_duration_ms,
            chrome_password_prompt=p2.chrome_password_prompt,
            screenshots_dir=p2.screenshots_dir,
            refind_root_before_press=p2.phase2_hold_refind_root_before_press,
            locator_probe_timeout_ms=p2.phase2_hold_locator_probe_ms,
        )
        log.info("结果: %s", r)
        return 0 if r["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
