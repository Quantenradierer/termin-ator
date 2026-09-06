"""Poll close handling & recalculation (T14).

Invoked when the active poll's duration elapses -- from the scheduled task or the startup
reconciliation (T15). Turns final vote counts into new weights, retires the winner, posts the
German announcement, and archives everything atomically.

``close_poll`` is idempotent: if there is no ``active_poll`` row it does nothing, and
``Database.archive_poll`` clears that row as part of its transaction, so a second call is a
no-op.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import logging
import random

from .. import strings_de
from ..config import Config
from ..db import ArchiveOption, Database
from .popularity import OptionResult, pick_winner, recalculate

log = logging.getLogger(__name__)

_FINALISE_RETRIES = 5
_FINALISE_DELAY_S = 2.0


async def _resolve_channel(client: object, channel_id: int) -> object | None:
    channel = client.get_channel(channel_id)  # type: ignore[attr-defined]
    if channel is not None:
        return channel
    fetch = getattr(client, "fetch_channel", None)
    if fetch is None:
        return None
    try:
        return await fetch(channel_id)
    except Exception:
        log.exception("could not resolve channel %s", channel_id)
        return None


async def _finalised_message(channel: object, message_id: int) -> object:
    message = await channel.fetch_message(message_id)  # type: ignore[attr-defined]
    poll = getattr(message, "poll", None)
    if poll is None or poll.is_finalised():
        return message
    try:
        await poll.end()
    except Exception:
        log.exception("Poll.end() failed for message %s", message_id)
    for _ in range(_FINALISE_RETRIES):
        await asyncio.sleep(_FINALISE_DELAY_S)
        message = await channel.fetch_message(message_id)  # type: ignore[attr-defined]
        poll = getattr(message, "poll", None)
        if poll is None or poll.is_finalised():
            break
    return message


async def _safe_send(channel: object, content: str) -> None:
    try:
        await channel.send(content)  # type: ignore[attr-defined]
    except Exception:
        log.exception("failed to send poll-close message")


async def close_poll(
    client: object,
    db: Database,
    config: Config,
    *,
    now: _dt.datetime | None = None,
    rng: random.Random | None = None,
) -> int | None:
    """Close the currently active poll. Returns the archived ``polls.id`` or ``None``."""
    active = await db.get_active_poll()
    if active is None:
        return None

    now = now or _dt.datetime.now(_dt.UTC)
    closed_at = now.isoformat()
    date_label = strings_de.format_date_de(_dt.date.fromisoformat(active.dinner_date))

    channel = await _resolve_channel(client, active.channel_id)
    answer_votes: dict[int, int] = {}
    if channel is not None:
        try:
            message = await _finalised_message(channel, active.message_id)
            poll = getattr(message, "poll", None)
            if poll is not None:
                answer_votes = {a.id: int(a.vote_count) for a in poll.answers}
        except Exception:
            log.exception("failed to read poll results for message %s", active.message_id)

    mapping = await db.get_active_poll_options()  # answer_id -> restaurant_id
    options: list[OptionResult] = []
    texts: dict[int, str] = {}
    for answer_id, restaurant_id in mapping.items():
        restaurant = await db.get_restaurant(restaurant_id)
        texts[restaurant_id] = restaurant.text
        options.append(
            OptionResult(
                restaurant_id=restaurant_id,
                weight_before=restaurant.weight,
                vote_count=answer_votes.get(answer_id, 0),
            )
        )

    total = sum(o.vote_count for o in options)

    # -- zero-vote path (Q19): nothing retired, no weight change ------
    if total == 0:
        poll_id = await db.archive_poll(
            message_id=active.message_id,
            channel_id=active.channel_id,
            dinner_date=active.dinner_date,
            created_at=active.created_at,
            closed_at=closed_at,
            status="no_votes",
            winner_restaurant_id=None,
            tie_broken=False,
            tie_break_kind=None,
            options=[
                ArchiveOption(
                    restaurant_id=o.restaurant_id,
                    restaurant_text=texts[o.restaurant_id],
                    vote_count=0,
                    weight_before=o.weight_before,
                    weight_after=o.weight_before,
                )
                for o in options
            ],
            new_weights={},
            deactivate_restaurant_id=None,
        )
        if channel is not None:
            await _safe_send(channel, strings_de.poll_no_votes(date_label))
        return poll_id

    # -- normal path ------------------------------------------------
    winner_id, tie_kind = pick_winner(options, rng=rng)
    new_weights = recalculate(options, lam=config.ema_lambda, floor=config.weight_floor)

    archive_options = [
        ArchiveOption(
            restaurant_id=o.restaurant_id,
            restaurant_text=texts[o.restaurant_id],
            vote_count=o.vote_count,
            weight_before=o.weight_before,
            weight_after=new_weights.get(o.restaurant_id, o.weight_before),
        )
        for o in options
    ]

    poll_id = await db.archive_poll(
        message_id=active.message_id,
        channel_id=active.channel_id,
        dinner_date=active.dinner_date,
        created_at=active.created_at,
        closed_at=closed_at,
        status="completed",
        winner_restaurant_id=winner_id,
        tie_broken=tie_kind is not None,
        tie_break_kind=tie_kind,
        options=archive_options,
        new_weights=new_weights,
        deactivate_restaurant_id=winner_id,
    )

    if channel is not None and winner_id is not None:
        await _safe_send(channel, strings_de.poll_winner(texts[winner_id], date_label))
    return poll_id


async def archive_discarded(
    db: Database,
    *,
    now: _dt.datetime | None = None,
) -> int | None:
    """Archive the active poll as ``discarded`` -- no winner, no recalculation (Q10/Q27)."""
    active = await db.get_active_poll()
    if active is None:
        return None

    now = now or _dt.datetime.now(_dt.UTC)
    mapping = await db.get_active_poll_options()
    options: list[ArchiveOption] = []
    for restaurant_id in mapping.values():
        restaurant = await db.get_restaurant(restaurant_id)
        options.append(
            ArchiveOption(
                restaurant_id=restaurant_id,
                restaurant_text=restaurant.text,
                vote_count=0,
                weight_before=restaurant.weight,
                weight_after=restaurant.weight,
            )
        )

    return await db.archive_poll(
        message_id=active.message_id,
        channel_id=active.channel_id,
        dinner_date=active.dinner_date,
        created_at=active.created_at,
        closed_at=now.isoformat(),
        status="discarded",
        winner_restaurant_id=None,
        tie_broken=False,
        tie_break_kind=None,
        options=options,
        new_weights={},
        deactivate_restaurant_id=None,
    )
