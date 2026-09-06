# T07 — Date parsing utility

**Depends on:** T01
**Traces to:** Q9, Q26

## Context
`/start-poll` takes a `date` string argument (no native Discord date type). The date is the
**dinner date** — informational only; it does not drive poll timing (Q9).

## Requirements
- `core/dates.py`: `parse_dinner_date(raw: str, *, today: date, tz: ZoneInfo) -> date`
- Accepted formats (in order):
  1. `DD.MM.YYYY`  e.g. `12.09.2026`
  2. `DD.MM.`  or  `DD.MM`  — year omitted → the **next occurrence** on/after `today`
     (if that day/month already passed this year, use next year)
  3. ISO `YYYY-MM-DD`
- Leading/trailing whitespace tolerated. Reject anything else → `BadDateFormat` (→ German
  error via T06).
- Reject dates **strictly before `today`** → `DateInPast` (→ German error).
  `today` itself is allowed.
- `today` derived from `datetime.now(tz).date()` at call sites (pass it in for testability).
- No third-party date libraries — hand-rolled parsing.

## Acceptance criteria
- Table-driven tests:
  - `12.09.2026` → 2026-09-12
  - `12.09.` with today 2026-09-06 → 2026-09-12
  - `01.01.` with today 2026-09-06 → 2027-01-01
  - `2026-09-12` → 2026-09-12
  - `06.09.2026` with today 2026-09-06 → allowed
  - `05.09.2026` with today 2026-09-06 → `DateInPast`
  - `2026-13-40`, `garbage`, `12/09/2026` → `BadDateFormat`
