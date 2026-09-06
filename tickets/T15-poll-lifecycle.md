# T15 — Poll lifecycle robustness & startup reconciliation

**Depends on:** T13, T14
**Traces to:** Q10, Q15 (robustness), Q19

## Context
The bot may be offline exactly when a poll's 7-day window ends. `discord.py` has **no
dedicated "poll ended" gateway event**, so closing is driven by a scheduled task plus a
startup check.

## Requirements
- **Scheduling:** when a poll is created (T13), start an `asyncio` task that sleeps until
  `expires_at` (+ a small buffer, e.g. 30 s) then calls `close_poll` (T14).
- **Startup reconciliation** (called from `on_ready`, T05):
  - read `get_active_poll()`
  - if `expires_at <= now` → call `close_poll` immediately
  - else → (re)schedule the sleep-until task for the remaining time
- **Single-flight:** a module-level `asyncio.Lock` (or a guard flag) so the scheduled task
  and a manual/`on_ready` path can't both close the same poll; combined with `close_poll`'s
  own idempotency (T14).
- **Force-discard interaction:** `/start-poll` discarding a running poll (T13) must cancel
  the pending close task for the old poll.
- **Optional safety net:** a low-frequency background loop (e.g. every 15 min) that runs the
  same reconciliation, in case a scheduled task was lost.
- Log each state transition (scheduled / closing / reconciled-on-startup / discarded).

## Acceptance criteria
- Start a short poll (e.g. 1 h via `duration_hours`), kill the process before expiry, restart
  after expiry → poll is closed on startup, winner announced once, archive written once.
- Restart *before* expiry → close task rescheduled, fires at the right time.
- `/start-poll` over a running poll → old close task cancelled, no stray later announcement.
- Two concurrent close triggers → exactly one archive row, one announcement.
