"""Phase-0 编排占位：Hubstudio 环境创建。"""

from datetime import datetime
from typing import Any

if __package__ in {None, ""}:
    from archive_store import append_archive_record, read_latest_phase1_user_profile
    from config import load_hubstudio_env_create_config
    from config import load_phase2_settings
    from create_hubstudio_environment import create_hubstudio_environment
    from start_hubstudio_browser import stop_then_start_browser
    from connect_browser import connect_browser
    from open_signup_page import open_signup_page
    from verify_page import verify_page
    from apply_signup_profile import apply_outlook_signup_profile
    from ms_hold_challenge import try_ms_accessible_hold_challenge
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
    from .archive_store import append_archive_record, read_latest_phase1_user_profile
    from .config import load_hubstudio_env_create_config
    from .config import load_phase2_settings
    from .create_hubstudio_environment import create_hubstudio_environment
    from .start_hubstudio_browser import stop_then_start_browser
    from .connect_browser import connect_browser
    from .open_signup_page import open_signup_page
    from .verify_page import verify_page
    from .apply_signup_profile import apply_outlook_signup_profile
    from .ms_hold_challenge import try_ms_accessible_hold_challenge
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
        archive_path, archive_ref = append_archive_record(
            log_dir=cfg.log_dir,
            phase="phase0_env_create",
            payload={
                "containerCode": api_data.get("containerCode"),
                "environment_name": env_name,
                "region": cfg.region,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "success": True,
            },
        )
        return (
            step_result(
                success=True,
                step="hubstudio_env_creation",
                message="T-005/T-009完成：Hubstudio环境创建成功并已留档",
                data={
                    "site_name": cfg.site_name,
                    "region": cfg.region,
                    "sequence_key": alloc.key,
                    "allocated_sequence": alloc.sequence,
                    "environment_name": env_name,
                    "state_file": str(cfg.log_dir / STATE_FILE_NAME),
                    "container_code": api_data.get("containerCode"),
                    "archive_path": archive_path,
                    "archive_ref": archive_ref,
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
        result, page = run_phase1_user_profile(seed=seed)
        if result["success"]:
            # T-P1-006: 按当前约定，archive 可包含明文 password（日志仍脱敏）。
            from pathlib import Path
            import os
            project_root = Path(__file__).resolve().parent.parent
            log_dir = project_root / os.getenv("LOG_DIR", "logs")
            archive_path, archive_ref = append_archive_record(
                log_dir=log_dir,
                phase="phase1_user_profile",
                payload={
                    "first_name": result["data"].get("first_name"),
                    "last_name": result["data"].get("last_name"),
                    "birth_date": result["data"].get("birth_date"),
                    "account": result["data"].get("account"),
                    "password": result["data"].get("password"),
                    "generated_at": datetime.now().isoformat(timespec="seconds"),
                    "success": True,
                },
            )
            result["data"]["archive_path"] = archive_path
            result["data"]["archive_ref"] = archive_ref
        return result, page
    except Exception as exc:
        return (
            step_result(
                success=False,
                step="outlook_user_profile",
                message="T-P1-003/T-P1-006失败：生成用户信息或留档失败",
                error=f"{type(exc).__name__}: {exc}",
            ),
            None,
        )


def run_phase2_outlook_signup_page() -> tuple[StepResult, Any | None]:
    """
    该函数负责执行 Phase-2 流程，主要步骤如下：
    1. 启动指定环境下的浏览器（通过 Hubstudio 环境 ID，或用 cdp_url_override 直连），获取调试端口；
    2. 通过 Playwright CDP 连接此浏览器，获取页面对象；
    3. 打开 Outlook 注册页面并校验页面（open_signup_page、verify_page）；
    4. 读取 phase-1 留档，将用户信息填入注册页（apply_outlook_signup_profile，不提交最终开户）；
    5. 成功时写入 phase-2 留档；全程使用结构化 StepResult。

    返回:
        Tuple[StepResult, Any | None]
        - StepResult: 结构化描述结果，包括每一步的 success、step 名、message、附加说明、错误原因等
        - Any | None: 可能返回的 page 对象，失败时为 None
    """
    from pathlib import Path
    import re
    from urllib.parse import urlparse

    from playwright.sync_api import sync_playwright

    try:
        p2 = load_phase2_settings()
        screenshots_dir: Path = p2.screenshots_dir
        timeout_ms: int = p2.page_load_timeout_ms

        # 从 URL 推导一个稳定的“期望模式”，用于 verify_page 的 regex search
        parsed = urlparse(p2.outlook_register_url)
        expected_url_pattern = re.escape(parsed.netloc + parsed.path)

        with sync_playwright() as pw:
            # 判断 p2.cdp_url_override 是否存在，优先用 cdp_url_override 直连
            if p2.cdp_url_override:
                cdp_url = p2.cdp_url_override
            else:
                # 如无 cdp_url_override，则通过 p2.container_code（即“环境ID”）启动 Hubstudio 容器
                # 环境ID 由 p2.container_code 传入
                assert p2.container_code is not None  # 环境ID 必须传入
                try:
                    # 官方 start 成功体无可靠的「已在运行」标志；已开时常报业务码（如 -10013）。
                    # 统一先 best-effort browser/stop，再 start，以拿到新的 debuggingPort。
                    start_data = stop_then_start_browser(
                        api_base=p2.hubstudio_api_base,
                        container_code=p2.container_code,
                    )
                except Exception as exc:
                    return (
                        step_result(
                            success=False,
                            step="hubstudio_browser_start",
                            message="phase-2失败：按环境 ID 调用 browser/stop→start 未成功",
                            data={"container_code": p2.container_code},
                            error=f"{type(exc).__name__}: {exc}",
                        ),
                        None,
                    )
                # 拿到环境已打开后的调试端口
                port = start_data.get("debuggingPort")
                cdp_url = f"http://127.0.0.1:{int(port)}"

            connect_res, objs = connect_browser(
                pw=pw,
                cdp_url=cdp_url,
            )
            if not connect_res["success"]:
                return connect_res, None

            browser = objs["browser"]
            page = objs["page"]
            # CDP 附着页仍可能沿用 Playwright 默认 30s，与 PAGE_LOAD_TIMEOUT_MS 对齐
            page.set_default_navigation_timeout(timeout_ms)
            page.set_default_timeout(timeout_ms)
            try:
                open_res = open_signup_page(
                    page=page,
                    url=p2.outlook_register_url,
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
                if not verify_res["success"]:
                    return verify_res, None

                vdata = verify_res["data"]
                profile = read_latest_phase1_user_profile(p2.log_dir)
                if not profile:
                    return (
                        step_result(
                            success=False,
                            step="phase2_user_profile",
                            message="phase-2失败：缺少 phase-1 成功留档（请先运行 phase-1 或检查 logs/archive）",
                            data={"hint": "python src/main.py --phase1"},
                            error="Phase1ArchiveMissing",
                        ),
                        None,
                    )

                apply_res = apply_outlook_signup_profile(
                    page=page,
                    profile=profile,
                    email_domain=p2.outlook_email_domain,
                    form_step_timeout_ms=p2.phase2_form_timeout_ms,
                    action_delay_ms=p2.phase2_action_delay_ms,
                    chrome_password_prompt=p2.chrome_password_prompt,
                    screenshots_dir=screenshots_dir,
                )
                if not apply_res["success"]:
                    return apply_res, None

                adata = apply_res["data"]
                hold_res = try_ms_accessible_hold_challenge(
                    page,
                    enabled=p2.phase2_try_hold_challenge,
                    form_step_timeout_ms=p2.phase2_form_timeout_ms,
                    after_accessible_wait_ms=p2.phase2_hold_after_accessible_ms,
                    hold_press_ms=p2.phase2_hold_press_duration_ms,
                    chrome_password_prompt=p2.chrome_password_prompt,
                    screenshots_dir=screenshots_dir,
                    refind_challenge_root_before_hold=p2.phase2_hold_refind_root_before_press,
                )
                if not hold_res["success"]:
                    return hold_res, None
                hdata = hold_res.get("data") or {}

                # phase-2 冒烟成功留档（与 design §10.8 一致；不写密码）
                archive_path, archive_ref = append_archive_record(
                    log_dir=p2.log_dir,
                    phase="phase2_signup_smoke",
                    payload={
                        "success": True,
                        "container_code": p2.container_code,
                        "used_cdp_url_override": p2.cdp_url_override is not None,
                        "current_url": vdata.get("current_url"),
                        "url_ok": vdata.get("url_ok"),
                        "element_ok": vdata.get("element_ok"),
                        "element_hit": vdata.get("element_hit"),
                        "steps_completed": adata.get("steps_completed"),
                        "email_used": adata.get("email_used"),
                        "hold_challenge": hdata,
                        "verified_at": datetime.now().isoformat(timespec="seconds"),
                    },
                )
                out = dict(apply_res)
                out["data"] = {
                    **vdata,
                    **adata,
                    **hdata,
                    "archive_path": archive_path,
                    "archive_ref": archive_ref,
                }
                msg_tail = "；页面校验已通过；已写入 phase-2 留档"
                if hdata.get("skipped"):
                    msg_tail += "（人机验证未触发或未启用）"
                else:
                    msg_tail += "；" + hold_res["message"]
                    out["step"] = hold_res["step"]
                out["message"] = apply_res["message"] + msg_tail
                return out, None
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
