"""Weighted random sampling without replacement (T08).

Used to pick the <=10 restaurants that go on a poll when more than 10 are active (Q12).
Selection probability is proportional to ``weight`` (plain proportional, no exponent knob).

Algorithm: Efraimidis-Spirakis A-Res -- assign each item the key ``u ** (1 / weight)`` with
``u`` uniform in (0, 1], then take the ``k`` items with the largest keys. No numpy.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")

_MIN_WEIGHT = 1e-9  # guard so pow/division stays well-defined even if a caller passes <= 0


def weighted_sample_without_replacement(
    items: Sequence[T],
    weights: Sequence[float],
    k: int,
    *,
    rng: random.Random | None = None,
) -> list[T]:
    if len(items) != len(weights):
        raise ValueError("items and weights must have the same length")
    if k <= 0 or not items:
        return []

    rng = rng or random.Random()

    if k >= len(items):
        result = list(items)
        rng.shuffle(result)
        return result

    keyed: list[tuple[float, int]] = []
    for idx, weight in enumerate(weights):
        w = weight if weight > _MIN_WEIGHT else _MIN_WEIGHT
        u = rng.random() or _MIN_WEIGHT  # random() can return 0.0; avoid 0 ** x collapsing ties
        keyed.append((u ** (1.0 / w), idx))

    keyed.sort(reverse=True)
    return [items[idx] for _, idx in keyed[:k]]
