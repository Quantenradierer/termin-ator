"""``/add-restaurant`` (T10)."""

from __future__ import annotations

import datetime as _dt

import discord
from discord import app_commands

from .. import strings_de
from ..config import POLL_OPTION_MAX_LEN
from ..db import AlreadyExists
from ..deps import Deps


def setup(tree: app_commands.CommandTree, deps: Deps) -> None:
    @tree.command(
        name="add-restaurant",
        description="Ein Restaurant zur Liste hinzufügen (Name oder URL).",
    )
    @app_commands.describe(text="Name oder URL des Restaurants")
    async def add_restaurant(interaction: discord.Interaction, text: str) -> None:
        text = text.strip()
        if not text:
            await interaction.response.send_message(
                strings_de.restaurant_text_empty(), ephemeral=True
            )
            return
        if len(text) > POLL_OPTION_MAX_LEN:
            await interaction.response.send_message(
                strings_de.restaurant_text_too_long(POLL_OPTION_MAX_LEN), ephemeral=True
            )
            return

        try:
            await deps.db.add_restaurant(text, now=_dt.datetime.now(_dt.UTC))
        except AlreadyExists:
            await interaction.response.send_message(strings_de.restaurant_already_exists(text))
            return

        await interaction.response.send_message(strings_de.restaurant_added(text))
