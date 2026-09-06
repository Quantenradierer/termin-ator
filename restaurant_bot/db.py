"""SQLite schema and async data-access layer (T04).

Single shared dataset -- no ``guild_id`` (Q3). A poll archive is kept so weights can be
audited or rebuilt if ``EMA_LAMBDA`` changes (Q32).
"""

from __future__ import annotations

import datetime as _dt
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import aiosqlite

SCHEMA_VERSION = 3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS restaurants (
    id          INTEGER PRIMARY KEY,
    text        TEXT    NOT NULL,
    text_norm   TEXT    NOT NULL UNIQUE,
    weight      REAL    NOT NULL DEFAULT 1.0,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL,
    retired_at  TEXT,
    visit_date  TEXT
);

CREATE TABLE IF NOT EXISTS active_poll (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    message_id  INTEGER NOT NULL,
    channel_id  INTEGER NOT NULL,
    dinner_date TEXT    NOT NULL,
    duration_h  INTEGER NOT NULL,
    created_at  TEXT    NOT NULL,
    expires_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS active_poll_options (
    poll_id       INTEGER NOT NULL REFERENCES active_poll(id) ON DELETE CASCADE,
    answer_id     INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    PRIMARY KEY (poll_id, answer_id)
);

CREATE TABLE IF NOT EXISTS polls (
    id                   INTEGER PRIMARY KEY,
    message_id           INTEGER NOT NULL,
    channel_id           INTEGER NOT NULL,
    dinner_date          TEXT    NOT NULL,
    created_at           TEXT    NOT NULL,
    closed_at            TEXT    NOT NULL,
    status               TEXT    NOT NULL,
    winner_restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE SET NULL,
    tie_broken           INTEGER NOT NULL DEFAULT 0,
    tie_break_kind       TEXT
);

CREATE TABLE IF NOT EXISTS poll_options (
    poll_id         INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    restaurant_id   INTEGER REFERENCES restaurants(id) ON DELETE SET NULL,
    restaurant_text TEXT    NOT NULL,
    vote_count      INTEGER NOT NULL,
    weight_before   REAL    NOT NULL,
    weight_after    REAL    NOT NULL,
    PRIMARY KEY (poll_id, restaurant_id)
);

CREATE TABLE IF NOT EXISTS reminders (
    id              INTEGER PRIMARY KEY,
    poll_id         INTEGER REFERENCES polls(id) ON DELETE SET NULL,
    channel_id      INTEGER NOT NULL,
    restaurant_text TEXT    NOT NULL,
    visit_date      TEXT    NOT NULL,
    remind_at       TEXT    NOT NULL,   -- ISO-8601 UTC
    voter_ids       TEXT    NOT NULL,   -- JSON array of Discord user ids
    created_at      TEXT    NOT NULL,
    sent            INTEGER NOT NULL DEFAULT 0
);
"""


class AlreadyExists(Exception):
    """A restaurant with the same normalised text already exists."""


@dataclass(frozen=True)
class Restaurant:
    id: int
    text: str
    text_norm: str
    weight: float
    active: bool
    created_at: str
    retired_at: str | None
    visit_date: str | None  # dinner date of the poll this restaurant won (Q9)


@dataclass(frozen=True)
class ActivePoll:
    message_id: int
    channel_id: int
    dinner_date: str
    duration_h: int
    created_at: str
    expires_at: str


@dataclass(frozen=True)
class ArchiveOption:
    restaurant_id: int
    restaurant_text: str
    vote_count: int
    weight_before: float
    weight_after: float


@dataclass(frozen=True)
class PendingReminder:
    """A visit-day reminder to create alongside a completed poll."""

    channel_id: int
    restaurant_text: str
    visit_date: str  # ISO date
    remind_at: str  # ISO-8601 UTC
    voter_ids: list[int]
    created_at: str


@dataclass(frozen=True)
class Reminder:
    id: int
    channel_id: int
    restaurant_text: str
    visit_date: str
    remind_at: str
    voter_ids: list[int]
    sent: bool


def normalise(text: str) -> str:
    return " ".join(text.split()).casefold()


def _row_to_reminder(row: aiosqlite.Row) -> Reminder:
    return Reminder(
        id=row["id"],
        channel_id=row["channel_id"],
        restaurant_text=row["restaurant_text"],
        visit_date=row["visit_date"],
        remind_at=row["remind_at"],
        voter_ids=list(json.loads(row["voter_ids"])),
        sent=bool(row["sent"]),
    )


def _row_to_restaurant(row: aiosqlite.Row) -> Restaurant:
    keys = row.keys()
    return Restaurant(
        id=row["id"],
        text=row["text"],
        text_norm=row["text_norm"],
        weight=row["weight"],
        active=bool(row["active"]),
        created_at=row["created_at"],
        retired_at=row["retired_at"],
        visit_date=row["visit_date"] if "visit_date" in keys else None,
    )


class Database:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    # -- lifecycle -------------------------------------------------------
    @classmethod
    async def connect(cls, path: str) -> Database:
        conn = await aiosqlite.connect(path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")
        db = cls(conn)
        await db.init()
        return db

    async def init(self) -> None:
        await self._conn.executescript(_SCHEMA)
        async with self._conn.execute("SELECT version FROM schema_version") as cur:
            row = await cur.fetchone()

        if row is None:
            await self._conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
            )
        else:
            await self._migrate(int(row["version"]))
        await self._conn.commit()

    async def _migrate(self, current: int) -> None:
        if current >= SCHEMA_VERSION:
            return
        if current < 2:
            async with self._conn.execute("PRAGMA table_info(restaurants)") as cur:
                columns = {r["name"] for r in await cur.fetchall()}
            if "visit_date" not in columns:
                await self._conn.execute("ALTER TABLE restaurants ADD COLUMN visit_date TEXT")
            # Backfill from the winning poll's dinner date where we can.
            await self._conn.execute(
                "UPDATE restaurants SET visit_date = ("
                "  SELECT p.dinner_date FROM polls p"
                "  WHERE p.winner_restaurant_id = restaurants.id"
                "  ORDER BY p.closed_at DESC LIMIT 1"
                ") WHERE active = 0 AND visit_date IS NULL"
            )
        # v3 adds the `reminders` table, already created by executescript(_SCHEMA).
        await self._conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))

    async def close(self) -> None:
        await self._conn.close()

    # -- restaurants --------------------------------------------------
    async def add_restaurant(self, text: str, *, now: _dt.datetime) -> Restaurant:
        text = text.strip()
        norm = normalise(text)
        try:
            cur = await self._conn.execute(
                "INSERT INTO restaurants (text, text_norm, weight, active, created_at) "
                "VALUES (?, ?, 1.0, 1, ?)",
                (text, norm, now.isoformat()),
            )
        except aiosqlite.IntegrityError as exc:
            raise AlreadyExists(text) from exc
        await self._conn.commit()
        return await self.get_restaurant(cur.lastrowid)  # type: ignore[arg-type]

    async def get_restaurant(self, restaurant_id: int) -> Restaurant:
        async with self._conn.execute(
            "SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            raise KeyError(restaurant_id)
        return _row_to_restaurant(row)

    async def find_by_norm(self, text: str) -> Restaurant | None:
        async with self._conn.execute(
            "SELECT * FROM restaurants WHERE text_norm = ?", (normalise(text),)
        ) as cur:
            row = await cur.fetchone()
        return _row_to_restaurant(row) if row else None

    async def list_active(self) -> list[Restaurant]:
        async with self._conn.execute(
            "SELECT * FROM restaurants WHERE active = 1 ORDER BY weight DESC, text ASC"
        ) as cur:
            return [_row_to_restaurant(r) for r in await cur.fetchall()]

    async def list_retired(self) -> list[Restaurant]:
        async with self._conn.execute(
            "SELECT * FROM restaurants WHERE active = 0 "
            "ORDER BY visit_date DESC, retired_at DESC, text ASC"
        ) as cur:
            return [_row_to_restaurant(r) for r in await cur.fetchall()]

    async def reactivate(self, restaurant_id: int) -> None:
        """Bring a retired restaurant back into rotation with a fresh weight of 1.0."""
        await self._conn.execute(
            "UPDATE restaurants SET active = 1, retired_at = NULL, visit_date = NULL, "
            "weight = 1.0 WHERE id = ?",
            (restaurant_id,),
        )
        await self._conn.commit()

    async def count_active(self) -> int:
        async with self._conn.execute(
            "SELECT COUNT(*) AS n FROM restaurants WHERE active = 1"
        ) as cur:
            row = await cur.fetchone()
        return int(row["n"])

    async def hard_delete(self, restaurant_id: int) -> None:
        await self._conn.execute("DELETE FROM restaurants WHERE id = ?", (restaurant_id,))
        await self._conn.commit()

    # -- active poll ------------------------------------------------
    async def get_active_poll(self) -> ActivePoll | None:
        async with self._conn.execute("SELECT * FROM active_poll WHERE id = 1") as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return ActivePoll(
            message_id=row["message_id"],
            channel_id=row["channel_id"],
            dinner_date=row["dinner_date"],
            duration_h=row["duration_h"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    async def get_active_poll_options(self) -> dict[int, int]:
        """Return ``{answer_id: restaurant_id}`` for the current poll."""
        async with self._conn.execute(
            "SELECT answer_id, restaurant_id FROM active_poll_options WHERE poll_id = 1"
        ) as cur:
            return {r["answer_id"]: r["restaurant_id"] for r in await cur.fetchall()}

    async def set_active_poll(
        self,
        poll: ActivePoll,
        options: Iterable[tuple[int, int]],
    ) -> None:
        """Replace any existing active poll with ``poll`` + its ``(answer_id, restaurant_id)``."""
        await self._conn.execute("DELETE FROM active_poll WHERE id = 1")
        await self._conn.execute(
            "INSERT INTO active_poll "
            "(id, message_id, channel_id, dinner_date, duration_h, created_at, expires_at) "
            "VALUES (1, ?, ?, ?, ?, ?, ?)",
            (
                poll.message_id,
                poll.channel_id,
                poll.dinner_date,
                poll.duration_h,
                poll.created_at,
                poll.expires_at,
            ),
        )
        await self._conn.executemany(
            "INSERT INTO active_poll_options (poll_id, answer_id, restaurant_id) VALUES (1, ?, ?)",
            list(options),
        )
        await self._conn.commit()

    async def clear_active_poll(self) -> None:
        await self._conn.execute("DELETE FROM active_poll WHERE id = 1")
        await self._conn.commit()

    # -- archive (atomic) -----------------------------------------
    async def archive_poll(
        self,
        *,
        message_id: int,
        channel_id: int,
        dinner_date: str,
        created_at: str,
        closed_at: str,
        status: str,
        winner_restaurant_id: int | None,
        tie_broken: bool,
        tie_break_kind: str | None,
        options: Sequence[ArchiveOption],
        new_weights: dict[int, float],
        deactivate_restaurant_id: int | None,
        reminder: PendingReminder | None = None,
    ) -> int:
        """Write the archive rows, apply weight updates and winner deactivation, create the
        visit-day reminder (if any), and clear the active poll -- all in one transaction.
        Returns the new ``polls.id``.
        """
        try:
            cur = await self._conn.execute(
                "INSERT INTO polls "
                "(message_id, channel_id, dinner_date, created_at, closed_at, status, "
                " winner_restaurant_id, tie_broken, tie_break_kind) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    message_id,
                    channel_id,
                    dinner_date,
                    created_at,
                    closed_at,
                    status,
                    winner_restaurant_id,
                    int(tie_broken),
                    tie_break_kind,
                ),
            )
            poll_id = cur.lastrowid
            assert poll_id is not None

            await self._conn.executemany(
                "INSERT INTO poll_options (poll_id, restaurant_id, restaurant_text, "
                "vote_count, weight_before, weight_after) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        poll_id,
                        o.restaurant_id,
                        o.restaurant_text,
                        o.vote_count,
                        o.weight_before,
                        o.weight_after,
                    )
                    for o in options
                ],
            )

            for restaurant_id, weight in new_weights.items():
                await self._conn.execute(
                    "UPDATE restaurants SET weight = ? WHERE id = ?", (weight, restaurant_id)
                )

            if deactivate_restaurant_id is not None:
                await self._conn.execute(
                    "UPDATE restaurants SET active = 0, retired_at = ?, visit_date = ? "
                    "WHERE id = ?",
                    (closed_at, dinner_date, deactivate_restaurant_id),
                )

            if reminder is not None:
                await self._conn.execute(
                    "INSERT INTO reminders "
                    "(poll_id, channel_id, restaurant_text, visit_date, remind_at, "
                    " voter_ids, created_at, sent) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                    (
                        poll_id,
                        reminder.channel_id,
                        reminder.restaurant_text,
                        reminder.visit_date,
                        reminder.remind_at,
                        json.dumps(reminder.voter_ids),
                        reminder.created_at,
                    ),
                )

            await self._conn.execute("DELETE FROM active_poll WHERE id = 1")
        except Exception:
            await self._conn.rollback()
            raise
        await self._conn.commit()
        return poll_id

    # -- reminders ----------------------------------------------------
    async def pending_reminders(self) -> list[Reminder]:
        async with self._conn.execute(
            "SELECT * FROM reminders WHERE sent = 0 ORDER BY remind_at ASC"
        ) as cur:
            return [_row_to_reminder(r) for r in await cur.fetchall()]

    async def get_reminder(self, reminder_id: int) -> Reminder | None:
        async with self._conn.execute(
            "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
        ) as cur:
            row = await cur.fetchone()
        return _row_to_reminder(row) if row else None

    async def mark_reminder_sent(self, reminder_id: int) -> None:
        await self._conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        await self._conn.commit()
