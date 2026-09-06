"""Shared dependency container passed to command modules (T05)."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .db import Database
from .lifecycle import PollScheduler


@dataclass
class Deps:
    config: Config
    db: Database
    scheduler: PollScheduler
