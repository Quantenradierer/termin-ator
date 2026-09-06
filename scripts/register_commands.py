"""One-shot: register the slash commands directly into one server so they show up NOW.

Global command registration (what the bot does on normal startup) can take up to ~1 hour to
propagate the first time. Running this once copies the same commands into a single guild,
where they appear immediately.

Usage
-----
    python scripts/register_commands.py <GUILD_ID>            # add them now
    python scripts/register_commands.py <GUILD_ID> --clear    # remove the guild copies

Get <GUILD_ID>: Discord → User Settings → Advanced → enable "Developer Mode", then
right-click the server icon → "Copy Server ID".

Note: once the global commands have propagated (~1 h after the bot has run normally), the
guild copies become duplicates. Run again with --clear to remove them; the global ones stay.

Reads DISCORD_TOKEN from the environment / .env, same as the bot.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import discord
from discord import app_commands

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from restaurant_bot.commands import add as add_cmd
from restaurant_bot.commands import list_cmd, poll, reactivate, remove
from restaurant_bot.config import ConfigError, load_config
from restaurant_bot.deps import Deps


def _parse_args(argv: list[str]) -> tuple[int, bool]:
    args = [a for a in argv[1:] if a]
    clear = "--clear" in args
    args = [a for a in args if a != "--clear"]
    if len(args) != 1 or not args[0].isdigit():
        sys.exit("Usage: python scripts/register_commands.py <GUILD_ID> [--clear]")
    return int(args[0]), clear


class _Registrar(discord.Client):
    def __init__(self, config, guild_id: int, clear: bool) -> None:
        super().__init__(intents=discord.Intents.none())
        self._config = config
        self._guild = discord.Object(id=guild_id)
        self._clear = clear
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        try:
            if self._clear:
                self.tree.clear_commands(guild=self._guild)
                await self.tree.sync(guild=self._guild)
                print(f"Cleared guild-scoped commands from {self._guild.id}.")
            else:
                # Register the same commands the bot uses. The callbacks are never
                # invoked here, so a dependency stub is fine.
                deps = Deps(config=self._config, db=None, scheduler=None)  # type: ignore[arg-type]
                for module in (add_cmd, list_cmd, remove, reactivate, poll):
                    module.setup(self.tree, deps)
                self.tree.copy_global_to(guild=self._guild)
                synced = await self.tree.sync(guild=self._guild)
                print(f"Registered {len(synced)} commands into guild {self._guild.id}:")
                for cmd in synced:
                    print(f"  /{cmd.name}")
        finally:
            await self.close()


async def _amain() -> None:
    guild_id, clear = _parse_args(sys.argv)
    try:
        config = load_config()
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from None

    client = _Registrar(config, guild_id, clear)
    async with client:
        await client.start(config.discord_token)


if __name__ == "__main__":
    asyncio.run(_amain())
