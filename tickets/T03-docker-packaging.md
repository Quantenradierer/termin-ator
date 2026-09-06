# T03 — Docker & compose packaging

**Depends on:** T01, T02
**Traces to:** Q11

## Context
Bot ships as a Docker container; SQLite lives on a mounted volume so data survives
container rebuilds and "travels" with the deployment (Q3 rationale).

## Requirements
- `Dockerfile`:
  - base `python:3.14-slim`
  - install `tzdata` (slim images lack zoneinfo data — needed for `Europe/Berlin`)
  - non-root user
  - copy source, `pip install -r requirements.txt`
  - `CMD ["python", "main.py"]`
- `docker-compose.yml`:
  - one service `bot`
  - `env_file: .env`
  - named volume (or bind mount `./data`) mounted at the dir holding `SQLITE_PATH`
  - `restart: unless-stopped`
- `.dockerignore`: `.venv`, `.git`, `tests`, `*.db`, `.env`, `__pycache__`.
- `data/` dir kept in repo via `.gitkeep`; `*.db` git-ignored.

## Acceptance criteria
- `docker compose build` succeeds.
- `docker compose up` with a dummy token starts, creates the DB file on the volume, then
  exits/loops on auth failure with a clear log line (no tracebacks about missing tzdata or
  missing directories).
- Stopping and recreating the container preserves the DB file.
