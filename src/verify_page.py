"""T-006：校验 URL 与注册相关元素（当前为占位实现）。"""

from typing import Any

from src.step_result import StepResult, step_result


def verify_page(
    _page: Any,
    _expected_url_pattern: str | None = None,
) -> StepResult:
    """T-003 仅占位。"""
    return step_result(
        success=False,
        step="verify_page",
        message="未实现：等待 T-006 URL + DOM 双校验",
        error="NotImplemented",
    )
