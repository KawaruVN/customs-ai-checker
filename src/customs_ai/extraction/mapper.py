import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

_DIGITS_ONLY_RE = re.compile(r"^[0-9]+$")
_DATE_RE = re.compile(r"^(\d{4})([-/.]){1}(\d{2})\2(\d{2})$")


def parse_decimal(value: Any) -> Decimal | None:
    """Strict lexical parser converting a raw numeric representation to Decimal.

    Safety contract:
    - Safe integer: "1200" -> Decimal("1200")
    - Safe decimal: "1200.50" -> Decimal("1200.50")
    - Decimal comma: "12,5" -> Decimal("12.5")
    - US grouped + decimal: "1,200.50" -> Decimal("1200.50")
    - EU grouped + decimal: "1.200,50" -> Decimal("1200.50")

    Unsafe / ambiguous / invalid forms return None:
    - Non-finite Decimals: Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity") -> None
    - Ambiguous single comma: "1,200" -> None
    - Ambiguous single dot: "1.200" -> None
    - Repeated grouping only: "1,200,000" -> None, "1.200.000" -> None
    - Formulas: "=B4*C4" -> None
    - Arbitrary non-numeric text: "abc1200" -> None, "USD 1200" -> None
    - Blank / None: None -> None, "" -> None

    Never strips arbitrary non-numeric characters to parse remaining digits.
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value if value.is_finite() else None

    if isinstance(value, int) and not isinstance(value, bool):
        return Decimal(value)

    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    # Reject formulas
    if s.startswith("="):
        return None

    # Optional leading sign
    sign = ""
    if s[0] in ("+", "-"):
        sign = s[0]
        s = s[1:].strip()
        if not s:
            return None

    # Reject any character that is not a digit, comma, or dot
    for ch in s:
        if ch not in "0123456789.,":
            return None

    has_dot = "." in s
    has_comma = "," in s

    # Case 1: Plain integer (no dot, no comma)
    if not has_dot and not has_comma:
        try:
            d = Decimal(f"{sign}{s}")
            return d if d.is_finite() else None
        except (InvalidOperation, TypeError):
            return None

    # Case 2: Both dot and comma are present
    if has_dot and has_comma:
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")

        if last_dot > last_comma:
            # Format: US grouped + decimal dot, e.g. "1,200.50" or "1,200,000.50"
            parts_before_dot = s[:last_dot].split(",")
            decimal_part = s[last_dot + 1 :]

            if not decimal_part or not _DIGITS_ONLY_RE.match(decimal_part):
                return None

            if not parts_before_dot[0] or not (1 <= len(parts_before_dot[0]) <= 3):
                return None
            if not _DIGITS_ONLY_RE.match(parts_before_dot[0]):
                return None

            for group in parts_before_dot[1:]:
                if len(group) != 3 or not _DIGITS_ONLY_RE.match(group):
                    return None

            normalized_str = f"{sign}{''.join(parts_before_dot)}.{decimal_part}"
            try:
                d = Decimal(normalized_str)
                return d if d.is_finite() else None
            except (InvalidOperation, TypeError):
                return None

        else:
            # Format: EU grouped + decimal comma, e.g. "1.200,50" or "1.200.000,50"
            parts_before_comma = s[:last_comma].split(".")
            decimal_part = s[last_comma + 1 :]

            if not decimal_part or not _DIGITS_ONLY_RE.match(decimal_part):
                return None

            if not parts_before_comma[0] or not (1 <= len(parts_before_comma[0]) <= 3):
                return None
            if not _DIGITS_ONLY_RE.match(parts_before_comma[0]):
                return None

            for group in parts_before_comma[1:]:
                if len(group) != 3 or not _DIGITS_ONLY_RE.match(group):
                    return None

            normalized_str = f"{sign}{''.join(parts_before_comma)}.{decimal_part}"
            try:
                d = Decimal(normalized_str)
                return d if d.is_finite() else None
            except (InvalidOperation, TypeError):
                return None

    # Case 3: Only ONE kind of separator is present (either dot or comma)
    sep = "." if has_dot else ","
    count = s.count(sep)

    # Repeated grouping only without decimal separator is ambiguous
    if count > 1:
        return None

    # Separator appears exactly once
    left, right = s.split(sep)
    if not left or not right:
        return None
    if not _DIGITS_ONLY_RE.match(left) or not _DIGITS_ONLY_RE.match(right):
        return None

    # Ambiguity check:
    # 1-3 digits before separator and exactly 3 digits after separator
    # (e.g. "1,200", "1.200", "123,456", "123.456") could be thousands grouping or 3 decimals.
    if 1 <= len(left) <= 3 and len(right) == 3:
        return None

    try:
        d = Decimal(f"{sign}{left}.{right}")
        return d if d.is_finite() else None
    except (InvalidOperation, TypeError):
        return None


def parse_date(value: Any) -> date | None:
    """Strict lexical parser converting a raw date representation to datetime.date.

    Safe explicit forms:
    - YYYY-MM-DD
    - YYYY/MM/DD
    - YYYY.MM.DD
    - Typed datetime (naive or timezone-aware): converted to pure calendar date (.date())
      to avoid Pydantic date_from_datetime_inexact validation errors on CanonicalField[date].
    - Typed date: passed through unchanged.

    Unsafe / ambiguous / invalid forms return None:
    - Ambiguous day/month (e.g. 01/02/2026, 11-09-2026)
    - Invalid calendar dates (e.g. 2026-02-30, 2026-13-01)
    - Arbitrary text
    - Blank / None
    """
    if value is None:
        return None

    # datetime inherits from date, so check datetime first to convert to pure date
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    match = _DATE_RE.match(s)
    if not match:
        return None

    year_str, _, month_str, day_str = match.groups()
    try:
        return date(int(year_str), int(month_str), int(day_str))
    except ValueError:
        return None
