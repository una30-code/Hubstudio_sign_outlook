"""入口：支持 phase-0（Hubstudio 环境创建）与 phase-1（用户信息生成）。"""

import logging
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    # 兼容直接运行 `python src/main.py`：优先导入当前项目的 src 目录
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from config import load_hubstudio_env_create_config
    from pipeline import (
        run_hubstudio_env_creation,
        run_phase1_user_profile_generation,
        run_phase2_outlook_signup_page,
    )
else:
    from .config import load_hubstudio_env_create_config
    from .pipeline import (
        run_hubstudio_env_creation,
        run_phase1_user_profile_generation,
        run_phase2_outlook_signup_page,
    )


def setup_logging(log_dir: Path, log_filename: str) -> None:
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


def _parse_phase_from_args_and_env() -> int:
    # 优先级：CLI > 环境变量 PHASE > 默认 0
    for arg in sys.argv[1:]:
        if arg.startswith("--phase="):
            return int(arg.split("=", 1)[1].strip())
        if arg in {"--phase1", "--phase-1"}:
            return 1
        if arg in {"--phase2", "--phase-2"}:
            return 2
        if arg in {"--phase0", "--phase-0"}:
            return 0

    raw = os.getenv("PHASE", "").strip()
    return int(raw) if raw else 0


def _parse_user_gen_seed() -> int | None:
    raw = os.getenv("USER_GEN_SEED", "").strip()
    if not raw:
        return None
    return int(raw)


def _redact_sensitive_data(data: dict) -> dict:
    # 对日志做脱敏，避免把密码原文写入日志文件。
    if not data:
        return {}
    safe = dict(data)
    if "password" in safe:
        safe["password"] = "***"
    return safe


def main() -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    phase = _parse_phase_from_args_and_env()
    log = logging.getLogger(__name__)

    # phase-1 / phase-2 不依赖 phase-0 的 Hubstudio 环境创建配置
    if phase in {1, 2}:
        project_root = Path(__file__).resolve().parent.parent
        log_dir = project_root / os.getenv("LOG_DIR", "logs")
        setup_logging(log_dir, log_filename=f"phase{phase}.log")
    else:
        # phase-0 需要完整 Hubstudio 环境创建配置
        try:
            settings = load_hubstudio_env_create_config()
        except ValueError as exc:
            log.error("配置加载失败：%s", exc)
            return 1
        setup_logging(settings.log_dir, log_filename="phase0.log")

    log = logging.getLogger(__name__)  # 重新获取包含 file handler 的 logger

    if phase == 1:
        seed = _parse_user_gen_seed()
        log.info("Phase-1 启动：生成 Outlook 注册用用户信息")
        result, _page = run_phase1_user_profile_generation(seed=seed)
    elif phase == 2:
        log.info("Phase-2 启动：连接 Hubstudio -> 打开 Outlook 注册页 -> 校验")
        result, _page = run_phase2_outlook_signup_page()
    else:
        log.info("Phase-0 启动：Hubstudio 环境创建")
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
        log.info("流水线数据(脱敏): %s", _redact_sensitive_data(result["data"]))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
