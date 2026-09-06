from __future__ import annotations

import random

import pytest

from restaurant_bot.core.popularity import OptionResult, pick_winner, recalculate


def test_recalculate_hand_worked() -> None:
    # n=4, total=10; shares 0.5 / 0.3 / 0.2 / 0.0
    options = [
        OptionResult(1, weight_before=1.0, vote_count=5),
        OptionResult(2, weight_before=1.0, vote_count=3),
        OptionResult(3, weight_before=1.0, vote_count=2),
        OptionResult(4, weight_before=1.0, vote_count=0),
    ]
    out = recalculate(options, lam=0.3, floor=0.05)
    # new = 0.7*1.0 + 0.3*(4*share)
    assert out[1] == pytest.approx(0.7 + 0.3 * (4 * 0.5))  # 1.30
    assert out[2] == pytest.approx(0.7 + 0.3 * (4 * 0.3))  # 1.06
    assert out[3] == pytest.approx(0.7 + 0.3 * (4 * 0.2))  # 0.94
    assert out[4] == pytest.approx(0.7 + 0.3 * 0.0)  # 0.70


def test_recalculate_zero_votes_returns_empty() -> None:
    options = [OptionResult(1, 1.0, 0), OptionResult(2, 1.0, 0)]
    assert recalculate(options, lam=0.3, floor=0.05) == {}


def test_recalculate_floor_applied() -> None:
    options = [
        OptionResult(1, weight_before=0.1, vote_count=10),
        OptionResult(2, weight_before=0.1, vote_count=0),
    ]
    out = recalculate(options, lam=1.0, floor=0.05)
    # option 2: (1-1)*0.1 + 1*(2*0) = 0 -> clamped to floor
    assert out[2] == 0.05


def test_recalculate_lambda_zero_is_noop() -> None:
    options = [OptionResult(1, 1.23, 5), OptionResult(2, 0.4, 1)]
    out = recalculate(options, lam=0.0, floor=0.01)
    assert out[1] == pytest.approx(1.23)
    assert out[2] == pytest.approx(0.4)


def test_recalculate_lambda_one_is_pure_performance() -> None:
    options = [OptionResult(1, 99.0, 3), OptionResult(2, 99.0, 1)]
    out = recalculate(options, lam=1.0, floor=0.01)
    assert out[1] == pytest.approx(2 * 0.75)
    assert out[2] == pytest.approx(2 * 0.25)


def test_pick_winner_clear() -> None:
    options = [OptionResult(1, 1.0, 5), OptionResult(2, 1.0, 2)]
    assert pick_winner(options, rng=random.Random(0)) == (1, None)


def test_pick_winner_vote_tie_broken_by_weight() -> None:
    options = [
        OptionResult(1, weight_before=1.2, vote_count=4),
        OptionResult(2, weight_before=0.9, vote_count=4),
    ]
    assert pick_winner(options, rng=random.Random(0)) == (1, "weight")


def test_pick_winner_full_tie_random_but_deterministic_with_seed() -> None:
    options = [
        OptionResult(1, weight_before=1.0, vote_count=4),
        OptionResult(2, weight_before=1.0, vote_count=4),
    ]
    first = pick_winner(options, rng=random.Random(5))
    second = pick_winner(options, rng=random.Random(5))
    assert first == second
    assert first[1] == "random"
    assert first[0] in (1, 2)


def test_pick_winner_no_votes() -> None:
    options = [OptionResult(1, 1.0, 0), OptionResult(2, 1.0, 0)]
    assert pick_winner(options) == (None, None)
