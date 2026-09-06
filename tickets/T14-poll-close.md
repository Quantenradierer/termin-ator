# T14 — Poll close handling & recalculation

**Depends on:** T04, T06, T09
**Traces to:** Q5, Q14, Q15, Q16, Q17, Q18, Q19, Q21, Q23, Q32

## Context
Runs when the active poll's duration elapses (scheduled task from T13, or startup
reconciliation from T15). Turns final vote counts into new weights, retires the winner,
posts the announcement, archives everything.

## Requirements
- Entry point: `close_poll(client, poll_row)` — safe to call more than once (idempotent:
  if there is no matching `active_poll` row, do nothing).
- Fetch the poll message; ensure the Discord poll is finalised
  (`poll.is_finalised`; if not, `await poll.end()` then re-fetch).
- Read per-answer `vote_count`; map `answer_id → restaurant_id` via `active_poll_options`.
- `n` = number of options; `total` = sum of vote counts.

### Zero-vote path (Q19)
- `total == 0`:
  - archive poll with `status = 'no_votes'`, no winner, `tie_broken = 0`
  - **no** weight changes, **no** deactivation
  - post German "keine Stimmen" message
  - `clear_active_poll()`

### Normal path
- `winner_id, tie_kind = pick_winner(...)` (T09).
- `new_weights = recalculate(options, lam=config.EMA_LAMBDA, floor=config.WEIGHT_FLOOR)` (T09)
  — applies to **all** options including the winner; restaurants not on the poll untouched.
- In **one transaction** (`archive_poll`, T04):
  - update `restaurants.weight` for every option
  - set winner `active = 0`, `retired_at = now UTC` (Q18 — permanent, no reactivation)
  - insert `polls` row (`status = 'completed'`, `winner_restaurant_id`, `tie_broken`,
    `tie_break_kind = tie_kind`)
  - insert `poll_options` rows (`vote_count`, `weight_before`, `weight_after`,
    `restaurant_text` snapshot)
  - `clear_active_poll()`
- Post the announcement in the poll's channel: German winner line
  `🏆 Gewinner: {winner.text} — {format_date_de(dinner_date)}` and nothing else (Q23).
  The winner's raw string is included so a URL stays clickable.

## Acceptance criteria
- Poll with a clear top option → that restaurant retired, weights updated per T09, single
  German winner+date message, archive rows written, `active_poll` cleared.
- Tie on top count → winner decided by weight (or seeded random if weights equal);
  `polls.tie_broken = 1`, `tie_break_kind` set; announcement still just winner+date.
- Zero votes → nothing retired, no weight change, "keine Stimmen" message, poll archived
  `no_votes`.
- Calling `close_poll` twice for the same poll → second call is a no-op (no double retire).
