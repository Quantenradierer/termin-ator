"""Bot bootstrap & command registration (T05).

Slash commands are registered **globally** (Q34) -- no ``GUILD_ID``. All commands are open to
everyone (Q8). The bot needs no privileged intents.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from .commands import add as add_cmd
from .commands import list_cmd, poll, reactivate, remove
from .config import Config, ConfigError, load_config
from .db import Database
from .deps import Deps
from .lifecycle import PollScheduler
from .strings_de import generic_error

log = logging.getLogger(__name__)


class RestaurantBot(discord.Client):
    def __init__(self, config: Config) -> None:
        super().__init__(intents=discord.Intents.default())
        self.config = config
        self.tree = app_commands.CommandTree(self)
        self.db: Database | None = None
        self.scheduler: PollScheduler | None = None
        self._synced = False

    async def setup_hook(self) -> None:
        self.db = await Database.connect(self.config.sqlite_path)
        self.scheduler = PollScheduler(self, self.db, self.config)

        deps = Deps(config=self.config, db=self.db, scheduler=self.scheduler)
        for module in (add_cmd, list_cmd, remove, reactivate, poll):
            module.setup(self.tree, deps)
        self.tree.on_error = self._on_app_command_error

        await self.tree.sync()
        self._synced = True
        log.info("Slash commands synced globally.")

    async def on_ready(self) -> None:
        assert self.scheduler is not None
        log.info(
            "Logged in as %s (guilds: %s)",
            self.user,
            ", ".join(g.name for g in self.guilds) or "none",
        )
        await self.scheduler.reconcile()
        self.scheduler.start_safety_net()

    async def close(self) -> None:
        if self.scheduler is not None:
            await self.scheduler.shutdown()
        if self.db is not None:
            await self.db.close()
        await super().close()

    async def _on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        log.exception("app command error", exc_info=error)
        try:
            if interaction.response.is_done():
                await interaction.followup.send(generic_error(), ephemeral=True)
            else:
                await interaction.response.send_message(generic_error(), ephemeral=True)
        except discord.DiscordException:
            pass


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        config = load_config()
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from None
    RestaurantBot(config).run(config.discord_token, log_handler=None)
