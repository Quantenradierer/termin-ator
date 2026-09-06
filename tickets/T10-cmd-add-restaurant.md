# T10 — `/add-restaurant` command

**Depends on:** T04, T05, T06
**Traces to:** Q6, Q7, Q8, Q29

## Context
Adds one free-text string — a name, a URL, a Maps link, anything. Open to everyone.
Structured fields (name/url/hours) are explicitly out of scope for now.

## Requirements
- Slash command `add-restaurant` with one required string arg (`text`).
- Normalisation for storage: strip leading/trailing whitespace; collapse nothing else.
- Validation:
  - empty / whitespace-only → German error
  - `len(text) > 55` → German error (Discord poll option limit, Q29)
- Duplicate detection: `text_norm = text.strip().casefold()`. If a row with that `text_norm`
  exists (active **or** retired) → reply German "steht schon auf der Liste", do **not** insert,
  do not error.
- On success: insert with `weight = 1.0`, `active = 1`, `created_at = now UTC`; reply German
  confirmation echoing the stored string.
- Replies can be public (non-ephemeral) so the group sees additions.

## Acceptance criteria
- Adding `Pizza Palace` then `pizza palace` → second is rejected as duplicate, one row exists.
- 56-character string → rejected, nothing stored.
- Whitespace-only string → rejected.
- Adding a string that matches a **retired** restaurant → duplicate message (no resurrection).
