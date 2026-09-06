"""``/start-poll`` (T13)."""

from __future__ import annotations

import datetime as _dt
import logging
import random

import discord
from discord import app_commands

from .. import strings_de
from ..config import (
    DEFAULT_POLL_DURATION_HOURS,
    MAX_POLL_DURATION_HOURS,
    MAX_POLL_OPTIONS,
    MIN_ACTIVE_TO_START_POLL,
    MIN_POLL_DURATION_HOURS,
)
from ..core.dates import BadDateFormat, DateInPast, parse_dinner_date
from ..core.poll_close import archive_discarded
from ..core.sampling import weighted_sample_without_replacement
from ..db import ActivePoll, Restaurant
from ..deps import Deps

log = logging.getLogger(__name__)


def _select(restaurants: list[Restaurant], rng: random.Random) -> list[Restaurant]:
    if len(restaurants) > MAX_POLL_OPTIONS:
        weights = [r.weight for r in restaurants]
        return weighted_sample_without_replacement(restaurants, weights, MAX_POLL_OPTIONS, rng=rng)
    chosen = list(restaurants)
    rng.shuffle(chosen)
    return chosen


async def _discard_existing(interaction: discord.Interaction, deps: Deps) -> bool:
    existing = await deps.db.get_active_poll()
    if existing is None:
        return False

    deps.scheduler.cancel()
    try:
        channel = interaction.client.get_channel(
            existing.channel_id
        ) or await interaction.client.fetch_channel(existing.channel_id)
        message = await channel.fetch_message(existing.message_id)
        if message.poll is not None and not message.poll.is_finalised():
            await message.poll.end()
    except Exception:
        log.exception("failed to end discarded poll message %s", existing.message_id)

    await archive_discarded(deps.db)
    return True


def setup(tree: app_commands.CommandTree, deps: Deps) -> None:
    @tree.command(
        name="start-poll",
        description="Eine Restaurant-Umfrage für ein Datum starten.",
    )
    @app_commands.describe(
        date="Datum, z. B. 12.09.2026, 12.09. oder 2026-09-12",
        duration_hours=f"Laufzeit in Stunden (Standard {DEFAULT_POLL_DURATION_HOURS} = 7 Tage)",
    )
    async def start_poll(
        interaction: discord.Interaction,
        date: str,
        duration_hours: int | None = None,
    ) -> None:
        today = _dt.datetime.now(deps.config.tz).date()
        try:
            dinner = parse_dinner_date(date, today=today)
        except DateInPast:
            await interaction.response.send_message(strings_de.poll_date_in_past(), ephemeral=True)
            return
        except BadDateFormat:
            await interaction.response.send_message(strings_de.poll_bad_date(), ephemeral=True)
            return

        duration = duration_hours or DEFAULT_POLL_DURATION_HOURS
        duration = max(MIN_POLL_DURATION_HOURS, min(MAX_POLL_DURATION_HOURS, duration))

        active_restaurants = await deps.db.list_active()
        if len(active_restaurants) < MIN_ACTIVE_TO_START_POLL:
            await interaction.response.send_message(
                strings_de.poll_not_enough_restaurants(MIN_ACTIVE_TO_START_POLL),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        discarded = await _discard_existing(interaction, deps)

        rng = random.Random()
        chosen = _select(active_restaurants, rng)
        date_label = strings_de.format_date_de(dinner)

        poll_obj = discord.Poll(
            question=strings_de.poll_question(date_label),
            duration=_dt.timedelta(hours=duration),
            multiple=True,
        )
        for restaurant in chosen:
            poll_obj.add_answer(text=restaurant.text)

        channel = interaction.channel
        poll_message = await channel.send(poll=poll_obj)

        sent_answers = poll_message.poll.answers
        options = [(sent_answers[i].id, chosen[i].id) for i in range(len(chosen))]

        now = _dt.datetime.now(_dt.UTC)
        expires_at = poll_message.poll.expires_at or (now + _dt.timedelta(hours=duration))
        await deps.db.set_active_poll(
            ActivePoll(
                message_id=poll_message.id,
                channel_id=channel.id,
                dinner_date=dinner.isoformat(),
                duration_h=duration,
                created_at=now.isoformat(),
                expires_at=expires_at.isoformat(),
            ),
            options,
        )

        companion = [strings_de.poll_companion_header(date_label)]
        for i, restaurant in enumerate(chosen, start=1):
            companion.append(strings_de.poll_companion_line(i, restaurant.text))
        await channel.send("\n".join(companion))

        deps.scheduler.schedule(expires_at)

        reply = strings_de.poll_started(date_label)
        if discarded:
            reply = f"{strings_de.poll_previous_discarded()}\n{reply}"
        await interaction.followup.send(reply, ephemeral=True)
