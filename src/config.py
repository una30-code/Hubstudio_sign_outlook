"""配置加载模块（仅 phase-0 / Hubstudio 环境创建）。"""

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv

# 项目根目录（包含 pyproject.toml、logs、screenshots）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_SCREENSHOTS_DIR = "screenshots"
DEFAULT_LOG_DIR = "logs"
DEFAULT_SITE_NAME = "outlook"
DEFAULT_NAME_SEQUENCE_START = 1
DEFAULT_UA_VERSION = "124.0.0.0"


@dataclass(frozen=True)
class ProxyConfig:
    host: str
    port: int
    username: str
    password: str


@dataclass(frozen=True)
class FingerprintConfig:
    ua: str
    ua_version: str


@dataclass(frozen=True)
class HubstudioEnvCreateConfig:
    hubstudio_api_base: str
    log_dir: Path
    screenshots_dir: Path
    site_name: str
    region: str
    name_sequence_start: int
    environment_name: str | None
    proxy: ProxyConfig
    fingerprint: FingerprintConfig


def _require(m: Mapping[str, str], key: str) -> str:
    v = m.get(key, "").strip()
    if not v:
        raise ValueError(f"missing or empty environment variable: {key}")
    return v


def _resolve_dir(root: Path, value: str, default_rel: str) -> Path:
    rel = value.strip() or default_rel
    p = Path(rel)
    return (root / p).resolve() if not p.is_absolute() else p.resolve()


def _int_with_default(raw: Any, default: int) -> int:
    if raw is None:
        return default
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    if not text:
        return default
    return int(text)


def _chrome_password_prompt_mode(raw: str | None) -> str:
    """
    将 PHASE2_CHROME_PASSWORD_PROMPT 配置解析为内置的处理模式字符串。

    示例输入与行为：
    - raw 为 None 或空字符串，返回 "skip"（暂不处理浏览器密码条）
    - raw 为 "save"、"update"、"1"、"yes"、"true"（不区分大小写），返回 "save"
    - raw 为 "dismiss"、"no"、"none"、"0"、"false"，返回 "dismiss"
    - raw 为 "skip"、"off"，返回 "skip"
    - 其他未识别值一律默认返回 "skip"

    该模式决定自动化时对于 Chrome 的密码保存弹窗如何响应：
        - "save"    ：尝试点击“保存/更新密码”
        - "dismiss" ：尝试关闭/跳过弹窗，不保存密码
        - "skip"    ：流程不处理此弹窗

    参数:
        raw: 配置项字符串（一般自 .env 或用户输入）

    返回:
        str: 标准模式（"save" | "dismiss" | "skip"）
    """
    if raw is None or not str(raw).strip():
        return "skip"
    v = str(raw).strip().lower()
    if v in {"save", "update", "1", "yes", "true"}:
        return "save"
    if v in {"dismiss", "no", "none", "0", "false"}:
        return "dismiss"
    if v in {"skip", "off"}:
        return "skip"
    return "skip"


