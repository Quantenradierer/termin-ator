from __future__ import annotations

import datetime as _dt
import inspect

import pytest

from restaurant_bot import strings_de


def test_format_date_de_weekday() -> None:
    # 2026-09-12 is a Saturday
    assert strings_de.format_date_de(_dt.date(2026, 9, 12)) == "Sa, 12.09.2026"
    # 2026-09-06 is a Sunday
    assert strings_de.format_date_de(_dt.date(2026, 9, 6)) == "So, 06.09.2026"


def test_format_weight() -> None:
    assert strings_de.format_weight(1.2) == "1.20"
    assert strings_de.format_weight(0.049) == "0.05"


def test_retired_block_is_spoiler() -> None:
    block = strings_de.list_retired_block(["• X (Sa, 12.09.2026)"])
    assert block.startswith("**Bereits besucht:**")
    assert "||" in block


@pytest.mark.parametrize(
    "func",
    [
        name
        for name, obj in inspect.getmembers(strings_de, inspect.isfunction)
        if obj.__module__ == strings_de.__name__ and name != "format_date_de"
    ],
)
def test_helpers_return_nonempty_str(func: str) -> None:
    fn = getattr(strings_de, func)
    sig = inspect.signature(fn)
    args: list[object] = []
    for param in sig.parameters.values():
        anno = param.annotation
        if anno in (int, "int"):
            args.append(1)
        elif anno in (float, "float"):
            args.append(1.0)
        elif "list" in str(anno):
            args.append(["x"])
        else:
            args.append("x")
    result = fn(*args)
    assert isinstance(result, str) and result.strip()
