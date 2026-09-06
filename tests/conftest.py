from __future__ import annotations

import datetime as _dt
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio

from restaurant_bot.config import Config
from restaurant_bot.db import Database


@pytest.fixture
def config() -> Config:
    return Config(
        discord_token="test-token",
        tz=ZoneInfo("Europe/Berlin"),
        tz_name="Europe/Berlin",
        sqlite_path=":memory:",
        ema_lambda=0.3,
        weight_floor=0.05,
    )


@pytest_asyncio.fixture
async def db(tmp_path) -> Database:
    database = await Database.connect(str(tmp_path / "test.db"))
    try:
        yield database
    finally:
        await database.close()


@pytest.fixture
def now() -> _dt.datetime:
    return _dt.datetime(2026, 9, 6, 12, 0, tzinfo=_dt.UTC)
