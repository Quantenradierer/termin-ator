# T01 — Project scaffolding & tooling

**Depends on:** none
**Traces to:** Q1, Q33

## Context
Fresh repo (`terminator`), only a stub `main.py`, empty `.venv`, Python 3.14.
Need a clean project layout for a `discord.py` bot with unit-testable pure logic.

## Requirements
- Package layout (flat, single package), e.g.:
  ```
  restaurant_bot/
    __init__.py
    config.py          # T02
    db.py              # T04
    bot.py             # T05  (client + on_ready)
    strings_de.py      # T06
    commands/
      __init__.py
      add.py           # T10
      list.py          # T11
      remove.py        # T12
      poll.py          # T13
    core/
      __init__.py
      dates.py         # T07
      sampling.py      # T08
      popularity.py    # T09
      poll_close.py    # T14
  tests/
  main.py              # entrypoint -> restaurant_bot.bot:run
  ```
- Replace the PyCharm stub `main.py` with a real entrypoint that loads config and starts the bot.
- `requirements.txt` pinned: `discord.py==2.7.1`, `aiosqlite`, `python-dotenv`, `tzdata`.
- `requirements-dev.txt`: `pytest`, `pytest-asyncio`, `ruff`.
- `ruff` config (`pyproject.toml` or `ruff.toml`): lint + format, line length 100, target py314.
- `.gitignore`: `.venv/`, `*.db`, `.env`, `__pycache__/`, `.pytest_cache/`.
- `README.md` skeleton (filled by T17).
- First git commit on a non-`main` branch.

## Acceptance criteria
- `ruff check .` and `ruff format --check .` pass on the empty scaffold.
- `python main.py` fails only with a clear "DISCORD_TOKEN missing" style error (no import errors).
- `pytest` runs (0 tests) with no collection errors.
