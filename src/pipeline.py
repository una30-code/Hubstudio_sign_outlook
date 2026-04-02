"""Phase-0 编排占位：Hubstudio 环境创建。"""

from typing import Any

if __package__ in {None, ""}:
    from config import load_hubstudio_env_create_config
    from config import load_settings
    from create_hubstudio_environment import create_hubstudio_environment
    from connect_browser import connect_browser
    from open_signup_page import open_signup_page
    from verify_page import verify_page
    from sequence_state import (
        STATE_FILE_NAME,
        build_environment_name,
        commit_sequence,
        get_next_sequence,
    )
    from step_result import StepResult, step_result
    from validate_hubstudio_env_config import validate_hubstudio_env_create_config
    from outlook_user_profile import run_phase1_user_profile
else:
    from .config import load_hubstudio_env_create_config
    from .config import load_settings
    from .create_hubstudio_environment import create_hubstudio_environment
    from .connect_browser import connect_browser
    from .open_signup_page import open_signup_page
    from .verify_page import verify_page
    from .sequence_state import (
        STATE_FILE_NAME,
        build_environment_name,
        commit_sequence,
        get_next_sequence,
    )
    from .step_result import StepResult, step_result
    from .validate_hubstudio_env_config import validate_hubstudio_env_create_config
    from .outlook_user_profile import run_phase1_user_profile


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


def run_phase1_user_profile_generation(seed: int | None = None) -> tuple[StepResult, Any | None]:
    """Phase-1：生成 Outlook 注册用用户信息（纯数据生成）。"""

    try:
        return run_phase1_user_profile(seed=seed)
    except Exception as exc:
        return (
            step_result(
                success=False,
                step="outlook_user_profile",
                message="T-P1-003失败：生成用户信息失败",
                error=f"{type(exc).__name__}: {exc}",
            ),
            None,
        )


def run_phase2_outlook_signup_page() -> tuple[StepResult, Any | None]:
    """Phase-2：连接 Hubstudio -> 打开 Outlook 注册页 -> 校验页面。"""

    from pathlib import Path
    import re
    from urllib.parse import urlparse

    from playwright.sync_api import sync_playwright

    try:
        settings = load_settings()
        screenshots_dir: Path = settings.screenshots_dir
        timeout_ms: int = settings.page_load_timeout_ms

        # 从 URL 推导一个稳定的“期望模式”，用于 verify_page 的 regex search
        parsed = urlparse(settings.outlook_register_url)
        expected_url_pattern = re.escape(parsed.netloc + parsed.path)

        with sync_playwright() as pw:
            connect_res, objs = connect_browser(
                pw=pw,
                cdp_url=settings.hubstudio_cdp_url,
            )
            if not connect_res["success"]:
                return connect_res, None

            browser = objs["browser"]
            page = objs["page"]
            try:
                open_res = open_signup_page(
                    page=page,
                    url=settings.outlook_register_url,
                    timeout_ms=timeout_ms,
                    screenshots_dir=screenshots_dir,
                )
                if not open_res["success"]:
                    return open_res, None

                verify_res = verify_page(
                    page=page,
                    expected_url_pattern=expected_url_pattern,
                    timeout_ms=timeout_ms,
                    screenshots_dir=screenshots_dir,
                )
                return verify_res, None
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    except Exception as exc:
        return (
            step_result(
                success=False,
                step="phase2_outlook_signup_page",
                message="T-P2-004失败：phase-2 执行过程中出现异常",
                error=f"{type(exc).__name__}: {exc}",
            ),
            None,
        )
