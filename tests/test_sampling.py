from __future__ import annotations

import random

from restaurant_bot.core.sampling import weighted_sample_without_replacement


def test_returns_all_when_k_ge_len() -> None:
    items = ["a", "b", "c"]
    out = weighted_sample_without_replacement(items, [1, 1, 1], 5, rng=random.Random(1))
    assert sorted(out) == ["a", "b", "c"]


def test_empty() -> None:
    assert weighted_sample_without_replacement([], [], 3) == []


def test_no_duplicates_and_exact_count() -> None:
    items = list(range(20))
    weights = [1.0] * 20
    out = weighted_sample_without_replacement(items, weights, 10, rng=random.Random(42))
    assert len(out) == 10
    assert len(set(out)) == 10


def test_seeded_reproducible() -> None:
    items = list(range(15))
    weights = [i + 1 for i in range(15)]
    a = weighted_sample_without_replacement(items, weights, 10, rng=random.Random(7))
    b = weighted_sample_without_replacement(items, weights, 10, rng=random.Random(7))
    assert a == b


def test_weight_bias() -> None:
    # "heavy" has weight 2.0, each "light_i" has weight 1.0; heavy should be picked
    # markedly more often than any single light item over many trials.
    items = ["heavy", *[f"light_{i}" for i in range(9)]]
    weights = [2.0, *([1.0] * 9)]
    rng = random.Random(123)
    trials = 4000
    counts = {name: 0 for name in items}
    for _ in range(trials):
        for picked in weighted_sample_without_replacement(items, weights, 5, rng=rng):
            counts[picked] += 1
    avg_light = sum(counts[f"light_{i}"] for i in range(9)) / 9
    assert counts["heavy"] > avg_light * 1.4


def test_nonpositive_weights_do_not_crash() -> None:
    items = ["a", "b", "c", "d"]
    out = weighted_sample_without_replacement(items, [0.0, -1.0, 1.0, 1.0], 2, rng=random.Random(1))
    assert len(out) == 2
    assert len(set(out)) == 2
