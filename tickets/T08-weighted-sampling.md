# T08 — Weighted random sampling utility

**Depends on:** T01
**Traces to:** Q12, Q13

## Context
When more than 10 active restaurants exist, the poll gets a **weighted random sample of 10
without replacement**, pick probability proportional to `weight` (plain proportional — no
exponent knob; Q12).

## Requirements
- `core/sampling.py`:
  `weighted_sample_without_replacement(items, weights, k, *, rng=random.Random()) -> list`
- Algorithm: Efraimidis–Spirakis (A-Res) — key `= rng.random() ** (1 / weight)` per item,
  take the `k` largest keys. No `numpy`.
- Edge handling:
  - `k >= len(items)` → return all items (order unspecified / shuffled). This covers the
    "≤ 10 active → everyone is on the poll" case (Q13), though callers may short-circuit.
  - `weight <= 0` should not occur (floor is `0.05`, Q14); guard by treating `<= 0` as the
    floor to avoid division/`pow` domain issues.
  - empty `items` → `[]`.
- Deterministic when a seeded `rng` is passed.

## Acceptance criteria
- Seeded call is reproducible.
- Statistical test (large N, fixed seed): item with weight `2.0` is selected roughly twice as
  often as an item with weight `1.0`, within tolerance.
- Never returns duplicates; always returns `min(k, len(items))` items.
