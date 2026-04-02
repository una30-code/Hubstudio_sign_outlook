"""统一返回结构的工厂函数。"""

from src.step_result import step_result


def test_step_result_defaults_empty_data() -> None:
    r = step_result(success=True, step="test", message="ok")
    assert r["success"] is True
    assert r["data"] == {}
    assert r["error"] is None
    assert r["screenshot_path"] is None


def test_step_result_with_data_and_error() -> None:
    r = step_result(
        success=False,
        step="open_signup_page",
        message="timeout",
        data={"timeout_ms": 3000},
        error="NavigationTimeout",
        screenshot_path="screenshots/x.png",
    )
    assert r["data"]["timeout_ms"] == 3000
    assert r["error"] == "NavigationTimeout"
