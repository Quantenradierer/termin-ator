# Restaurant Selector — Discord Bot

Helps a group of friends pick a restaurant. Friends add restaurants to a shared list;
anyone can start a poll for a given dinner date. The bot builds a Discord poll from up to
10 candidates (chosen by weighted popularity when there are more than 10), and when the poll
closes it recalculates each candidate's popularity, permanently retires the winner
("we're going there"), and announces it.

All bot replies are in **German**; the command names are English.

## Commands

| Command | Who | What it does |
|---|---|---|
| `/add-restaurant text:<name or URL>` | everyone | Adds one free-text entry (name, URL, Maps link — anything). Max **55 characters** (Discord poll limit). A case-insensitive duplicate is ignored. |
| `/list-restaurants` | everyone | Active restaurants sorted by popularity (weight shown), plus a "Bereits besucht" section listing each retired winner with the **dinner date** it won. |
| `/start-poll date:<date> [duration_hours:<1–168>]` | everyone | Starts a poll. `date` is the **dinner date** (informational). Accepts `12.09.2026`, `12.09.` / `12.09` (year → next occurrence), or `2026-09-12`. Duration defaults to **168 h (7 days)**. Approval voting (pick as many as you like). Posts a companion message with the raw (clickable) entries. If a poll is already running it is discarded and replaced. |
| `/remove-restaurant restaurant:<name>` | everyone | Hard-deletes an active entry (autocomplete). Blocked while that entry is on the running poll. |
| `/reactivate-restaurant restaurant:<name>` | everyone | Brings a retired restaurant back into rotation (autocomplete over retired). Its weight is reset to `1.0`. |

### How selection & popularity work

- Every restaurant has a **weight** (a float). New restaurants start at `1.0` = "average".
- Picking the poll's ≤10 options: if ≤10 active, all go on; otherwise a **weighted random
  sample** (probability ∝ weight).
- When a poll closes, for every restaurant that was on it:
  `new = (1 − λ)·old + λ·(n × vote_share)` with `λ = 0.3` (env `EMA_LAMBDA`), floored at
  `0.05` (env `WEIGHT_FLOOR`). `n` is the number of options; `vote_share` is that
  restaurant's fraction of all approvals. Restaurants not on the poll are unchanged.
- **Winner** = most approvals. Tie → highest current weight wins; still tied → random.
  The winner is **retired** (dropped from future polls); bring it back later with
  `/reactivate-restaurant`, which resets its weight to `1.0`.
- On the **visit date** at `REMINDER_HOUR` local time, the bot posts a reminder in the
  poll's channel that @-mentions everyone who voted for the winner. Survives restarts; if
  the bot was down for more than 12 h past the due time the reminder is skipped.
- **Zero votes** → no winner, no retirement, no weight changes.

## Discord application setup

1. Create an application and a bot at <https://discord.com/developers/applications>.
2. Copy the **bot token**.
3. Invite the bot with scopes `bot` and `applications.commands`, and permissions:
   **Send Messages**, **Send Polls** (Create Polls), **Read Message History**.
   No privileged intents are required.
   Invite URL template:
   `https://discord.com/api/oauth2/authorize?client_id=<APP_ID>&scope=bot%20applications.commands&permissions=274877991936`
4. Commands are registered **globally** and can take up to ~1 hour to appear the first time.

## Configuration

Copy `.env.example` to `.env` and fill it in:

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `DISCORD_TOKEN` | yes | — | Bot token |
| `TZ` | no | `Europe/Berlin` | IANA timezone for parsing/rendering dinner dates |
| `SQLITE_PATH` | no | `./data/restaurants.db` | Database file (in Docker: on the mounted volume) |
| `EMA_LAMBDA` | no | `0.3` | Popularity smoothing factor, `0 < λ ≤ 1` |
| `WEIGHT_FLOOR` | no | `0.05` | Minimum weight after a recalculation |
| `REMINDER_HOUR` | no | `9` | Local hour (0–23) on the visit date to ping the winning voters |

## Run with Docker

```bash
cp .env.example .env      # then edit .env
docker compose up -d
docker compose logs -f
```

The SQLite database lives on the named volume `bot-data` (`/app/data` in the container) and
survives rebuilds. Back it up by copying the `.db` file out of the volume.

## Run locally (development)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env      # then edit .env
python main.py
```

## Development

```bash
ruff check . && ruff format --check .
pytest
```

Tests cover the pure logic (date parsing, weighted sampling, EMA recalculation, tie-break,
persistence transactions, poll-close paths). The Discord layer is mocked.

## Project layout

```
restaurant_bot/
  config.py        env loading & validation
  db.py            SQLite schema + async data access
  bot.py           discord.py client, command registration, error handler
  lifecycle.py     scheduled poll close + startup reconciliation
  strings_de.py    all user-facing German text
  commands/        add · list_cmd · remove · reactivate · poll
  core/            dates · sampling · popularity · poll_close
tickets/           the design tickets this implementation follows
tests/
```
