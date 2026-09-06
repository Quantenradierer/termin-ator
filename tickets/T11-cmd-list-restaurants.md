# T11 — `/list-restaurants` command

**Depends on:** T04, T05, T06
**Traces to:** Q8, Q22

## Context
Shows the active list **with weights**, plus a collapsed section of already-visited
(deactivated) restaurants.

## Requirements
- Slash command `list-restaurants`, no args, open to everyone.
- Active section:
  - restaurants with `active = 1`
  - sorted by `weight` **descending**, tie-break by `text` ascending (stable, readable)
  - each line: `text` + weight formatted to 2 decimals (e.g. `Pizza Palace — 1.32`)
  - if none: German "noch keine Restaurants"
- Retired section:
  - restaurants with `active = 0`, sorted by `retired_at` descending
  - each line: `text` + retirement date rendered `format_date_de(retired_at)` (date only)
  - wrapped in a Discord spoiler block `||...||` so it renders collapsed (Q22)
  - omitted entirely if there are none
- If the combined message would exceed Discord's 2000-char limit, split into follow-up
  messages (simple chunking by lines).

## Acceptance criteria
- With mixed data: active lines are weight-sorted desc with 2-decimal weights; retired lines
  appear inside `||...||` with dates.
- Empty DB → single message with the "noch keine Restaurants" text and no retired section.
- 60+ restaurants → output is chunked, no message over 2000 chars.
