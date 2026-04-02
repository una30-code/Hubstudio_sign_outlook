"""Phase-1：Outlook 注册用用户信息生成（不涉及 Hubstudio/CDP/页面）。"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from datetime import date
from typing import Any

if __package__ in {None, ""}:
    from step_result import StepResult, step_result
else:
    from .step_result import StepResult, step_result


US_FIRST_NAMES = [
    "James",
    "John",
    "Robert",
    "Michael",
    "William",
    "David",
    "Richard",
    "Joseph",
    "Thomas",
    "Charles",
    "Christopher",
    "Daniel",
    "Matthew",
    "Anthony",
    "Donald",
    "Mark",
    "Paul",
    "Steven",
    "Andrew",
    "Kenneth",
    "Joshua",
    "Kevin",
    "Brian",
    "George",
    "Edward",
    "Ronald",
    "Timothy",
    "Jason",
    "Jeffrey",
    "Ryan",
    "Jacob",
    "Gary",
    "Nicholas",
    "Eric",
    "Stephen",
    "Jonathan",
    "Larry",
    "Justin",
    "Scott",
    "Brandon",
]

US_LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Miller",
    "Davis",
    "Garcia",
    "Rodriguez",
    "Wilson",
    "Martinez",
    "Anderson",
    "Taylor",
    "Thomas",
    "Hernandez",
    "Moore",
    "Martin",
    "Jackson",
    "Thompson",
    "White",
    "Lewis",
    "Lee",
    "Walker",
    "Hall",
    "Allen",
    "Young",
    "King",
    "Wright",
    "Scott",
    "Green",
    "Baker",
    "Adams",
    "Nelson",
    "Hill",
    "Ramirez",
    "Campbell",
    "Mitchell",
    "Roberts",
    "Carter",
    "Phillips",
    "Evans",
    "Turner",
    "Torres",
    "Parker",
    "Collins",
    "Edwards",
    "Stewart",
    "Flores",
    "Morris",
    "Nguyen",
    "Murphy",
    "Rivera",
    "Cook",
    "Rogers",
    "Morgan",
    "Peterson",
    "Cooper",
    "Reed",
    "Bailey",
    "Bell",
    "Gomez",
    "Kelly",
    "Howard",
    "Ward",
    "Cox",
    "Diaz",
    "Richardson",
    "Wood",
    "Watson",
    "Brooks",
    "Bennett",
    "Gray",
    "James",
    "Reyes",
    "Cruz",
    "Hughes",
    "Price",
    "Myers",
    "Long",
    "Foster",
    "Sanders",
    "Ross",
    "Morales",
    "Powell",
    "Sullivan",
    "Russell",
    "Ortiz",
    "Jenkins",
    "Gutierrez",
    "Perry",
    "Butler",
    "Barnes",
    "Fisher",
]


@dataclass(frozen=True)
class OutlookUserProfile:
    first_name: str
    last_name: str
    birth_date: date
    account: str
    password: str


def _compute_age_years(birth: date, reference: date) -> int:
    """按日历精确计算周岁（非纯年份差）。"""

    years = reference.year - birth.year
    if (reference.month, reference.day) < (birth.month, birth.day):
        years -= 1
    return years


def _safe_replace_year(d: date, year: int) -> date:
    """处理 2/29 这类跨年替换导致的 ValueError。"""

    try:
        return d.replace(year=year)
    except ValueError:
        # 仅可能发生在 2/29 -> 非闰年
        return d.replace(year=year, month=2, day=28)


def _random_birth_date(
    *,
    rng: random.Random,
    reference_date: date,
    min_age: int = 18,
    max_age: int = 55,
) -> date:
    """在给定参考日期的“周岁”范围内生成生日（含边界）。"""

    if min_age > max_age:
        raise ValueError("min_age must be <= max_age")

    start = _safe_replace_year(reference_date, reference_date.year - max_age)
    end = _safe_replace_year(reference_date, reference_date.year - min_age)
    if start > end:
        start, end = end, start

    # 通过 ordinal 采样，随后用精确 age 校验兜底（闰日边缘情况）。
    for _ in range(2000):
        d = date.fromordinal(rng.randint(start.toordinal(), end.toordinal()))
        age = _compute_age_years(d, reference_date)
        if min_age <= age <= max_age:
            return d
    raise RuntimeError("failed to generate birth_date in required age range")


def _normalize_for_account(text: str) -> str:
    """账号基础：只保留字母并转为小写，避免引入空格/符号。"""

    normalized = "".join(ch for ch in text.strip().lower() if ch.isalpha())
    return normalized


def _generate_password(
    *,
    rng: random.Random,
    length: int = 10,
) -> str:
    """密码规则：长度 10，同时包含 数字/小写/大写（至少各 1）。"""

    digits = string.digits
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    all_chars = digits + lower + upper

    # 强制三类各取 1，剩余用全集合随机，再洗牌。
    chars = [
        rng.choice(digits),
        rng.choice(lower),
        rng.choice(upper),
    ]
    chars.extend(rng.choice(all_chars) for _ in range(length - len(chars)))
    rng.shuffle(chars)
    return "".join(chars)


def _generate_account(
    *,
    rng: random.Random,
    first_name: str,
    last_name: str,
    digits_count: int = 5,
) -> str:
    """账号规则：基于姓名规范化 + 固定 5 位随机数字。"""

    base = _normalize_for_account(first_name + last_name)
    if not base:
        base = "user"

    suffix = "".join(rng.choice(string.digits) for _ in range(digits_count))
    return f"{base}{suffix}"


def generate_outlook_user_profile(
    *,
    seed: int | None = None,
    reference_date: date | None = None,
) -> OutlookUserProfile:
    """
    生成 phase-1 用户信息。

    - 姓名：美国风格 first + last
    - 生日：周岁 18~55（含边界）
    - 账号：姓名规范化 + 5 位随机数字
    - 密码：长度 10，且至少包含数字/小写/大写
    """

    reference = reference_date or date.today()
    rng = random.Random(seed) if seed is not None else random.Random()

    first_name = rng.choice(US_FIRST_NAMES)
    last_name = rng.choice(US_LAST_NAMES)
    birth = _random_birth_date(
        rng=rng,
        reference_date=reference,
        min_age=18,
        max_age=55,
    )
    password = _generate_password(rng=rng, length=10)
    account = _generate_account(rng=rng, first_name=first_name, last_name=last_name)

    profile = OutlookUserProfile(
        first_name=first_name,
        last_name=last_name,
        birth_date=birth,
        account=account,
        password=password,
    )

    # 内部自检（更早暴露偏差）
    _validate_outlook_user_profile(profile=profile, reference_date=reference)
    return profile


def _validate_outlook_user_profile(
    *,
    profile: OutlookUserProfile,
    reference_date: date,
) -> None:
    if not profile.first_name or not profile.last_name:
        raise ValueError("first_name/last_name must not be empty")

    age = _compute_age_years(profile.birth_date, reference_date)
    if not (18 <= age <= 55):
        raise ValueError(f"birth_date age out of range: age={age}")

    if len(profile.password) != 10:
        raise ValueError("password length must be 10")

    has_digit = any(ch in string.digits for ch in profile.password)
    has_lower = any(ch in string.ascii_lowercase for ch in profile.password)
    has_upper = any(ch in string.ascii_uppercase for ch in profile.password)
    if not (has_digit and has_lower and has_upper):
        raise ValueError("password must contain digit/lower/upper")

    # 账号后缀 5 位数字（严格校验）
    if len(profile.account) < 5 or not profile.account[-5:].isdigit():
        raise ValueError("account must end with 5 digits")


def outlook_user_profile_to_step_data(profile: OutlookUserProfile) -> dict[str, Any]:
    return {
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "birth_date": profile.birth_date.isoformat(),
        "account": profile.account,
        "password": profile.password,
    }


def run_phase1_user_profile(
    *,
    seed: int | None = None,
    reference_date: date | None = None,
) -> tuple[StepResult, None]:
    """对外统一 StepResult 包装，便于 pipeline/main 复用。"""

    profile = generate_outlook_user_profile(seed=seed, reference_date=reference_date)
    return (
        step_result(
            success=True,
            step="outlook_user_profile",
            message="T-P1-002完成：生成 Outlook 注册用用户信息",
            data=outlook_user_profile_to_step_data(profile),
        ),
        None,
    )

