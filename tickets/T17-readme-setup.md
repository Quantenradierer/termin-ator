# T17 — README & Discord app setup docs

**Depends on:** all
**Traces to:** Q11, Q24, Q34

## Context
A friend needs to be able to stand this up from scratch.

## Requirements
- `README.md` covering:
  - **What it does** — one paragraph, the four commands.
  - **Discord application setup:**
    - create app + bot at the Developer Portal
    - required bot scopes: `bot`, `applications.commands`
    - required bot permissions: **Send Messages**, **Send Polls** (Create Polls),
      **Read Message History**
    - no privileged intents needed
    - invite URL template
    - note: global commands can take up to ~1 h to appear after first deploy (Q34)
  - **Configuration:** the `.env` table (from T02) + `cp .env.example .env`.
  - **Run with Docker:** `docker compose up -d`; where the SQLite volume lives; how to back
    up (copy the `.db` file).
  - **Run locally (dev):** venv, `pip install -r requirements.txt -r requirements-dev.txt`,
    `python main.py`.
  - **Commands reference:** each command, its arguments, the accepted date formats (T07),
    the 55-char restaurant limit, the "one poll at a time / new poll discards the old" rule.
  - **How selection & popularity work:** short, plain-language description of weighted
    sampling and the EMA update, and that a poll winner is retired permanently.
  - **Development:** `ruff`, `pytest`.
- Keep it German-user-friendly but the README itself can be English (dev-facing).

## Acceptance criteria
- Following the README from a clean machine yields a running bot that responds to
  `/add-restaurant`.
- The `.env` table in the README matches `.env.example` and T02.
