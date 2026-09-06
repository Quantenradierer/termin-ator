"""Poll lifecycle: scheduled close, startup reconciliation, and visit-day reminders (T15).

``discord.py`` has no "poll ended" gateway event, so closing is driven by an asyncio task
that sleeps until the poll expiry, backed by a check on startup (in case the bot was offline
when the poll ended) and a slow safety-net loop.

The same scheduler also fires the visit-day reminder: on the dinner date at
``config.reminder_hour`` local time it pings everyone who voted for the winning restaurant.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import logging

import discord

from . import strings_de
from .config import Config
from .core.poll_close import _resolve_channel, close_poll
from .db import Database

log = logging.getLogger(__name__)

_SAFETY_NET_INTERVAL_S = 15 * 60
_CLOSE_BUFFER_S = 30
# If the bot was down past this much after a reminder was due, skip it silently.
_REMINDER_STALE = _dt.timedelta(hours=12)


class PollScheduler:
    def __init__(self, client: object, db: Database, config: Config) -> None:
        self._client = client
        self._db = db
        self._config = config
        self._task: asyncio.Task[None] | None = None
        self._safety_task: asyncio.Task[None] | None = None
        self._reminder_tasks: dict[int, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()
        self._reminder_lock = asyncio.Lock()

    # -- public API ---------------------------------------------------
    async def reconcile(self) -> None:
        """Close an overdue poll now / (re)schedule a live one, and (re)schedule reminders."""
        active = await self._db.get_active_poll()
        if active is None:
            self.cancel()
        else:
            expires_at = _dt.datetime.fromisoformat(active.expires_at)
            if expires_at <= _dt.datetime.now(_dt.UTC):
                await self._run_close()
            else:
                self.schedule(expires_at)
        await self._reconcile_reminders()

    def schedule(self, expires_at: _dt.datetime) -> None:
        """(Re)arm the close task for ``expires_at``."""
        self.cancel()
        delay = (expires_at - _dt.datetime.now(_dt.UTC)).total_seconds() + _CLOSE_BUFFER_S
        self._task = asyncio.create_task(self._sleep_then_close(max(delay, 0.0)))

    def cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None

    def start_safety_net(self) -> None:
        if self._safety_task is None or self._safety_task.done():
            self._safety_task = asyncio.create_task(self._safety_net_loop())

    async def shutdown(self) -> None:
        self.cancel()
        for task in (self._safety_task, *self._reminder_tasks.values()):
            if task is not None and not task.done():
                task.cancel()
        self._reminder_tasks.clear()

    # -- poll close ------------------------------------------------
    async def _sleep_then_close(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            await self._run_close()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("scheduled poll close failed")

    async def _run_close(self) -> None:
        async with self._lock:
            try:
                await close_poll(self._client, self._db, self._config)
            except Exception:
                log.exception("close_poll raised")
        # A completed poll may have created a reminder row.
        await self._reconcile_reminders()

    async def _safety_net_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(_SAFETY_NET_INTERVAL_S)
                active = await self._db.get_active_poll()
                if active is not None:
                    expires_at = _dt.datetime.fromisoformat(active.expires_at)
                    if expires_at <= _dt.datetime.now(_dt.UTC):
                        log.warning("safety net closing an overdue poll")
                        await self._run_close()
                await self._reconcile_reminders()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("safety-net loop iteration failed")

    # -- visit-day reminders -------------------------------------
    async def _reconcile_reminders(self) -> None:
        now = _dt.datetime.now(_dt.UTC)
        for reminder in await self._db.pending_reminders():
            existing = self._reminder_tasks.get(reminder.id)
            if existing is not None and not existing.done():
                continue
            remind_at = _dt.datetime.fromisoformat(reminder.remind_at)
            if remind_at <= now:
                await self._fire_reminder(reminder.id)
            else:
                delay = (remind_at - now).total_seconds()
                self._reminder_tasks[reminder.id] = asyncio.create_task(
                    self._sleep_then_fire(delay, reminder.id)
                )

    async def _sleep_then_fire(self, delay: float, reminder_id: int) -> None:
        try:
            await asyncio.sleep(max(delay, 0.0))
            await self._fire_reminder(reminder_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("scheduled reminder %s failed", reminder_id)
        finally:
            self._reminder_tasks.pop(reminder_id, None)

    async def _fire_reminder(self, reminder_id: int) -> None:
        async with self._reminder_lock:
            reminder = await self._db.get_reminder(reminder_id)
            if reminder is None or reminder.sent:
                return

            now = _dt.datetime.now(_dt.UTC)
            remind_at = _dt.datetime.fromisoformat(reminder.remind_at)
            if now > remind_at + _REMINDER_STALE:
                log.warning("reminder %s is stale; marking sent without posting", reminder_id)
                await self._db.mark_reminder_sent(reminder_id)
                return

            channel = await _resolve_channel(self._client, reminder.channel_id)
            if channel is None:
                log.warning("reminder %s: channel %s unresolved", reminder_id, reminder.channel_id)
                return  # try again on the next reconcile / safety-net tick

            mentions = " ".join(f"<@{uid}>" for uid in reminder.voter_ids)
            try:
                await channel.send(  # type: ignore[attr-defined]
                    strings_de.visit_reminder(reminder.restaurant_text, mentions),
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
            except Exception:
                log.exception("failed to send reminder %s", reminder_id)
                return
            await self._db.mark_reminder_sent(reminder_id)
