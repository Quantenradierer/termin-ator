# T19 — Visit-day reminder

**Depends on:** T04, T06, T14, T15
**Traces to:** user request (post-design)

## Context
On the dinner date, at ~09:00 local time, ping everyone who voted for the winning
restaurant as a reminder.

## Requirements
- Config: `REMINDER_HOUR` env (0–23, default `9`), validated in `config.py`.
- At poll close (T14, completed path only): capture the Discord user ids that voted for the
  **winning answer** (`PollAnswer.voters()`), and create a `reminders` row **inside the
  `archive_poll` transaction**:
  - `channel_id` = the poll's channel
  - `restaurant_text` = winner's string (snapshot)
  - `visit_date` = the poll's `dinner_date`
  - `remind_at` = `dinner_date` at `REMINDER_HOUR` in `config.tz`, stored as ISO-8601 UTC
  - `voter_ids` = JSON array (best-effort; empty if the fetch fails)
  - `sent = 0`
- No reminder for `no_votes` or `discarded` polls.
- Scheduling (`PollScheduler`, T15):
  - on `reconcile()` and after each close, and on the safety-net loop, load
    `pending_reminders()`
  - due (`remind_at <= now`) → fire immediately; future → `asyncio` task sleeping until then
  - single-flight via a dedicated lock; re-check `sent` before posting; idempotent
  - **stale guard**: if `now > remind_at + 12 h` (bot was down), mark `sent` without posting
  - if the channel can't be resolved, leave unsent for the next tick
- Message (German, `strings_de.visit_reminder`):
  `🔔 Erinnerung: Heute geht's zu **<restaurant>**!` followed by the `<@id>` mentions on the
  next line. Sent with `AllowedMentions(users=True)` so the pings actually notify.
- Schema: `reminders` table added at `SCHEMA_VERSION = 3` (created by the idempotent schema
  script; no ALTER needed).

## Acceptance criteria
- Closing a poll with a winner writes one pending reminder with the right `remind_at`
  (e.g. 09:00 Europe/Berlin → 07:00Z in summer) and the winning voters' ids.
- A due reminder posts one channel message containing every voter mention and the winner
  name, then is marked `sent`; a second reconcile does not repost.
- A future reminder is scheduled, not sent.
- A reminder overdue by > 12 h is marked `sent` without posting.
- Zero-vote / discarded polls create no reminder.
