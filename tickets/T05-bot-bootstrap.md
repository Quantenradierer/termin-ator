# T05 — Bot bootstrap & command registration

**Depends on:** T01, T02
**Traces to:** Q1, Q2, Q8, Q34

## Context
`discord.py` client with an app-command tree, **global** registration (no `GUILD_ID`).
All commands open to everyone (no permission checks — Q8).

## Requirements
- `bot.py`:
  - `discord.Client` + `app_commands.CommandTree` (or `commands.Bot`).
  - Intents: `discord.Intents.default()` — poll vote events need no privileged intent;
    `message_content` **not** required.
  - `run()` entrypoint: `init_db()` (T04), then `client.run(config.DISCORD_TOKEN)`.
  - `on_ready`:
    - `await tree.sync()` (global).
    - Call poll reconciliation hook (T15) — stub acceptable until T15 lands.
    - Log the invite URL / connected guild names.
- Command modules register onto the shared tree via a `setup(tree, deps)` function so each
  command lives in its own file (T10–T13).
- A small `deps` container (config + db handle + strings) passed to command callbacks.
- Central error handler for app commands: log full error, reply to the user with a generic
  German "Da ist etwas schiefgelaufen." ephemeral message.

## Acceptance criteria
- Bot connects with a real token and `/`-commands appear in the client (allow propagation delay).
- Unknown/failing command → user sees the German fallback, full traceback in logs.
- No privileged-intent warning in the console.
