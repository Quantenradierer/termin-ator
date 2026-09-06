from __future__ import annotations

import datetime as _dt

from restaurant_bot.db import ActivePoll, Database
from restaurant_bot.lifecycle import PollScheduler
from tests.test_poll_close import FakeAnswer, FakeChannel, FakeClient, FakeMessage, FakePoll

NOW = _dt.datetime(2026, 9, 20, 12, 0, tzinfo=_dt.UTC)


async def _seed_active_poll(db: Database, expires_at: _dt.datetime) -> FakeClient:
    restaurants = [await db.add_restaurant(n, now=NOW) for n in ("Alpha", "Bravo")]
    await db.set_active_poll(
        ActivePoll(
            message_id=1,
            channel_id=1,
            dinner_date="2026-09-26",
            duration_h=168,
            created_at=NOW.isoformat(),
            expires_at=expires_at.isoformat(),
        ),
        [(i + 1, r.id) for i, r in enumerate(restaurants)],
    )
    answers = [FakeAnswer(1, 3), FakeAnswer(2, 1)]
    return FakeClient(FakeChannel(FakeMessage(FakePoll(answers))))


async def test_reconcile_no_active_poll(db: Database, config) -> None:
    scheduler = PollScheduler(FakeClient(FakeChannel(FakeMessage(FakePoll([])))), db, config)
    await scheduler.reconcile()  # must not raise
    assert scheduler._task is None


async def test_reconcile_closes_overdue_poll(db: Database, config) -> None:
    past = _dt.datetime.now(_dt.UTC) - _dt.timedelta(hours=1)
    client = await _seed_active_poll(db, past)
    scheduler = PollScheduler(client, db, config)

    await scheduler.reconcile()

    assert await db.get_active_poll() is None
    async with db._conn.execute("SELECT status FROM polls") as cur:
        assert (await cur.fetchone())["status"] == "completed"


async def test_reconcile_schedules_future_poll(db: Database, config) -> None:
    future = _dt.datetime.now(_dt.UTC) + _dt.timedelta(hours=2)
    client = await _seed_active_poll(db, future)
    scheduler = PollScheduler(client, db, config)

    await scheduler.reconcile()

    assert scheduler._task is not None
    assert not scheduler._task.done()
    assert await db.get_active_poll() is not None  # not closed yet

    scheduler.cancel()
