"""Phase-0 编排占位：Hubstudio 环境创建。"""

from typing import Any

if __package__ in {None, ""}:
    from config import load_hubstudio_env_create_config
    from create_hubstudio_environment import create_hubstudio_environment
    from sequence_state import (
        STATE_FILE_NAME,
        build_environment_name,
        commit_sequence,
        get_next_sequence,
    )
    from step_result import StepResult, step_result
    from validate_hubstudio_env_config import validate_hubstudio_env_create_config
else:
    from .config import load_hubstudio_env_create_config
    from .create_hubstudio_environment import create_hubstudio_environment
    from .sequence_state import (
        STATE_FILE_NAME,
        build_environment_name,
        commit_sequence,
        get_next_sequence,
    )
    from .step_result import StepResult, step_result
    from .validate_hubstudio_env_config import validate_hubstudio_env_create_config


def run_hubstudio_env_creation() -> tuple[StepResult, Any | None]:
    """
    串联 load_hubstudio_env_config -> validate_hubstudio_env_config -> create_hubstudio_environment。
    当前为占位实现；返回 (结果字典, None)。
    """
    try:
        cfg = load_hubstudio_env_create_config()
        alloc = get_next_sequence(
            log_dir=cfg.log_dir,
            site_name=cfg.site_name,
            region=cfg.region,
            sequence_start=cfg.name_sequence_start,
        )
        env_name = cfg.environment_name or build_environment_name(
            cfg.site_name, alloc.sequence, cfg.region
        )
        validation = validate_hubstudio_env_create_config(
            cfg, allocated_sequence=alloc.sequence, environment_name=env_name
        )
        if not validation.ok:
            return (
                step_result(
                    success=False,
                    step="hubstudio_env_creation",
                    message="T-004失败：配置或命名规则校验未通过",
                    data={
                        "site_name": cfg.site_name,
                        "region": cfg.region,
                        "allocated_sequence": alloc.sequence,
                        "environment_name": env_name,
                    },
                    error="; ".join(validation.errors),
                ),
                None,
            )
        api_data = create_hubstudio_environment(cfg, env_name)
        commit_sequence(log_dir=cfg.log_dir, key=alloc.key, used_sequence=alloc.sequence)
        return (
            step_result(
                success=True,
                step="hubstudio_env_creation",
                message="T-005完成：Hubstudio环境创建成功并已提交序号",
                data={
                    "site_name": cfg.site_name,
                    "region": cfg.region,
                    "sequence_key": alloc.key,
                    "allocated_sequence": alloc.sequence,
                    "environment_name": env_name,
                    "state_file": str(cfg.log_dir / STATE_FILE_NAME),
                    "container_code": api_data.get("containerCode"),
                },
                error=None,
            ),
            None,
        )
    except Exception as exc:
        return (
            step_result(
                success=False,
                step="hubstudio_env_creation",
                message="T-005失败：配置、校验、创建接口或序号提交失败",
                error=f"{type(exc).__name__}: {exc}",
            ),
            None,
        )
