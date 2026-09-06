# T18 — `/reactivate-restaurant` command

**Depends on:** T04, T05, T06
**Traces to:** Q18 (revised)

## Context
Q18 originally chose "no reactivation". Revised: a retired restaurant can be brought back
into rotation on demand.

## Requirements
- Slash command `reactivate-restaurant` with one required string arg `restaurant`,
  open to everyone (Q8).
- **Autocomplete** on that arg: **retired** restaurant names (`active = 0`), filtered by the
  typed substring (case-insensitive), capped at 25.
- Resolution: match the chosen value to a **retired** restaurant via `find_by_norm`.
  No match, or the match is already active → German "nicht in der Liste der bereits
  besuchten".
- On success (`Database.reactivate`):
  - `active = 1`, `retired_at = NULL`, `visit_date = NULL`
  - **weight reset to `1.0`** (its winning-era weight is stale; matches a fresh entry)
  - reply German confirmation noting the weight reset
- After reactivation the restaurant is a normal active entry and eligible for the next poll.

## Acceptance criteria
- Autocomplete lists only retired names, substring-filtered, ≤ 25.
- Reactivating a retired restaurant → it disappears from "Bereits besucht", reappears in the
  active list with weight `1.0`.
- Reactivating a name that is active (or unknown) → refused, nothing changes.
