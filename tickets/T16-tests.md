# T16 — Test suite

**Depends on:** T07, T08, T09, T14
**Traces to:** Q33

## Context
Unit tests over the pure logic — where subtle bugs actually hide. Discord layer is mocked;
no live gateway, no real DB server (use a temp SQLite file / `:memory:`).

## Requirements
- `pytest` + `pytest-asyncio`. Config in `pyproject.toml`.
- **Date parsing (T07):** the full table in that ticket, incl. next-occurrence and past-date
  rejection, with a fixed `today`.
- **Weighted sampling (T08):** reproducibility under a seeded rng; distribution check
  (weight 2.0 chosen ~2× weight 1.0 over large N); no duplicates; returns `min(k, len)`.
- **Popularity recalc (T09):**
  - EMA math for a hand-worked example
  - `total == 0` → `{}` and no winner
  - floor clamping
  - `lam` boundaries (0 → unchanged, 1 → pure performance)
  - `pick_winner`: clear winner; count-tie broken by weight; count+weight tie broken by
    seeded random; `tie_kind` values
- **Persistence (T04):** `init_db` idempotent; duplicate `text_norm` rejected;
  `archive_poll` atomic (inject an error, assert rollback); hard-delete leaves archive rows
  intact.
- **Poll close (T14)** with a mocked Discord message/poll object:
  - normal path → winner retired, weights written, one announcement, `active_poll` cleared
  - tie path → `tie_broken`/`tie_break_kind` recorded
  - zero-vote path → nothing retired, `no_votes` archived
  - idempotency → second `close_poll` is a no-op
- **German strings (T06):** helpers non-empty; `format_date_de` weekday correctness.
- Target: all pure-logic branches covered. No coverage gate required, but CI-friendly.

## Acceptance criteria
- `pytest` green locally and in a clean checkout with only `requirements*.txt` installed.
- `ruff check` / `ruff format --check` clean on `tests/`.
