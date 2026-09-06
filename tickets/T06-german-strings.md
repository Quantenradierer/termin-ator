# T06 — German user-facing strings module

**Depends on:** T01
**Traces to:** Q23, Q24

## Context
Command names and argument names stay English; **every** message the bot sends is German.
Centralise strings so wording is consistent and easy to twei­ak.

## Requirements
- `strings_de.py` with named constants / small formatting helpers. No f-strings scattered
  through command code — command code calls `strings_de.restaurant_added(text)` etc.
- Cover at minimum:
  - add: added, already-on-list, too-long (>55), empty/whitespace
  - list: header for active section, "noch keine Restaurants", retired section header
    ("Bereits besucht"), rendered inside a spoiler block `||...||`
  - remove: removed, not-found, blocked-because-on-active-poll
  - start-poll: bad date format, date in the past, fewer than 2 active restaurants,
    previous poll discarded notice, the poll **question** text
    (`🍽️ Wo essen wir am {Sa, 12.09.2026}?`), companion-message header
  - poll close: winner announcement (`🏆 Gewinner: {text} — {Sa, 12.09.2026}`),
    zero-votes message
  - generic error fallback
- Date rendering helper: `format_date_de(date) -> "Sa, 12.09.2026"` (German weekday abbrev,
  `Europe/Berlin`), shared with T07/T13/T14.
- Weight rendering helper: 2 decimals.

## Acceptance criteria
- Unit test: every helper returns a non-empty German string; `format_date_de` correct for a
  known date incl. weekday abbreviation.
- Grep check (lint or test): command modules contain no user-facing literal strings.
