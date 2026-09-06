from __future__ import annotations

import datetime as _dt

import pytest

from restaurant_bot.db import (
    ActivePoll,
    AlreadyExists,
    ArchiveOption,
    Database,
)

NOW = _dt.datetime(2026, 9, 6, 12, 0, tzinfo=_dt.UTC)


async def test_init_idempotent(tmp_path) -> None:
    path = str(tmp_path / "a.db")
    db1 = await Database.connect(path)
    await db1.init()
    await db1.close()
    db2 = await Database.connect(path)  # connect() calls init() again
    await db2.close()


async def test_add_and_duplicate(db: Database) -> None:
    r = await db.add_restaurant("Pizza Palace", now=NOW)
    assert r.weight == 1.0
    assert r.active is True
    with pytest.raises(AlreadyExists):
        await db.add_restaurant("  pizza   palace ", now=NOW)


async def test_duplicate_against_retired(db: Database) -> None:
    r = await db.add_restaurant("Sushi Go", now=NOW)
    await _retire(db, r.id)
    with pytest.raises(AlreadyExists):
        await db.add_restaurant("sushi go", now=NOW)


async def test_list_ordering(db: Database) -> None:
    a = await db.add_restaurant("Alpha", now=NOW)
    b = await db.add_restaurant("Bravo", now=NOW)
    await db.archive_poll(
        message_id=1,
        channel_id=1,
        dinner_date="2026-09-12",
        created_at=NOW.isoformat(),
        closed_at=NOW.isoformat(),
        status="completed",
        winner_restaurant_id=None,
        tie_broken=False,
        tie_break_kind=None,
        options=[],
        new_weights={a.id: 2.0, b.id: 0.5},
        deactivate_restaurant_id=None,
    )
    active = await db.list_active()
    assert [r.text for r in active] == ["Alpha", "Bravo"]  # weight desc


async def test_archive_poll_atomic_rollback(db: Database, monkeypatch) -> None:
    r = await db.add_restaurant("Rollback Cafe", now=NOW)

    real_executemany = db._conn.executemany

    async def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(db._conn, "executemany", boom)
    with pytest.raises(RuntimeError):
        await db.archive_poll(
            message_id=1,
            channel_id=1,
            dinner_date="2026-09-12",
            created_at=NOW.isoformat(),
            closed_at=NOW.isoformat(),
            status="completed",
            winner_restaurant_id=r.id,
            tie_broken=False,
            tie_break_kind=None,
            options=[ArchiveOption(r.id, r.text, 3, 1.0, 1.3)],
            new_weights={r.id: 1.3},
            deactivate_restaurant_id=r.id,
        )
    monkeypatch.setattr(db._conn, "executemany", real_executemany)

    after = await db.get_restaurant(r.id)
    assert after.weight == 1.0
    assert after.active is True
    async with db._conn.execute("SELECT COUNT(*) AS n FROM polls") as cur:
        assert (await cur.fetchone())["n"] == 0


async def test_active_poll_roundtrip_and_clear(db: Database) -> None:
    a = await db.add_restaurant("A", now=NOW)
    b = await db.add_restaurant("B", now=NOW)
    poll = ActivePoll(
        message_id=111,
        channel_id=222,
        dinner_date="2026-09-12",
        duration_h=168,
        created_at=NOW.isoformat(),
        expires_at=(NOW + _dt.timedelta(hours=168)).isoformat(),
    )
    await db.set_active_poll(poll, [(1, a.id), (2, b.id)])
    got = await db.get_active_poll()
    assert got is not None and got.message_id == 111
    assert await db.get_active_poll_options() == {1: a.id, 2: b.id}
    await db.clear_active_poll()
    assert await db.get_active_poll() is None


async def test_hard_delete_keeps_archive(db: Database) -> None:
    r = await db.add_restaurant("Typo Diner", now=NOW)
    await db.archive_poll(
        message_id=9,
        channel_id=9,
        dinner_date="2026-09-12",
        created_at=NOW.isoformat(),
        closed_at=NOW.isoformat(),
        status="completed",
        winner_restaurant_id=r.id,
        tie_broken=False,
        tie_break_kind=None,
        options=[ArchiveOption(r.id, r.text, 4, 1.0, 1.4)],
        new_weights={r.id: 1.4},
        deactivate_restaurant_id=r.id,
    )
    await db.hard_delete(r.id)
    async with db._conn.execute("SELECT restaurant_text, restaurant_id FROM poll_options") as cur:
        row = await cur.fetchone()
    assert row["restaurant_text"] == "Typo Diner"
    assert row["restaurant_id"] is None  # FK set null, archive text preserved


async def _retire(db: Database, restaurant_id: int) -> None:
    await db.archive_poll(
        message_id=1,
        channel_id=1,
        dinner_date="2026-09-12",
        created_at=NOW.isoformat(),
        closed_at=NOW.isoformat(),
        status="completed",
        winner_restaurant_id=restaurant_id,
        tie_broken=False,
        tie_break_kind=None,
        options=[],
        new_weights={},
        deactivate_restaurant_id=restaurant_id,
    )
