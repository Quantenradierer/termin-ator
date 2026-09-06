# T09 — Popularity recalculation (EMA)

**Depends on:** T01
**Traces to:** Q5, Q6, Q14, Q15, Q16, Q17

## Context
Pure function that turns a finished poll's vote counts into new weights. No DB, no Discord.

## Requirements
- `core/popularity.py`:
  `recalculate(options: list[OptionResult], *, lam: float, floor: float) -> dict[int, float]`
  where `OptionResult = (restaurant_id, weight_before, vote_count)`.
- Formula, per restaurant **that was on the poll** (winner included — its post-poll weight is
  computed then it gets deactivated by the caller):
  - `n` = number of options on the poll
  - `total` = sum of all `vote_count` (approval voting → sum of approvals, Q21)
  - `share_i = vote_count_i / total`
  - `new_i = (1 - lam) * weight_before_i + lam * (n * share_i)`
  - `new_i = max(new_i, floor)`
- If `total == 0` → return `{}` (no changes; caller handles the zero-vote path, Q19).
- Restaurants **not** on the poll are not passed in and are never modified (Q15).
- Separate helper `pick_winner(options, weights_before, *, rng) -> (restaurant_id, tie_kind)`:
  - highest `vote_count` wins
  - tie on `vote_count` → highest `weight_before` wins (`tie_kind = "weight"`)
  - still tied (equal weight) → `rng.choice` (`tie_kind = "random"`)
  - no tie → `tie_kind = None`
  - `total == 0` → returns `None` winner

## Acceptance criteria
- `n=4`, one option with all votes → its weight rises toward `n*1.0`, others toward `0` but
  clamped at `floor`; unchanged restaurants absent from the result.
- `total == 0` → `recalculate` returns `{}`, `pick_winner` returns no winner.
- Tie tests: equal counts, unequal weight → weight winner, `tie_kind="weight"`; equal counts
  and equal weight → deterministic under seeded `rng`, `tie_kind="random"`.
- λ boundary: `lam=1.0` → `new_i == n * share_i` (clamped).
