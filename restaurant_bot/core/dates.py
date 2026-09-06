"""Dinner-date parsing (T07).

The ``date`` argument of ``/start-poll`` is the *dinner* date -- informational only (Q9).
Accepted input formats (Q26):

1. ``DD.MM.YYYY``          e.g. ``12.09.2026``
2. ``DD.MM.`` / ``DD.MM``  year omitted -> next occurrence on/after ``today``
3. ISO ``YYYY-MM-DD``

Anything else -> :class:`BadDateFormat`. A date strictly before ``today`` -> :class:`DateInPast`.
"""

from __future__ import annotations

import datetime as _dt
import re

_ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DMY_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
_DM_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.?$")


class BadDateFormat(ValueError):
    """The string does not match any accepted date format."""


class DateInPast(ValueError):
    """The parsed date lies before ``today``."""


def _build(year: int, month: int, day: int) -> _dt.date:
    try:
        return _dt.date(year, month, day)
    except ValueError as exc:  # e.g. 31.02. or month 13
        raise BadDateFormat(str(exc)) from exc


def parse_dinner_date(raw: str, *, today: _dt.date, tz: object | None = None) -> _dt.date:
    """Parse ``raw`` into a :class:`datetime.date`.

    ``tz`` is accepted for call-site symmetry but not used here; callers derive ``today``
    from the configured timezone.
    """
    del tz  # documented no-op
    text = raw.strip()
    if not text:
        raise BadDateFormat("empty date")

    if m := _ISO_RE.match(text):
        return _guard_past(_build(int(m[1]), int(m[2]), int(m[3])), today)

    if m := _DMY_RE.match(text):
        return _guard_past(_build(int(m[3]), int(m[2]), int(m[1])), today)

    if m := _DM_RE.match(text):
        day, month = int(m[1]), int(m[2])
        candidate = _build(today.year, month, day)
        if candidate < today:
            candidate = _build(today.year + 1, month, day)
        return candidate  # by construction >= today

    raise BadDateFormat(f"unrecognised date: {raw!r}")


def _guard_past(value: _dt.date, today: _dt.date) -> _dt.date:
    if value < today:
        raise DateInPast(f"{value.isoformat()} is before {today.isoformat()}")
    return value
