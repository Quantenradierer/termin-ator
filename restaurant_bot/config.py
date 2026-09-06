"""Configuration loading and validation (T02).

All secrets and tunables come from the environment / a ``.env`` file.
There is intentionally no ``GUILD_ID`` -- slash commands are registered globally (Q34).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants that are NOT environment-configurable (Q20, Q29, Q12/Q13, Q16).
# ---------------------------------------------------------------------------
DEFAULT_POLL_DURATION_HOURS = 168  # 7 days (Q20)
MIN_POLL_DURATION_HOURS = 1
MAX_POLL_DURATION_HOURS = 168
POLL_OPTION_MAX_LEN = 55  # Discord poll answer text limit (Q29)
MAX_POLL_OPTIONS = 10  # (Q12 / Q13)
NEW_RESTAURANT_WEIGHT = 1.0  # (Q16)
MIN_ACTIVE_TO_START_POLL = 2  # (Q13)


class ConfigError(RuntimeError):
    """Raised when the environment is missing or invalid."""


@dataclass(frozen=True)
class Config:
    discord_token: str
    tz: ZoneInfo
    tz_name: str
    sqlite_path: str
    ema_lambda: float
    weight_floor: float
    reminder_hour: int  # local hour on the visit date to ping the winning voters


def _get_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def load_config(*, load_dotenv_file: bool = True) -> Config:
    """Build a :class:`Config` from the current environment.

    Raises :class:`ConfigError` with an actionable message on any problem.
    """
    if load_dotenv_file:
        load_dotenv()

    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        raise ConfigError(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and fill in the bot token."
        )

    tz_name = os.environ.get("TZ", "Europe/Berlin").strip() or "Europe/Berlin"
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"TZ={tz_name!r} is not a valid IANA timezone name.") from exc

    sqlite_path = os.environ.get("SQLITE_PATH", "").strip() or "./data/restaurants.db"

    ema_lambda = _get_float("EMA_LAMBDA", 0.3)
    if not (0.0 < ema_lambda <= 1.0):
        raise ConfigError(f"EMA_LAMBDA must be in (0, 1], got {ema_lambda}")

    weight_floor = _get_float("WEIGHT_FLOOR", 0.05)
    if weight_floor <= 0.0:
        raise ConfigError(f"WEIGHT_FLOOR must be > 0, got {weight_floor}")

    reminder_hour_raw = os.environ.get("REMINDER_HOUR", "").strip() or "9"
    try:
        reminder_hour = int(reminder_hour_raw)
    except ValueError as exc:
        raise ConfigError(
            f"REMINDER_HOUR must be an integer 0-23, got {reminder_hour_raw!r}"
        ) from exc
    if not (0 <= reminder_hour <= 23):
        raise ConfigError(f"REMINDER_HOUR must be 0-23, got {reminder_hour}")

    return Config(
        discord_token=token,
        tz=tz,
        tz_name=tz_name,
        sqlite_path=sqlite_path,
        ema_lambda=ema_lambda,
        weight_floor=weight_floor,
        reminder_hour=reminder_hour,
    )
