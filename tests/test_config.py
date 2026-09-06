from __future__ import annotations

import pytest

from restaurant_bot.config import ConfigError, load_config


def _env(monkeypatch, **overrides: str | None) -> None:
    base = {
        "DISCORD_TOKEN": "abc",
        "TZ": "Europe/Berlin",
        "SQLITE_PATH": "./data/x.db",
        "EMA_LAMBDA": "0.3",
        "WEIGHT_FLOOR": "0.05",
    }
    base.update(overrides)
    for key, value in base.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


def test_valid(monkeypatch) -> None:
    _env(monkeypatch)
    cfg = load_config(load_dotenv_file=False)
    assert cfg.discord_token == "abc"
    assert cfg.tz_name == "Europe/Berlin"
    assert cfg.ema_lambda == 0.3
    assert cfg.weight_floor == 0.05


def test_missing_token(monkeypatch) -> None:
    _env(monkeypatch, DISCORD_TOKEN=None)
    with pytest.raises(ConfigError):
        load_config(load_dotenv_file=False)


def test_bad_tz(monkeypatch) -> None:
    _env(monkeypatch, TZ="Mars/Olympus")
    with pytest.raises(ConfigError):
        load_config(load_dotenv_file=False)


@pytest.mark.parametrize("value", ["0", "-0.1", "1.5", "abc"])
def test_bad_lambda(monkeypatch, value: str) -> None:
    _env(monkeypatch, EMA_LAMBDA=value)
    with pytest.raises(ConfigError):
        load_config(load_dotenv_file=False)


def test_bad_floor(monkeypatch) -> None:
    _env(monkeypatch, WEIGHT_FLOOR="0")
    with pytest.raises(ConfigError):
        load_config(load_dotenv_file=False)


def test_defaults_applied(monkeypatch) -> None:
    _env(monkeypatch, TZ=None, SQLITE_PATH=None, EMA_LAMBDA=None, WEIGHT_FLOOR=None)
    cfg = load_config(load_dotenv_file=False)
    assert cfg.tz_name == "Europe/Berlin"
    assert cfg.sqlite_path == "./data/restaurants.db"
    assert cfg.ema_lambda == 0.3
    assert cfg.weight_floor == 0.05
