"""入口：phase-0 配置加载 + 调用编排 + 退出码。"""

import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    # 兼容直接运行 `python src/main.py`：优先导入当前项目的 src 目录
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from config import load_hubstudio_env_create_config
    from pipeline import run_hubstudio_env_creation
else:
    from .config import load_hubstudio_env_create_config
    from .pipeline import run_hubstudio_env_creation


def setup_logging(log_dir: Path, log_filename: str = "phase0.log") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_filename
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    for h in root.handlers[:]:
        h.close()
        root.removeHandler(h)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    root.addHandler(fh)
    root.addHandler(sh)


def main() -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger(__name__)
    try:
        settings = load_hubstudio_env_create_config()
    except ValueError as exc:
        log.error("配置加载失败：%s", exc)
        return 1

    setup_logging(settings.log_dir)
    log = logging.getLogger(__name__)

    log.info("Phase-0 启动（当前为 T-006 之前的编排骨架）")
    result, _page = run_hubstudio_env_creation()
    log.info(
        "流水线结果: success=%s step=%s message=%s",
        result["success"],
        result["step"],
        result["message"],
    )
    if result.get("error"):
        log.error("流水线错误: %s", result["error"])
    if result["data"]:
        log.info("流水线数据: %s", result["data"])
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
