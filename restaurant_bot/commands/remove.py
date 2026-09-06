"""``/remove-restaurant`` (T12)."""

from __future__ import annotations

import discord
from discord import app_commands

from .. import strings_de
from ..deps import Deps

_MAX_CHOICES = 25


def setup(tree: app_commands.CommandTree, deps: Deps) -> None:
    async def restaurant_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        needle = current.casefold()
        active = await deps.db.list_active()
        return [
            app_commands.Choice(name=r.text, value=r.text)
            for r in active
            if needle in r.text.casefold()
        ][:_MAX_CHOICES]

    @tree.command(
        name="remove-restaurant",
        description="Ein Restaurant von der Liste entfernen (z. B. Tippfehler).",
    )
    @app_commands.describe(restaurant="Welches Restaurant entfernt werden soll")
    @app_commands.autocomplete(restaurant=restaurant_autocomplete)
    async def remove_restaurant(interaction: discord.Interaction, restaurant: str) -> None:
        found = await deps.db.find_by_norm(restaurant)
        if found is None or not found.active:
            await interaction.response.send_message(
                strings_de.restaurant_not_found(), ephemeral=True
            )
            return

        active_poll = await deps.db.get_active_poll()
        if active_poll is not None:
            mapping = await deps.db.get_active_poll_options()
            if found.id in mapping.values():
                await interaction.response.send_message(
                    strings_de.restaurant_on_active_poll(), ephemeral=True
                )
                return

        await deps.db.hard_delete(found.id)
        await interaction.response.send_message(strings_de.restaurant_removed(found.text))
