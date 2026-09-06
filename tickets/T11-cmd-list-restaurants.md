# T11 — `/list-restaurants` command

**Depends on:** T04, T05, T06
**Traces to:** Q8, Q22

## Context
Shows the active list **with weights**, plus a section of already-visited
(deactivated) restaurants.

> **Revision:** the spoiler/"collapse" wrapping was removed (Discord renders it poorly);
> the retired section is now plain text. Retired lines show the **dinner date the
> restaurant won** (`restaurants.visit_date`), not the poll-close time.

## Requirements
- Slash command `list-restaurants`, no args, open to everyone.
- Active section:
  - restaurants with `active = 1`
  - sorted by `weight` **descending**, tie-break by `text` ascending (stable, readable)
  - each line: `text` + weight formatted to 2 decimals (e.g. `Pizza Palace — 1.32`)
  - if none: German "noch keine Restaurants"
- Retired section:
  - restaurants with `active = 0`, sorted by `visit_date` descending
  - each line: `text` + the dinner date it won, rendered `format_date_de(visit_date)`
    (e.g. `• Pizza Palace (besucht am Sa, 12.09.2026)`)
  - plain text under a `**Bereits besucht:**` header — no spoiler block
  - omitted entirely if there are none
- If the combined message would exceed Discord's 2000-char limit, split into follow-up
  messages (simple chunking by lines).

## Acceptance criteria
- With mixed data: active lines are weight-sorted desc with 2-decimal weights; retired lines
  show the dinner date, with no `||` spoiler markup.
- Empty DB → single message with the "noch keine Restaurants" text and no retired section.
- 60+ restaurants → output is chunked, no message over 2000 chars.
