#!/usr/bin/env python3
"""
对同一 Hubstudio 环境 ID 重复执行 stop→start，记录每次 debuggingPort 与 CDP HTTP 基址。

输出写入本工具目录下 output/，不污染仓库 logs/ 与 .env。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# 仓库根目录（…/tools/hubstudio_cdp_probe/run_probe.py → 上两级到根）
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _setup_path() -> None:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _maybe_load_dotenv(*, use_dotenv: bool) -> None:
    if not use_dotenv:
        return
    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_file)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="重复 Hubstudio browser/stop→start，记录 debuggingPort（CDP 基址）是否变化",
    )
    parser.add_argument(
        "--container-code",
        required=True,
        help="Hubstudio 环境 ID（containerCode）",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="循环次数（默认 3）",
    )
    parser.add_argument(
        "--api-base",
        default="",
        help="Hubstudio API 根 URL；缺省使用环境变量 HUBSTUDIO_API_BASE",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="每轮结束后休眠秒数（默认 2；设 0 关闭）",
    )
    parser.add_argument(
        "--no-dotenv",
        action="store_true",
        help="不加载仓库根目录 .env",
    )
    args = parser.parse_args()

    if args.rounds < 1:
        print("rounds 须 >= 1", file=sys.stderr)
        return 2

    _setup_path()
    _maybe_load_dotenv(use_dotenv=not args.no_dotenv)

    api_base = (args.api_base or "").strip() or os.environ.get("HUBSTUDIO_API_BASE", "").strip()
    if not api_base:
        print(
            "缺少 API 基址：请设置 --api-base 或环境变量 HUBSTUDIO_API_BASE",
            file=sys.stderr,
        )
        return 2

    from src.start_hubstudio_browser import stop_then_start_browser

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    jsonl_path = out_dir / f"probe_{stamp}.jsonl"

    ports: list[int] = []
    container = str(args.container_code).strip()

    print(f"API_BASE={api_base}")
    print(f"containerCode={container}")
    print(f"rounds={args.rounds}")
    print(f"jsonl={jsonl_path}")
    print("---")

    for i in range(1, args.rounds + 1):
        utc_now = datetime.now(timezone.utc).isoformat()
        try:
            data = stop_then_start_browser(
                api_base=api_base,
                container_code=container,
            )
            port = int(data["debuggingPort"])
            cdp_http = f"http://127.0.0.1:{port}"
            ports.append(port)
            record = {
                "round": i,
                "utc": utc_now,
                "container_code": container,
                "debuggingPort": port,
                "cdp_http": cdp_http,
                "hubstudio_data_keys": sorted(data.keys()),
            }
            line = json.dumps(record, ensure_ascii=False)
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            print(f"round {i}: debuggingPort={port}  cdp_http={cdp_http}")
        except Exception as exc:
            err = {
                "round": i,
                "utc": utc_now,
                "container_code": container,
                "error": f"{type(exc).__name__}: {exc}",
            }
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(err, ensure_ascii=False) + "\n")
            print(f"round {i}: ERROR {err['error']}", file=sys.stderr)
            return 1

        if i < args.rounds and args.sleep > 0:
            time.sleep(args.sleep)

    unique = sorted(set(ports))
    print("---")
    print(f"全部端口序列: {ports}")
    print(f"去重集合: {unique}")
    if len(ports) >= 2:
        changes = sum(1 for a, b in zip(ports, ports[1:]) if a != b)
        print(f"相邻轮端口变化次数: {changes} / {len(ports) - 1}")
        if changes == 0:
            print("结论（本机本次）: 各轮 debuggingPort 相同。")
        else:
            print("结论（本机本次）: debuggingPort 在至少一轮之间发生了变化。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
