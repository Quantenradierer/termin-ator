# T12 — `/remove-restaurant` command

**Depends on:** T04, T05, T06
**Traces to:** Q8, Q28

## Context
Escape hatch for typos / uncaught duplicates. Hard delete — a bad entry has no history worth
keeping. Open to everyone.

## Requirements
- Slash command `remove-restaurant` with one required string arg `restaurant`.
- **Autocomplete** on that arg: active restaurant names, filtered by the typed substring
  (case-insensitive), capped at Discord's 25-choice limit.
- Resolution:
  - match the chosen value to an **active** restaurant by exact `text` (fallback: `text_norm`)
  - no match → German "nicht gefunden"
- Guard: if the restaurant is currently an option on the active poll
  (`active_poll_options`) → refuse with German "ist gerade in der laufenden Umfrage" and do
  not delete (Q28).
- On success: `hard_delete(id)` (removes the row; archive tables keep their snapshot text via
  `poll_options.restaurant_text`, but FK from `poll_options.restaurant_id` must be handled —
  use `ON DELETE SET NULL` or nullable FK, decided in T04). Reply German confirmation.
- Retired restaurants are **not** offered and cannot be removed (nothing to fix there).

## Acceptance criteria
- Autocomplete returns only active names, substring-filtered, ≤ 25.
- Removing a restaurant that is on the running poll → refused, row still present.
- Removing a normal active restaurant → gone from `/list-restaurants`.
- Prior poll archives still readable after the delete (no broken query).
