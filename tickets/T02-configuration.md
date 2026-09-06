# T02 — Configuration loading

**Depends on:** T01
**Traces to:** Q11, Q14, Q20, Q26, Q31, Q34

## Context
All secrets and tunables come from environment / `.env` (loaded via `python-dotenv`).
No `GUILD_ID` (global command registration, Q34). Poll duration default is **not** in env (Q20).

## Requirements
- `config.py` exposes a frozen `Config` object built from the environment:

  | Var | Required | Default | Notes |
  |-----|----------|---------|-------|
  | `DISCORD_TOKEN` | yes | — | bot token |
  | `TZ` | no | `Europe/Berlin` | IANA name; used for date parsing & rendering (Q26) |
  | `SQLITE_PATH` | no | `./data/restaurants.db` | on the mounted volume in Docker (Q11) |
  | `EMA_LAMBDA` | no | `0.3` | recalculation smoothing λ (Q14) |
  | `WEIGHT_FLOOR` | no | `0.05` | minimum weight after recalculation (Q14) |

- Missing `DISCORD_TOKEN` → raise with a clear message and non-zero exit.
- Validate: `TZ` resolvable via `zoneinfo.ZoneInfo`; `0 < EMA_LAMBDA <= 1`; `WEIGHT_FLOOR > 0`.
- `.env.example` committed with every var and its default, `DISCORD_TOKEN=` blank.
- Constants that are **not** env-configurable, defined in code:
  - default poll duration `168` hours, clamp range `1..168` (Q20)
  - Discord poll option max length `55` (Q29)
  - max restaurants on a poll `10` (Q12/Q13)
  - new-restaurant starting weight `1.0` (Q16)

## Acceptance criteria
- Unit test: valid env → `Config` populated; bad `TZ` / bad `EMA_LAMBDA` / missing token each raise.
- `.env.example` matches the table above.
