"""流水线各步统一返回的字典结构（与设计文档一致）。"""

from typing import Any, TypedDict


class StepResult(TypedDict):
    success: bool
    step: str
    message: str
    data: dict[str, Any]
    error: str | None
    screenshot_path: str | None


def step_result(
    *,
    success: bool,
    step: str,
    message: str,
    data: dict[str, Any] | None = None,
    error: str | None = None,
    screenshot_path: str | None = None,
) -> StepResult:
    return {
        "success": success,
        "step": step,
        "message": message,
        "data": data or {},
        "error": error,
        "screenshot_path": screenshot_path,
    }
