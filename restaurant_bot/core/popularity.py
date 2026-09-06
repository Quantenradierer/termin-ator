"""Popularity recalculation and winner selection (T09).

Pure functions -- no DB, no Discord. Called by the poll-close handler (T14).

Model (Q5, Q6, Q14, Q16):
  * each restaurant carries a persistent float ``weight``; new restaurants start at 1.0.
  * after a poll, for every restaurant *that was on the poll* (winner included):

        n      = number of options on the poll
        total  = sum of all vote counts (approval voting -> sum of approvals, Q21)
        share  = vote_count / total
        new    = (1 - lam) * weight_before + lam * (n * share)
        new    = max(new, floor)

  * restaurants that were NOT on the poll are never passed in and never change (Q15).
  * if ``total == 0`` nothing changes and there is no winner (Q19).
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class OptionResult:
    restaurant_id: int
    weight_before: float
    vote_count: int


def recalculate(
    options: list[OptionResult],
    *,
    lam: float,
    floor: float,
) -> dict[int, float]:
    """Return ``{restaurant_id: new_weight}`` for every option.

    Empty dict when there were no votes at all (caller handles the zero-vote path).
    """
    total = sum(o.vote_count for o in options)
    if total == 0:
        return {}

    n = len(options)
    new_weights: dict[int, float] = {}
    for o in options:
        share = o.vote_count / total
        updated = (1.0 - lam) * o.weight_before + lam * (n * share)
        new_weights[o.restaurant_id] = max(updated, floor)
    return new_weights


def pick_winner(
    options: list[OptionResult],
    *,
    rng: random.Random | None = None,
) -> tuple[int | None, str | None]:
    """Return ``(winner_restaurant_id, tie_break_kind)``.

    * highest ``vote_count`` wins
    * tie on votes -> highest ``weight_before`` wins            -> ``tie_break_kind="weight"``
    * still tied (equal weight) -> uniform random choice        -> ``tie_break_kind="random"``
    * no tie                                                    -> ``tie_break_kind=None``
    * no votes at all -> ``(None, None)``
    """
    total = sum(o.vote_count for o in options)
    if total == 0 or not options:
        return None, None

    rng = rng or random.Random()

    top_votes = max(o.vote_count for o in options)
    leaders = [o for o in options if o.vote_count == top_votes]
    if len(leaders) == 1:
        return leaders[0].restaurant_id, None

    # Vote tie -> highest current weight wins (Q17).
    top_weight = max(o.weight_before for o in leaders)
    weight_leaders = [o for o in leaders if o.weight_before == top_weight]
    if len(weight_leaders) == 1:
        return weight_leaders[0].restaurant_id, "weight"

    # Still tied -> random.
    chosen = rng.choice(sorted(weight_leaders, key=lambda o: o.restaurant_id))
    return chosen.restaurant_id, "random"
