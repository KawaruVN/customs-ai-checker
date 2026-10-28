from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from customs_ai.domain.enums import ValueOrigin
from customs_ai.domain.schema import CanonicalField
from customs_ai.extraction.mapper import parse_date, parse_decimal


# =============================================================================
# Decimal Parsing Tests
# =============================================================================

def test_parse_decimal_plain_integer():
    assert parse_decimal("1200") == Decimal("1200")
    assert parse_decimal("0") == Decimal("0")
    assert parse_decimal("+1200") == Decimal("1200")
    assert parse_decimal("-500") == Decimal("-500")


def test_parse_decimal_plain_decimal():
    assert parse_decimal("1200.50") == Decimal("1200.50")
    assert parse_decimal("12.5") == Decimal("12.5")
    assert parse_decimal("0.05") == Decimal("0.05")


def test_parse_decimal_decimal_comma():
    assert parse_decimal("12,5") == Decimal("12.5")
    assert parse_decimal("1200,50") == Decimal("1200.50")
    assert parse_decimal("0,05") == Decimal("0.05")


def test_parse_decimal_us_grouped_with_decimal():
    assert parse_decimal("1,200.50") == Decimal("1200.50")
    assert parse_decimal("1,200,000.50") == Decimal("1200000.50")
    assert parse_decimal("25,000.00") == Decimal("25000.00")


def test_parse_decimal_eu_grouped_with_decimal():
    assert parse_decimal("1.200,50") == Decimal("1200.50")
    assert parse_decimal("1.200.000,50") == Decimal("1200000.50")
    assert parse_decimal("25.000,00") == Decimal("25000.00")


def test_parse_decimal_ambiguous_single_comma_and_dot_returns_none():
    # Ambiguous single comma (could be thousands separator or 3 decimal places)
    assert parse_decimal("1,200") is None
    assert parse_decimal("123,456") is None

    # Ambiguous single dot (could be thousands separator or 3 decimal places)
    assert parse_decimal("1.200") is None
    assert parse_decimal("123.456") is None


def test_parse_decimal_repeated_grouping_only_returns_none():
    assert parse_decimal("1,200,000") is None
    assert parse_decimal("1.200.000") is None


def test_parse_decimal_formula_arbitrary_text_and_blank_return_none():
    assert parse_decimal("=B4*C4") is None
    assert parse_decimal("abc1200") is None
    assert parse_decimal("USD 1200") is None
    assert parse_decimal("1200 USD") is None
    assert parse_decimal("") is None
    assert parse_decimal("   ") is None
    assert parse_decimal(None) is None


def test_parse_decimal_pass_through_existing_types():
    assert parse_decimal(Decimal("1200.50")) == Decimal("1200.50")
    assert parse_decimal(1200) == Decimal("1200")
    assert parse_decimal(True) is None  # bool should not be treated as int


def test_parse_decimal_rejects_non_finite_decimals():
    """Regression test for non-finite Decimal objects (NaN, sNaN, Infinity)."""
    assert parse_decimal(Decimal("NaN")) is None
    assert parse_decimal(Decimal("sNaN")) is None
    assert parse_decimal(Decimal("Infinity")) is None
    assert parse_decimal(Decimal("-Infinity")) is None


# =============================================================================
# Date Parsing Tests
# =============================================================================

def test_parse_date_safe_iso_like_formats():
    assert parse_date("2026-05-12") == date(2026, 5, 12)
    assert parse_date("2026/05/12") == date(2026, 5, 12)
    assert parse_date("2026.05.12") == date(2026, 5, 12)
    assert parse_date(date(2026, 5, 12)) == date(2026, 5, 12)


def test_parse_date_handles_datetime_types():
    """Regression test: datetime must be converted to pure date to satisfy CanonicalField[date]."""
    naive_dt = datetime(2026, 5, 12, 14, 30, 45)
    parsed_naive = parse_date(naive_dt)
    assert parsed_naive == date(2026, 5, 12)
    assert type(parsed_naive) is date
    assert not isinstance(parsed_naive, datetime)

    tz_dt = datetime(2026, 5, 12, 14, 30, 45, tzinfo=timezone.utc)
    parsed_tz = parse_date(tz_dt)
    assert parsed_tz == date(2026, 5, 12)
    assert type(parsed_tz) is date

    # Ensure compatibility with CanonicalField[date] without date_from_datetime_inexact error
    field = CanonicalField[date](
        origin=ValueOrigin.EXTRACTED,
        raw_value="2026-05-12 14:30",
        source_document_id="doc_test",
        normalized_value=parsed_naive,
    )
    assert field.normalized_value == date(2026, 5, 12)


def test_parse_date_ambiguous_day_month_returns_none():
    assert parse_date("01/02/2026") is None
    assert parse_date("11-09-2026") is None
    assert parse_date("12.05.2026") is None


def test_parse_date_invalid_calendar_and_arbitrary_text_returns_none():
    assert parse_date("2026-02-30") is None  # Invalid day in Feb
    assert parse_date("2026-13-01") is None  # Invalid month
    assert parse_date("2026/04/31") is None  # April has 30 days
    assert parse_date("arbitrary text") is None
    assert parse_date("2026-05-12 extra") is None
    assert parse_date("2026-05-12 14:30:00") is None  # Raw string with time is not plain date
    assert parse_date("") is None
    assert parse_date("   ") is None
    assert parse_date(None) is None
