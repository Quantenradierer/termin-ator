# Tickets — Restaurant Selector Discord Bot

Derived from the design interview. Each ticket lists context, acceptance criteria,
dependencies, and the design questions (`Qn`) it traces back to.

## Order of work

| # | Ticket | Depends on |
|---|--------|-----------|
| T01 | [Project scaffolding & tooling](T01-project-scaffolding.md) | — |
| T02 | [Configuration loading](T02-configuration.md) | T01 |
| T03 | [Docker & compose packaging](T03-docker-packaging.md) | T01, T02 |
| T04 | [SQLite schema & data-access layer](T04-persistence.md) | T01, T02 |
| T05 | [Bot bootstrap & command registration](T05-bot-bootstrap.md) | T01, T02 |
| T06 | [German user-facing strings module](T06-german-strings.md) | T01 |
| T07 | [Date parsing utility](T07-date-parsing.md) | T01 |
| T08 | [Weighted random sampling utility](T08-weighted-sampling.md) | T01 |
| T09 | [Popularity recalculation (EMA)](T09-popularity-recalc.md) | T01 |
| T10 | [`/add-restaurant` command](T10-cmd-add-restaurant.md) | T04, T05, T06 |
| T11 | [`/list-restaurants` command](T11-cmd-list-restaurants.md) | T04, T05, T06 |
| T12 | [`/remove-restaurant` command](T12-cmd-remove-restaurant.md) | T04, T05, T06 |
| T13 | [`/start-poll` command](T13-cmd-start-poll.md) | T04–T08, T14 |
| T14 | [Poll close handling & recalculation](T14-poll-close.md) | T04, T06, T09 |
| T15 | [Poll lifecycle robustness & startup reconciliation](T15-poll-lifecycle.md) | T13, T14 |
| T16 | [Test suite](T16-tests.md) | T07, T08, T09, T14 |
| T17 | [README & Discord app setup docs](T17-readme-setup.md) | all |
| T18 | [`/reactivate-restaurant` command](T18-cmd-reactivate-restaurant.md) | T04, T05, T06 |

## Cross-cutting design decisions

- Python + `discord.py` 2.7.1; `aiosqlite`; SQLite on a mounted volume. (Q1, Q4, Q11)
- Single shared dataset, no `guild_id` partitioning. (Q3)
- Slash commands, **global** registration, no `GUILD_ID`. (Q2, Q34)
- Command names/args in English; **every** user-facing message in German. Code/comments English. (Q24)
- All commands open to everyone. (Q8)
- One active poll at a time; `/start-poll` force-ends a running poll with no friction. (Q10, Q27)
