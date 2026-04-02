"""Validation for phase-0 Hubstudio environment creation config."""

from __future__ import annotations

from dataclasses import dataclass

if __package__ in {None, ""}:
    from config import HubstudioEnvCreateConfig
    from sequence_state import build_environment_name
else:
    from .config import HubstudioEnvCreateConfig
    from .sequence_state import build_environment_name


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]


def validate_hubstudio_env_create_config(
    cfg: HubstudioEnvCreateConfig,
    *,
    allocated_sequence: int,
    environment_name: str,
) -> ValidationResult:
    errors: list[str] = []

    if not cfg.site_name.strip():
        errors.append("site_name must not be empty")
    if not cfg.region.strip():
        errors.append("region must not be empty")
    if cfg.name_sequence_start < 1:
        errors.append("name_sequence_start must be >= 1")

    if not cfg.proxy.host.strip():
        errors.append("proxy.host must not be empty")
    if cfg.proxy.port < 1 or cfg.proxy.port > 65535:
        errors.append("proxy.port must be between 1 and 65535")
    if not cfg.proxy.username.strip():
        errors.append("proxy.username must not be empty")
    if not cfg.proxy.password.strip():
        errors.append("proxy.password must not be empty")

    if not cfg.fingerprint.ua.strip():
        errors.append("fingerprint.ua must not be empty")
    if not cfg.fingerprint.ua_version.strip():
        errors.append("fingerprint.ua_version must not be empty")

    if allocated_sequence < 1:
        errors.append("allocated_sequence must be >= 1")

    expected = build_environment_name(cfg.site_name, allocated_sequence, cfg.region)
    if len(environment_name) < 1 or len(environment_name) > 60:
        errors.append("environment_name length must be 1-60")
    if environment_name != expected:
        errors.append(
            "environment_name must match "
            f"'{expected}' for current site/sequence/region/today"
        )

    return ValidationResult(ok=not errors, errors=errors)
