from datetime import date

from src.outlook_user_profile import generate_outlook_user_profile


def _compute_age_years(birth: date, reference: date) -> int:
    years = reference.year - birth.year
    if (reference.month, reference.day) < (birth.month, birth.day):
        years -= 1
    return years


def test_generate_outlook_user_profile_rules_seeded() -> None:
    reference = date(2026, 4, 2)
    profile = generate_outlook_user_profile(seed=123, reference_date=reference)

    # 姓名：first + last 非空
    assert profile.first_name
    assert profile.last_name

    # 生日：18~55（含边界）
    age = _compute_age_years(profile.birth_date, reference)
    assert 18 <= age <= 55

    # 账号：基于姓名规范化 + 5 位随机数字（严格校验：结尾 5 位数字）
    assert len(profile.account) >= 5
    assert profile.account[-5:].isdigit()

    # 密码：长度 10，至少包含 digit/lower/upper
    assert len(profile.password) == 10
    assert any(ch.isdigit() for ch in profile.password)
    assert any("a" <= ch <= "z" for ch in profile.password)
    assert any("A" <= ch <= "Z" for ch in profile.password)


def test_generate_outlook_user_profile_multiple_seeds_age_range() -> None:
    reference = date(2026, 4, 2)
    for seed in [0, 1, 2, 999, 1001]:
        profile = generate_outlook_user_profile(seed=seed, reference_date=reference)
        age = _compute_age_years(profile.birth_date, reference)
        assert 18 <= age <= 55

