"""``/list-restaurants`` (T11)."""

from __future__ import annotations

import datetime as _dt

import discord
from discord import app_commands

from .. import strings_de
from ..deps import Deps

_DISCORD_MSG_LIMIT = 2000


def _visit_label(visit_date: str | None) -> str:
    if not visit_date:
        return "?"
    try:
        return strings_de.format_date_de(_dt.date.fromisoformat(visit_date))
    except ValueError:
        return "?"


def _chunk(lines: list[str], limit: int = _DISCORD_MSG_LIMIT - 100) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for line in lines:
        add = len(line) + 1
        if current and size + add > limit:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += add
    if current:
        chunks.append("\n".join(current))
    return chunks or [""]


def setup(tree: app_commands.CommandTree, deps: Deps) -> None:
    @tree.command(
        name="list-restaurants",
        description="Alle Restaurants auf der Liste anzeigen.",
    )
    async def list_restaurants(interaction: discord.Interaction) -> None:
        active = await deps.db.list_active()
        retired = await deps.db.list_retired()

        lines: list[str] = []
        if not active:
            lines.append(strings_de.list_empty())
        else:
            lines.append(strings_de.list_header_active())
            for i, r in enumerate(active, start=1):
                lines.append(strings_de.list_active_line(i, r.text, r.weight))

        blocks = _chunk(lines)
        if retired:
            retired_lines = [
                strings_de.list_retired_line(r.text, _visit_label(r.visit_date)) for r in retired
            ]
            blocks.append(strings_de.list_retired_block(retired_lines))

        await interaction.response.send_message(blocks[0])
        for block in blocks[1:]:
            await interaction.followup.send(block)
