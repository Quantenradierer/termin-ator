# T04 — SQLite schema & data-access layer

**Depends on:** T01, T02
**Traces to:** Q3, Q4, Q5, Q13, Q18, Q28, Q32

## Context
SQLite via `aiosqlite`, single shared dataset (no `guild_id`). Keep a poll archive so
weights can be audited / rebuilt if λ changes (Q32).

## Schema

```sql
CREATE TABLE restaurants (
    id          INTEGER PRIMARY KEY,
    text        TEXT    NOT NULL,                 -- raw string, <= 55 chars (Q29)
    text_norm   TEXT    NOT NULL UNIQUE,          -- casefold()/trim for dedup (Q7)
    weight      REAL    NOT NULL DEFAULT 1.0,     -- (Q5, Q16)
    active      INTEGER NOT NULL DEFAULT 1,       -- 0 once it wins a poll (Q13/Q18)
    created_at  TEXT    NOT NULL,                 -- ISO-8601 UTC
    retired_at  TEXT                              -- ISO-8601 UTC, set on deactivation
);

CREATE TABLE active_poll (
    id            INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton row (Q10)
    message_id    INTEGER NOT NULL,
    channel_id    INTEGER NOT NULL,
    dinner_date   TEXT    NOT NULL,               -- ISO date (Q9/Q26)
    duration_h    INTEGER NOT NULL,
    created_at    TEXT    NOT NULL,               -- ISO-8601 UTC
    expires_at    TEXT    NOT NULL                -- ISO-8601 UTC (Q15 robustness)
);

CREATE TABLE active_poll_options (
    poll_id        INTEGER NOT NULL REFERENCES active_poll(id) ON DELETE CASCADE,
    answer_id      INTEGER NOT NULL,             -- Discord poll answer id
    restaurant_id  INTEGER NOT NULL REFERENCES restaurants(id),
    PRIMARY KEY (poll_id, answer_id)
);

CREATE TABLE polls (                             -- archive (Q32)
    id            INTEGER PRIMARY KEY,
    message_id    INTEGER NOT NULL,
    channel_id    INTEGER NOT NULL,
    dinner_date   TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    closed_at     TEXT    NOT NULL,
    status        TEXT    NOT NULL,              -- 'completed' | 'no_votes' | 'discarded'
    winner_restaurant_id INTEGER REFERENCES restaurants(id),
    tie_broken    INTEGER NOT NULL DEFAULT 0,    -- 1 if Q17 tie-break was applied
    tie_break_kind TEXT                          -- 'weight' | 'random' | NULL
);

CREATE TABLE poll_options (                      -- archive (Q32)
    poll_id        INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
    restaurant_id  INTEGER REFERENCES restaurants(id) ON DELETE SET NULL,  -- nullable: T12 hard-delete keeps the archive row
    restaurant_text TEXT   NOT NULL,             -- snapshot of the string at poll time
    vote_count     INTEGER NOT NULL,
    weight_before  REAL    NOT NULL,
    weight_after   REAL    NOT NULL,
    PRIMARY KEY (poll_id, restaurant_id)
);
```

## Requirements
- `db.py`: async connection helper, `PRAGMA foreign_keys = ON`, `PRAGMA journal_mode = WAL`.
- Idempotent `init_db()` creating tables if absent (simple `CREATE TABLE IF NOT EXISTS`;
  a `schema_version` table for future migrations).
- Typed accessor functions (no ORM), e.g.:
  - `add_restaurant(text, text_norm, created_at) -> Restaurant | AlreadyExists`
  - `list_active() -> list[Restaurant]` (caller sorts)
  - `list_retired() -> list[Restaurant]`
  - `hard_delete(restaurant_id)` (Q28)
  - `get_active_poll()`, `set_active_poll(...)`, `clear_active_poll()`
  - `archive_poll(...)` writing `polls` + `poll_options` + updating `restaurants.weight`,
    `active`, `retired_at` **in one transaction**
- All timestamps stored ISO-8601 UTC; conversion to `Europe/Berlin` happens in the view layer.

## Acceptance criteria
- `init_db()` on a fresh file creates all tables; running it twice is a no-op.
- Inserting a duplicate `text_norm` raises / returns the `AlreadyExists` signal.
- `archive_poll` is atomic: a forced error mid-write leaves weights and `active_poll` untouched.
