"""``/reactivate-restaurant`` -- bring a retired restaurant back into rotation."""

from __future__ import annotations

import discord
from discord import app_commands

from .. import strings_de
from ..deps import Deps

_MAX_CHOICES = 25


def setup(tree: app_commands.CommandTree, deps: Deps) -> None:
    async def retired_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        needle = current.casefold()
        retired = await deps.db.list_retired()
        return [
            app_commands.Choice(name=r.text, value=r.text)
            for r in retired
            if needle in r.text.casefold()
        ][:_MAX_CHOICES]

    @tree.command(
        name="reactivate-restaurant",
        description="Ein bereits besuchtes Restaurant wieder in die Auswahl aufnehmen.",
    )
    @app_commands.describe(restaurant="Welches Restaurant wieder aufgenommen werden soll")
    @app_commands.autocomplete(restaurant=retired_autocomplete)
    async def reactivate_restaurant(interaction: discord.Interaction, restaurant: str) -> None:
        found = await deps.db.find_by_norm(restaurant)
        if found is None or found.active:
            await interaction.response.send_message(
                strings_de.restaurant_not_retired(), ephemeral=True
            )
            return

        await deps.db.reactivate(found.id)
        await interaction.response.send_message(strings_de.restaurant_reactivated(found.text))
