"""步骤 01：仅连接 CDP、列出标签 URL、对当前目标页截图。不点击、不导航。

用法（仓库根目录）：
  python scripts/ms_step01_connect_probe.py

依赖 .env 与 phase-2 相同：至少 OUTLOOK_REGISTER_URL；
连接方式：HUBSTUDIO_CDP_URL **或** HUBSTUDIO_API_BASE + HUBSTUDIO_CONTAINER。

标签页选择：环境变量 PHASE2_PAGE_URL_CONTAINS（默认 signup.live.com）；置空则使用 CDP 附着后的第一个标签页。

保留已开页面：请使用 HUBSTUDIO_CDP_URL 直连；若仅 HUBSTUDIO_CONTAINER + API，会先 stop/start 浏览器导致标签丢失（见 phase2_attach 日志）。
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
from phase2_attach import attach_phase2_session
from playwright.sync_api import sync_playwright


def _page_url_filter() -> str | None:
    raw = os.getenv("PHASE2_PAGE_URL_CONTAINS", "signup.live.com").strip()
    return raw if raw else None


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("ms_step01")
    p2 = load_phase2_settings()
    filt = _page_url_filter()
    with sync_playwright() as pw:
        res, objs = attach_phase2_session(pw, p2, page_url_contains=filt)
        if not res["success"]:
            log.error("连接失败: %s", res)
            return 1
        assert objs is not None
        browser = objs["browser"]
        page = objs["page"]
        for ci, ctx in enumerate(browser.contexts):
            for pi, pg in enumerate(ctx.pages):
                try:
                    u = pg.url
                except Exception as exc:
                    u = f"<url error: {exc}>"
                log.info("context %s tab %s: %s", ci, pi, u)
        p2.screenshots_dir.mkdir(parents=True, exist_ok=True)
        shot = p2.screenshots_dir / "ms_step01_connect_probe.png"
        page.screenshot(path=str(shot), full_page=True)
        log.info("已截图: %s", shot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
