"""All user-facing text, in German (T06 / Q24).

Command code never contains user-facing literals -- it calls these helpers so wording stays
consistent and easy to change.
"""

from __future__ import annotations

import datetime as _dt
from zoneinfo import ZoneInfo

_WEEKDAYS_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def format_date_de(value: _dt.date | _dt.datetime, *, tz: ZoneInfo | None = None) -> str:
    """Render a date as ``Sa, 12.09.2026`` with a German weekday abbreviation."""
    if isinstance(value, _dt.datetime):
        if tz is not None:
            value = value.astimezone(tz)
        value = value.date()
    return f"{_WEEKDAYS_DE[value.weekday()]}, {value:%d.%m.%Y}"


def format_weight(weight: float) -> str:
    return f"{weight:.2f}"


# --- /add-restaurant -------------------------------------------------------
def restaurant_added(text: str) -> str:
    return f"✅ **{text}** wurde zur Liste hinzugefügt."


def restaurant_already_exists(text: str) -> str:
    return f"ℹ️ **{text}** steht schon auf der Liste."


def restaurant_text_empty() -> str:
    return "❌ Bitte gib einen Namen oder eine URL an."


def restaurant_text_too_long(limit: int) -> str:
    return (
        f"❌ Das ist zu lang (max. {limit} Zeichen, wegen Discord-Umfragen). Bitte kürzer fassen."
    )


# --- /list-restaurants ---------------------------------------------------
def list_header_active() -> str:
    return "**🍽️ Restaurants zur Auswahl** (nach Beliebtheit):"


def list_empty() -> str:
    return (
        "Es stehen noch keine Restaurants auf der Liste. Füge welche mit `/add-restaurant` hinzu."
    )


def list_active_line(index: int, text: str, weight: float) -> str:
    return f"{index}. {text} — {format_weight(weight)}"


def list_retired_block(lines: list[str]) -> str:
    body = "\n".join(lines)
    return f"**Bereits besucht:**\n||{body}||"


def list_retired_line(text: str, retired_on: str) -> str:
    return f"• {text} ({retired_on})"


# --- /remove-restaurant ------------------------------------------------
def restaurant_removed(text: str) -> str:
    return f"🗑️ **{text}** wurde von der Liste entfernt."


def restaurant_not_found() -> str:
    return "❌ Dieses Restaurant steht nicht (mehr) auf der aktiven Liste."


def restaurant_on_active_poll() -> str:
    return (
        "❌ Dieses Restaurant ist gerade Teil der laufenden Umfrage und kann nicht entfernt werden."
    )


# --- /start-poll --------------------------------------------------------
def poll_bad_date() -> str:
    return "❌ Datum nicht verstanden. Erlaubt sind z. B. `12.09.2026`, `12.09.` oder `2026-09-12`."


def poll_date_in_past() -> str:
    return "❌ Dieses Datum liegt in der Vergangenheit."


def poll_not_enough_restaurants(minimum: int) -> str:
    return (
        f"❌ Es müssen mindestens {minimum} Restaurants auf der Liste stehen, "
        "um eine Umfrage zu starten."
    )


def poll_previous_discarded() -> str:
    return "♻️ Die vorherige Umfrage wurde verworfen."


def poll_question(date_label: str) -> str:
    return f"🍽️ Wo essen wir am {date_label}?"


def poll_companion_header(date_label: str) -> str:
    return f"**Zur Auswahl für {date_label}** (zum Anklicken):"


def poll_companion_line(index: int, text: str) -> str:
    return f"{index}. {text}"


def poll_started(date_label: str) -> str:
    return f"✅ Umfrage für **{date_label}** gestartet."


# --- poll close -------------------------------------------------------
def poll_winner(text: str, date_label: str) -> str:
    return f"🏆 Gewinner: **{text}** — {date_label}"


def poll_no_votes(date_label: str) -> str:
    return (
        f"🤷 Keine Stimmen für die Umfrage am {date_label}. "
        "Niemand hat Hunger — starte sie neu, wenn's soweit ist."
    )


# --- generic ---------------------------------------------------------
def generic_error() -> str:
    return "⚠️ Da ist etwas schiefgelaufen. Bitte versuch es noch einmal."
