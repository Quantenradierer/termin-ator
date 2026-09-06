from __future__ import annotations

import datetime as _dt
import random

from restaurant_bot.core.poll_close import archive_discarded, close_poll
from restaurant_bot.db import ActivePoll, Database

NOW = _dt.datetime(2026, 9, 20, 12, 0, tzinfo=_dt.UTC)


class _FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


# --- fake discord objects --------------------------------------------
class FakeAnswer:
    def __init__(self, answer_id: int, vote_count: int, voter_ids: list[int] | None = None) -> None:
        self.id = answer_id
        self.vote_count = vote_count
        self._voter_ids = voter_ids or []

    async def voters(self, *_args, **_kwargs):
        for uid in self._voter_ids:
            yield _FakeUser(uid)


class FakePoll:
    def __init__(self, answers: list[FakeAnswer], *, finalised: bool = True) -> None:
        self.answers = answers
        self._finalised = finalised

    def is_finalised(self) -> bool:
        return self._finalised

    async def end(self) -> None:
        self._finalised = True


class FakeMessage:
    def __init__(self, poll: FakePoll) -> None:
        self.poll = poll


class FakeChannel:
    def __init__(self, message: FakeMessage) -> None:
        self._message = message
        self.sent: list[str] = []

    async def fetch_message(self, _message_id: int) -> FakeMessage:
        return self._message

    async def send(self, content: str, **_kwargs) -> None:
        self.sent.append(content)


class FakeClient:
    def __init__(self, channel: FakeChannel) -> None:
        self._channel = channel

    def get_channel(self, _channel_id: int):
        return self._channel


# --- helpers -------------------------------------------------------
async def _seed(
    db: Database,
    votes: list[int],
    weights: list[float] | None = None,
    voters: list[list[int]] | None = None,
):
    names = ["Alpha", "Bravo", "Charlie"][: len(votes)]
    restaurants = [await db.add_restaurant(n, now=NOW) for n in names]
    if weights:
        for r, w in zip(restaurants, weights, strict=True):
            await db._conn.execute("UPDATE restaurants SET weight = ? WHERE id = ?", (w, r.id))
        await db._conn.commit()

    poll = ActivePoll(
        message_id=500,
        channel_id=42,
        dinner_date="2026-09-26",
        duration_h=168,
        created_at=NOW.isoformat(),
        expires_at=NOW.isoformat(),
    )
    await db.set_active_poll(poll, [(i + 1, r.id) for i, r in enumerate(restaurants)])
    voters = voters or [[] for _ in votes]
    answers = [FakeAnswer(i + 1, v, voters[i]) for i, v in enumerate(votes)]
    channel = FakeChannel(FakeMessage(FakePoll(answers)))
    return restaurants, channel, FakeClient(channel)


async def test_normal_path(db: Database, config) -> None:
    restaurants, channel, client = await _seed(db, [5, 2, 0])
    poll_id = await close_poll(client, db, config, now=NOW, rng=random.Random(0))

    assert poll_id is not None
    winner = await db.get_restaurant(restaurants[0].id)
    assert winner.active is False
    assert winner.retired_at is not None
    assert winner.visit_date == "2026-09-26"  # the poll's dinner date, not the close time

    # weights recalculated for every option
    charlie = await db.get_restaurant(restaurants[2].id)
    assert charlie.weight < 1.0

    assert await db.get_active_poll() is None
    assert len(channel.sent) == 1
    assert "Alpha" in channel.sent[0]

    async with db._conn.execute("SELECT status FROM polls") as cur:
        assert (await cur.fetchone())["status"] == "completed"


async def test_creates_visit_reminder_for_winning_voters(db: Database, config) -> None:
    # Alpha wins with voters 111 & 222.
    _, _channel, client = await _seed(db, [3, 1, 0], voters=[[111, 222], [999], []])
    await close_poll(client, db, config, now=NOW, rng=random.Random(0))

    pending = await db.pending_reminders()
    assert len(pending) == 1
    reminder = pending[0]
    assert reminder.restaurant_text == "Alpha"
    assert reminder.visit_date == "2026-09-26"
    assert sorted(reminder.voter_ids) == [111, 222]
    # 09:00 Europe/Berlin on 2026-09-26 is 07:00 UTC (CEST, UTC+2).
    assert reminder.remind_at == "2026-09-26T07:00:00+00:00"
    assert reminder.sent is False


async def test_no_reminder_when_zero_votes(db: Database, config) -> None:
    _, _channel, client = await _seed(db, [0, 0, 0])
    await close_poll(client, db, config, now=NOW)
    assert await db.pending_reminders() == []


async def test_tie_broken_by_weight(db: Database, config) -> None:
    restaurants, channel, client = await _seed(db, [4, 4, 1], weights=[1.2, 0.9, 1.0])
    await close_poll(client, db, config, now=NOW, rng=random.Random(0))

    assert (await db.get_restaurant(restaurants[0].id)).active is False
    assert (await db.get_restaurant(restaurants[1].id)).active is True
    async with db._conn.execute("SELECT tie_broken, tie_break_kind FROM polls") as cur:
        row = await cur.fetchone()
    assert row["tie_broken"] == 1
    assert row["tie_break_kind"] == "weight"


async def test_zero_votes(db: Database, config) -> None:
    restaurants, channel, client = await _seed(db, [0, 0, 0])
    await close_poll(client, db, config, now=NOW)

    for r in restaurants:
        fresh = await db.get_restaurant(r.id)
        assert fresh.active is True
        assert fresh.weight == 1.0
    assert await db.get_active_poll() is None
    assert len(channel.sent) == 1
    assert "Keine Stimmen" in channel.sent[0]
    async with db._conn.execute("SELECT status FROM polls") as cur:
        assert (await cur.fetchone())["status"] == "no_votes"


async def test_idempotent(db: Database, config) -> None:
    _, channel, client = await _seed(db, [3, 1, 0])
    first = await close_poll(client, db, config, now=NOW)
    second = await close_poll(client, db, config, now=NOW)
    assert first is not None
    assert second is None
    async with db._conn.execute("SELECT COUNT(*) AS n FROM polls") as cur:
        assert (await cur.fetchone())["n"] == 1


async def test_archive_discarded(db: Database, config) -> None:
    restaurants, _channel, _client = await _seed(db, [2, 2, 2])
    poll_id = await archive_discarded(db, now=NOW)
    assert poll_id is not None
    assert await db.get_active_poll() is None
    for r in restaurants:
        fresh = await db.get_restaurant(r.id)
        assert fresh.active is True
        assert fresh.weight == 1.0
    async with db._conn.execute("SELECT status FROM polls") as cur:
        assert (await cur.fetchone())["status"] == "discarded"
