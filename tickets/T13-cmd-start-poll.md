# T13 — `/start-poll` command

**Depends on:** T04, T05, T06, T07, T08; coordinates with T14
**Traces to:** Q5, Q8, Q9, Q10, Q12, Q13, Q20, Q21, Q26, Q27, Q29, Q30, Q31

## Context
Creates a Discord **native poll** among up to 10 active restaurants and a companion
reference message with the raw (clickable) strings.

## Requirements
### Arguments
- `date` (string, required) → `parse_dinner_date` (T07). Errors → German messages.
- `duration_hours` (integer, optional) → default `168`; clamp to `1..168` (Q20).

### Preconditions
- Count active restaurants:
  - `< 2` → refuse with German message (Q13). No poll created.
- Existing active poll (`get_active_poll()` returns a row) → **force-discard, no friction**
  (Q10/Q27):
  1. best-effort `await old_message.end()` so voting stops
  2. archive the old poll with `status = 'discarded'`, **no winner, no recalculation**
  3. `clear_active_poll()`
  4. include a short German "vorherige Umfrage verworfen" line in the reply

### Candidate selection
- Pool = active restaurants.
- `count <= 10` → all of them, order shuffled.
- `count > 10` → `weighted_sample_without_replacement(items, weights, 10, rng)` (T08).

### Poll creation
- `discord.Poll(question=strings_de.poll_question(format_date_de(date)),
   duration=timedelta(hours=duration_hours), multiple=True)` — **multi-select / approval
   voting** (Q21).
- One answer per selected restaurant, `text = restaurant.text` (guaranteed ≤ 55 by T10).
- Send in the channel the command was used in.

### Companion message (Q30)
- Posted immediately after, same channel.
- Numbered list, order matching the poll answers, each line the **raw** restaurant string so
  Discord auto-links URLs. German header line.
- No `@here` / `@everyone` / role ping (Q31).

### Persistence
- `set_active_poll(message_id, channel_id, dinner_date, duration_h, created_at, expires_at)`
  plus `active_poll_options` mapping `answer_id → restaurant_id`.
- Schedule the close handler for `expires_at` (hand off to T14/T15).

### Reply
- Ephemeral or short public confirmation in German (poll + companion message are the real
  output).

## Acceptance criteria
- `< 2` active → no poll, German refusal.
- 8 active → poll has all 8, no sampling.
- 15 active → poll has exactly 10; over many runs, higher-weight restaurants appear more often.
- Running `/start-poll` while a poll is live → old poll message ends, old poll archived as
  `discarded`, new poll starts, reply mentions the discard.
- Companion message lines are raw strings and URLs render as clickable links.
- `active_poll` + `active_poll_options` rows reflect the new poll.
