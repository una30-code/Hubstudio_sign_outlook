"""T-005：打开 Outlook 注册页（当前为占位实现）。"""

from typing import Any

from src.step_result import StepResult, step_result


def open_signup_page(
    _page: Any,
    _url: str,
    _timeout_ms: int,
) -> StepResult:
    """T-003 仅占位。"""
    return step_result(
        success=False,
        step="open_signup_page",
        message="未实现：等待 T-005 导航与超时",
        error="NotImplemented",
    )
