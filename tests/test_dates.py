from __future__ import annotations

import datetime as _dt

import pytest

from restaurant_bot.core.dates import BadDateFormat, DateInPast, parse_dinner_date

TODAY = _dt.date(2026, 9, 6)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12.09.2026", _dt.date(2026, 9, 12)),
        ("  12.09.2026 ", _dt.date(2026, 9, 12)),
        ("2.9.2027", _dt.date(2027, 9, 2)),  # single-digit day/month
        ("2026-09-12", _dt.date(2026, 9, 12)),
        ("12.09.", _dt.date(2026, 9, 12)),
        ("12.09", _dt.date(2026, 9, 12)),
        ("06.09.2026", _dt.date(2026, 9, 6)),  # today is allowed
        ("01.01.", _dt.date(2027, 1, 1)),  # month/day already passed -> next year
        ("06.09.", _dt.date(2026, 9, 6)),  # today, no year
    ],
)
def test_parse_ok(raw: str, expected: _dt.date) -> None:
    assert parse_dinner_date(raw, today=TODAY) == expected


@pytest.mark.parametrize("raw", ["05.09.2026", "2026-09-05", "01.01.2020", "02.09.2026"])
def test_parse_in_past(raw: str) -> None:
    with pytest.raises(DateInPast):
        parse_dinner_date(raw, today=TODAY)


@pytest.mark.parametrize(
    "raw",
    ["garbage", "12/09/2026", "2026-13-40", "", "  ", "32.01.2026", "2026-02-30", "12.2026"],
)
def test_parse_bad_format(raw: str) -> None:
    with pytest.raises(BadDateFormat):
        parse_dinner_date(raw, today=TODAY)