def _get_nested(data: Mapping[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(key)
    return cur


def _parse_proxy_raw(proxy_raw: str) -> ProxyConfig:
    parts = [p.strip() for p in proxy_raw.split(":")]
    if len(parts) != 4 or any(not p for p in parts):
        raise ValueError("proxy_raw must be host:port:user:pass")
    return ProxyConfig(
        host=parts[0],
        port=int(parts[1]),
        username=parts[2],
        password=parts[3],
    )


def _load_config_mapping_from_path(config_path: Path) -> Mapping[str, Any]:
    if not config_path.exists():
        raise ValueError(f"config file not found: {config_path}")
    text = config_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"config file is empty: {config_path}")

    suffix = config_path.suffix.lower()
    if suffix == ".json":
        parsed = json.loads(text)
    elif suffix in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ValueError(
                "YAML config requires PyYAML, please install it or use JSON"
            ) from exc
        parsed = yaml.safe_load(text)
    else:
        raise ValueError(f"unsupported config format: {config_path.suffix}")

    if not isinstance(parsed, Mapping):
        raise ValueError("hubstudio_env_create_config must be an object/dict")
    return parsed


def _load_hubstudio_env_create_mapping(
    environ: Mapping[str, str], config: Mapping[str, Any] | None, config_path: str | Path | None
) -> Mapping[str, Any]:
    if config is not None:
        return config

    if config_path is not None:
        return _load_config_mapping_from_path(Path(config_path))

    raw_json = environ.get("HUBSTUDIO_ENV_CREATE_CONFIG_JSON", "").strip()
    if raw_json:
        parsed = json.loads(raw_json)
        if not isinstance(parsed, Mapping):
            raise ValueError("HUBSTUDIO_ENV_CREATE_CONFIG_JSON must be an object")
        return parsed

    return {}


def load_hubstudio_env_create_config(
    *,
    environ: Mapping[str, str] | None = None,
    config: Mapping[str, Any] | None = None,
    config_path: str | Path | None = None,
) -> HubstudioEnvCreateConfig:
    """加载 Hubstudio 环境创建配置（T-002）。

    优先级：
    1. 显式传入 config（字典）
    2. config_path（json/yaml 文件）
    3. 环境变量 HUBSTUDIO_ENV_CREATE_CONFIG_JSON（json 字符串）
    4. 回退为仅从环境变量读取 site/region/proxy 等扁平字段
    """
    if environ is None:
        load_dotenv(PROJECT_ROOT / ".env")
        environ = os.environ

    mapping = _load_hubstudio_env_create_mapping(environ, config, config_path)

    site_name = (
        str(mapping.get("site_name", "")).strip()
        or environ.get("SITE_NAME", "").strip()
        or DEFAULT_SITE_NAME
    )
    region = str(mapping.get("region", "")).strip() or environ.get("REGION", "").strip()
    if not region:
        raise ValueError("missing required field: region")

    name_sequence_start = _int_with_default(
        mapping.get("name_sequence_start", environ.get("NAME_SEQUENCE_START")),
        DEFAULT_NAME_SEQUENCE_START,
    )

    environment_name_raw = str(mapping.get("environment_name", "")).strip()
    environment_name = environment_name_raw or None

    proxy_host = str(_get_nested(mapping, "proxy", "host") or environ.get("PROXY_HOST", "")).strip()
    proxy_port_raw = _get_nested(mapping, "proxy", "port")
    if proxy_port_raw is None:
        proxy_port_raw = environ.get("PROXY_PORT", "")
    proxy_username = str(
        _get_nested(mapping, "proxy", "username") or environ.get("PROXY_USERNAME", "")
    ).strip()
    proxy_password = str(
        _get_nested(mapping, "proxy", "password") or environ.get("PROXY_PASSWORD", "")
    ).strip()

    if proxy_host and proxy_port_raw and proxy_username and proxy_password:
        proxy = ProxyConfig(
            host=proxy_host,
            port=int(str(proxy_port_raw).strip()),
            username=proxy_username,
            password=proxy_password,
        )
    else:
        proxy_raw = str(mapping.get("proxy_raw", "")).strip() or environ.get(
            "PROXY_RAW", ""
        ).strip()
        if not proxy_raw:
            raise ValueError(
                "missing proxy config: provide proxy.host/port/username/password or proxy_raw"
            )
        proxy = _parse_proxy_raw(proxy_raw)

    fp_ua = str(_get_nested(mapping, "fingerprint", "ua") or environ.get("FINGERPRINT_UA", "")).strip()
    fp_ua_version = str(
        _get_nested(mapping, "fingerprint", "ua_version")
        or environ.get("FINGERPRINT_UA_VERSION", "")
    ).strip()
    if not fp_ua:
        # 与 design.md 示例一致，给出默认 UA
        fp_ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    if not fp_ua_version:
        fp_ua_version = DEFAULT_UA_VERSION

    root = PROJECT_ROOT
    return HubstudioEnvCreateConfig(
        hubstudio_api_base=_require(environ, "HUBSTUDIO_API_BASE"),
        log_dir=_resolve_dir(root, environ.get("LOG_DIR", "").strip(), DEFAULT_LOG_DIR),
        screenshots_dir=_resolve_dir(
            root, environ.get("SCREENSHOTS_DIR", "").strip(), DEFAULT_SCREENSHOTS_DIR
        ),
        site_name=site_name,
        region=region,
        name_sequence_start=name_sequence_start,
        environment_name=environment_name,
        proxy=proxy,
        fingerprint=FingerprintConfig(ua=fp_ua, ua_version=fp_ua_version),
    )


# =============================================================================
# Backward compatibility (tests /旧接口)
# =============================================================================

# NOTE:
# 仓库早期曾有“phase-1 页面自动化”接口（`load_settings` 等）。
# 当前 phase-0/1/2 重构后主逻辑不再使用这些字段，但现有测试仍引用。

DEFAULT_PAGE_LOAD_TIMEOUT_MS = 100_000
# 页面已打开后：单步填表/点击等待（毫秒），避免沿用整页导航超时导致「填邮箱前空等过久」
DEFAULT_PHASE2_FORM_TIMEOUT_MS = 15_000
# 每一步主操作后的间隔（毫秒），降低操作过快带来的不稳定；0 表示不额外等待
DEFAULT_PHASE2_ACTION_DELAY_MS = 1_000


@dataclass(frozen=True)
class Settings:
    hubstudio_cdp_url: str
    outlook_register_url: str
    page_load_timeout_ms: int
    screenshots_dir: Path
    log_dir: Path


def load_settings(*, environ: Mapping[str, str] | None = None) -> Settings:
    """加载 CDP + Outlook 注册页参数（兼容旧测试）。"""

    if environ is None:
        load_dotenv(PROJECT_ROOT / ".env")
        environ = os.environ

    hubstudio_cdp_url = _require(environ, "HUBSTUDIO_CDP_URL")
    outlook_register_url = _require(environ, "OUTLOOK_REGISTER_URL")
    page_load_timeout_ms = _int_with_default(
        environ.get("PAGE_LOAD_TIMEOUT_MS"), DEFAULT_PAGE_LOAD_TIMEOUT_MS
    )

    root = PROJECT_ROOT
    screenshots_dir = _resolve_dir(
        root, environ.get("SCREENSHOTS_DIR", "").strip(), DEFAULT_SCREENSHOTS_DIR
    )
    log_dir = _resolve_dir(
        root, environ.get("LOG_DIR", "").strip(), DEFAULT_LOG_DIR
    )
    return Settings(
        hubstudio_cdp_url=hubstudio_cdp_url,
        outlook_register_url=outlook_register_url,
        page_load_timeout_ms=page_load_timeout_ms,
        screenshots_dir=screenshots_dir,
        log_dir=log_dir,
    )


@dataclass(frozen=True)
class Phase2Settings:
    """phase-2：按环境 ID 调 browser/start，或用 CDP URL 直连（调试）。"""

    hubstudio_api_base: str
    container_code: str | None
    outlook_register_url: str
    outlook_email_domain: str
    page_load_timeout_ms: int
    phase2_form_timeout_ms: int
    phase2_action_delay_ms: int
    chrome_password_prompt: str
    screenshots_dir: Path
    log_dir: Path
    cdp_url_override: str | None


def load_phase2_settings(*, environ: Mapping[str, str] | None = None) -> Phase2Settings:
    """加载 phase-2 参数。默认先 browser/start；若设置 HUBSTUDIO_CDP_URL 则跳过启动、直接连 CDP。"""

    if environ is None:
        load_dotenv(PROJECT_ROOT / ".env")
        environ = os.environ

    root = PROJECT_ROOT
    log_dir = _resolve_dir(root, environ.get("LOG_DIR", "").strip(), DEFAULT_LOG_DIR)
    screenshots_dir = _resolve_dir(
        root, environ.get("SCREENSHOTS_DIR", "").strip(), DEFAULT_SCREENSHOTS_DIR
    )
    outlook_register_url = _require(environ, "OUTLOOK_REGISTER_URL")
    outlook_email_domain = (environ.get("OUTLOOK_EMAIL_DOMAIN", "") or "").strip() or "outlook.com"
    outlook_email_domain = outlook_email_domain.lstrip("@")
    page_load_timeout_ms = _int_with_default(
        environ.get("PAGE_LOAD_TIMEOUT_MS"), DEFAULT_PAGE_LOAD_TIMEOUT_MS
    )
    phase2_form_timeout_ms = _int_with_default(
        environ.get("PHASE2_FORM_TIMEOUT_MS"), DEFAULT_PHASE2_FORM_TIMEOUT_MS
    )
    phase2_action_delay_ms = max(
        0,
        _int_with_default(
            environ.get("PHASE2_ACTION_DELAY_MS"), DEFAULT_PHASE2_ACTION_DELAY_MS
        ),
    )
    chrome_password_prompt = _chrome_password_prompt_mode(
        environ.get("PHASE2_CHROME_PASSWORD_PROMPT")
    )

    cdp_override = environ.get("HUBSTUDIO_CDP_URL", "").strip() or None
    api_base = environ.get("HUBSTUDIO_API_BASE", "").strip()

    container = (
        environ.get("HUBSTUDIO_CONTAINER", "").strip()
        or environ.get("CONTAINER_CODE", "").strip()
    )
    if not container and not cdp_override:
        from archive_store import read_latest_phase0_container_code

        container = read_latest_phase0_container_code(log_dir) or ""

    if cdp_override:
        return Phase2Settings(
            hubstudio_api_base=api_base,
            container_code=container or None,
            outlook_register_url=outlook_register_url,
            outlook_email_domain=outlook_email_domain,
            page_load_timeout_ms=page_load_timeout_ms,
            phase2_form_timeout_ms=phase2_form_timeout_ms,
            phase2_action_delay_ms=phase2_action_delay_ms,
            chrome_password_prompt=chrome_password_prompt,
            screenshots_dir=screenshots_dir,
            log_dir=log_dir,
            cdp_url_override=cdp_override,
        )

    if not api_base:
        raise ValueError(
            "phase-2 requires HUBSTUDIO_API_BASE for POST /api/v1/browser/start, "
            "or set HUBSTUDIO_CDP_URL to connect without starting via API"
        )
    if not container:
        raise ValueError(
            "phase-2 requires HUBSTUDIO_CONTAINER or CONTAINER_CODE, "
            "or a phase-0 archive line with success and containerCode, "
            "unless HUBSTUDIO_CDP_URL is set"
        )
    return Phase2Settings(
        hubstudio_api_base=api_base,
        container_code=container,
        outlook_register_url=outlook_register_url,
        outlook_email_domain=outlook_email_domain,
        page_load_timeout_ms=page_load_timeout_ms,
        phase2_form_timeout_ms=phase2_form_timeout_ms,
        phase2_action_delay_ms=phase2_action_delay_ms,
        chrome_password_prompt=chrome_password_prompt,
        screenshots_dir=screenshots_dir,
        log_dir=log_dir,
        cdp_url_override=None,
    )

