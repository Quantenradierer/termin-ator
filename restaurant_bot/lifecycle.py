"""Poll lifecycle: scheduled close + startup reconciliation (T15).

``discord.py`` has no "poll ended" gateway event, so closing is driven by an asyncio task
that sleeps until the poll expiry, backed by a check on startup (in case the bot was offline
when the poll ended) and a slow safety-net loop.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import logging

from .config import Config
from .core.poll_close import close_poll
from .db import Database

log = logging.getLogger(__name__)

_SAFETY_NET_INTERVAL_S = 15 * 60
_CLOSE_BUFFER_S = 30


class PollScheduler:
    def __init__(self, client: object, db: Database, config: Config) -> None:
        self._client = client
        self._db = db
        self._config = config
        self._task: asyncio.Task[None] | None = None
        self._safety_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    # -- public API ---------------------------------------------------
    async def reconcile(self) -> None:
        """Close an overdue poll now, or (re)schedule the close task for a live one."""
        active = await self._db.get_active_poll()
        if active is None:
            self.cancel()
            return

        expires_at = _dt.datetime.fromisoformat(active.expires_at)
        now = _dt.datetime.now(_dt.UTC)
        if expires_at <= now:
            await self._run_close()
        else:
            self.schedule(expires_at)

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
        if self._safety_task is not None and not self._safety_task.done():
            self._safety_task.cancel()

    # -- internals --------------------------------------------------
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

    async def _safety_net_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(_SAFETY_NET_INTERVAL_S)
                active = await self._db.get_active_poll()
                if active is None:
                    continue
                expires_at = _dt.datetime.fromisoformat(active.expires_at)
                if expires_at <= _dt.datetime.now(_dt.UTC):
                    log.warning("safety net closing an overdue poll")
                    await self._run_close()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("safety-net loop iteration failed")
