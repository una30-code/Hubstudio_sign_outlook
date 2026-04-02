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

DEFAULT_PAGE_LOAD_TIMEOUT_MS = 30000


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

