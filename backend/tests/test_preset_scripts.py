"""Preset content script tests (``app/presets/scripts/*`` and ``script_runner``)."""

from __future__ import annotations

import base64
import gzip
import json
import sys
import types
from datetime import date, datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

import httpx
import psycopg
import pytest
from PIL import Image

from app.config import get_settings
from app.exceptions import PresetScriptError
from app.presets.script_runner import run_content_script, run_image_script
from app.presets.scripts import (
    jagdtag_heute,
    mealie_shopping_list,
    positive_message,
    random_animal,
    super_productivity_today,
    tenets_of_it,
    weather_forecast,
)


class _FakeResponse:
    def __init__(self, json_data=None, text=None):
        self._json_data = json_data
        self.text = text if text is not None else ""

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._json_data


# --- run_content_script -----------------------------------------------------


def test_run_content_script_unknown_module_raises():
    with pytest.raises(PresetScriptError):
        run_content_script("does_not_exist_xyz")


def test_run_content_script_without_generate_raises(monkeypatch):
    module = types.ModuleType("app.presets.scripts.no_generate")
    monkeypatch.setitem(sys.modules, "app.presets.scripts.no_generate", module)

    with pytest.raises(PresetScriptError):
        run_content_script("no_generate")


def test_run_content_script_wraps_exceptions(monkeypatch):
    module = types.ModuleType("app.presets.scripts.broken")
    module.generate = lambda: (_ for _ in ()).throw(ValueError("boom"))
    monkeypatch.setitem(sys.modules, "app.presets.scripts.broken", module)

    with pytest.raises(PresetScriptError):
        run_content_script("broken")


def test_run_content_script_passes_through_preset_script_error(monkeypatch):
    module = types.ModuleType("app.presets.scripts.broken_preset_error")
    module.generate = lambda: (_ for _ in ()).throw(PresetScriptError("kaputt"))
    monkeypatch.setitem(sys.modules, "app.presets.scripts.broken_preset_error", module)

    with pytest.raises(PresetScriptError, match="kaputt"):
        run_content_script("broken_preset_error")


def test_run_content_script_rejects_non_string_result(monkeypatch):
    module = types.ModuleType("app.presets.scripts.not_a_string")
    module.generate = lambda: 123
    monkeypatch.setitem(sys.modules, "app.presets.scripts.not_a_string", module)

    with pytest.raises(PresetScriptError):
        run_content_script("not_a_string")


# --- run_image_script --------------------------------------------------------


def test_run_image_script_unknown_module_raises():
    with pytest.raises(PresetScriptError):
        run_image_script("does_not_exist_xyz")


def test_run_image_script_without_generate_image_raises(monkeypatch):
    module = types.ModuleType("app.presets.scripts.no_generate_image")
    monkeypatch.setitem(sys.modules, "app.presets.scripts.no_generate_image", module)

    with pytest.raises(PresetScriptError):
        run_image_script("no_generate_image")


def test_run_image_script_wraps_exceptions(monkeypatch):
    module = types.ModuleType("app.presets.scripts.broken_image")
    module.generate_image = lambda: (_ for _ in ()).throw(ValueError("boom"))
    monkeypatch.setitem(sys.modules, "app.presets.scripts.broken_image", module)

    with pytest.raises(PresetScriptError):
        run_image_script("broken_image")


def test_run_image_script_passes_through_preset_script_error(monkeypatch):
    module = types.ModuleType("app.presets.scripts.broken_image_preset_error")
    module.generate_image = lambda: (_ for _ in ()).throw(PresetScriptError("kaputt"))
    monkeypatch.setitem(sys.modules, "app.presets.scripts.broken_image_preset_error", module)

    with pytest.raises(PresetScriptError, match="kaputt"):
        run_image_script("broken_image_preset_error")


def test_run_image_script_rejects_non_bytes_result(monkeypatch):
    module = types.ModuleType("app.presets.scripts.not_bytes")
    module.generate_image = lambda: "not bytes"
    monkeypatch.setitem(sys.modules, "app.presets.scripts.not_bytes", module)

    with pytest.raises(PresetScriptError):
        run_image_script("not_bytes")


# --- custom/ fallback (app/presets/scripts/custom, see its README.md) -------


def test_run_content_script_falls_back_to_custom_dir(monkeypatch):
    module = types.ModuleType("app.presets.scripts.custom.my_custom_script")
    module.generate = lambda: "Hallo aus custom"
    monkeypatch.setitem(sys.modules, "app.presets.scripts.custom.my_custom_script", module)

    assert run_content_script("my_custom_script") == "Hallo aus custom"


def test_run_image_script_falls_back_to_custom_dir(monkeypatch):
    module = types.ModuleType("app.presets.scripts.custom.my_custom_image_script")
    module.generate_image = lambda: b"PNGDATA"
    monkeypatch.setitem(sys.modules, "app.presets.scripts.custom.my_custom_image_script", module)

    assert run_image_script("my_custom_image_script") == b"PNGDATA"


def test_run_content_script_prefers_main_dir_over_custom(monkeypatch):
    main_module = types.ModuleType("app.presets.scripts.shadowed")
    main_module.generate = lambda: "aus dem Hauptverzeichnis"
    monkeypatch.setitem(sys.modules, "app.presets.scripts.shadowed", main_module)

    custom_module = types.ModuleType("app.presets.scripts.custom.shadowed")
    custom_module.generate = lambda: "aus custom"
    monkeypatch.setitem(sys.modules, "app.presets.scripts.custom.shadowed", custom_module)

    assert run_content_script("shadowed") == "aus dem Hauptverzeichnis"


# --- random_animal -------------------------------------------------------------


def test_random_animal_generate_image_returns_a_valid_png(settings_env):
    data = random_animal.generate_image()

    assert isinstance(data, bytes)
    image = Image.open(BytesIO(data))
    assert image.format == "PNG"
    # No leftover grid: the cropped/cleaned motif is plain black-on-white.
    colors = {color for _count, color in image.convert("RGB").getcolors(maxcolors=1_000_000)}
    assert (255, 0, 0) not in colors


# --- positive_message --------------------------------------------------------


def test_positive_message_returns_one_of_the_known_messages():
    assert positive_message.generate() in positive_message._MESSAGES


# --- tenets_of_it -------------------------------------------------------------


def test_tenets_of_it_returns_one_of_the_known_messages():
    assert tenets_of_it.generate() in tenets_of_it._MESSAGES


# --- weather_forecast ---------------------------------------------------------


def _ha_sensor_responses(url, headers=None, timeout=None):
    """Fake httpx.get that returns HA state responses for all required entities."""
    if "wetterstation_outdoor_temperature" in url:
        return _FakeResponse(json_data={"state": "18.5", "attributes": {"unit_of_measurement": "°C"}})
    if "wetterstation_feels_like_temperature" in url:
        return _FakeResponse(json_data={"state": "16.2", "attributes": {}})
    if "wetterstation_wind_direction" in url:
        return _FakeResponse(json_data={"state": "225", "attributes": {"unit_of_measurement": "°"}})
    if "wetterstation_wind_speed" in url:
        return _FakeResponse(json_data={"state": "15", "attributes": {"unit_of_measurement": "km/h"}})
    if "weather.openweathermap" in url:
        return _FakeResponse(json_data={
            "state": "sunny",
            "attributes": {
                "forecast": [{"temperature": 22, "templow": 12, "precipitation_probability": 10}]
            },
        })
    raise ValueError(f"Unerwartete URL: {url}")


def _set_ha_env(monkeypatch) -> None:
    monkeypatch.setenv("HOMEASSISTANT_URL", "http://ha.example.com:8123")
    monkeypatch.setenv("HOMEASSISTANT_TOKEN", "test-token")
    get_settings.cache_clear()


def test_weather_forecast_without_ha_config_raises(settings_env):
    with pytest.raises(PresetScriptError):
        weather_forecast.generate()


def test_weather_forecast_formats_ha_response(settings_env, monkeypatch):
    _set_ha_env(monkeypatch)
    monkeypatch.setattr(weather_forecast.httpx, "get", _ha_sensor_responses)

    content = weather_forecast.generate()
    assert "Berlin" in content
    assert "Sonnig" in content
    assert "18" in content
    assert "16" in content
    assert "SW" in content
    assert "15" in content
    assert "22" in content
    assert "12" in content
    assert "10" in content


def test_weather_forecast_http_error_raises_preset_script_error(settings_env, monkeypatch):
    _set_ha_env(monkeypatch)

    def _fake_get(*_args, **_kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(weather_forecast.httpx, "get", _fake_get)

    with pytest.raises(PresetScriptError):
        weather_forecast.generate()


def test_weather_forecast_without_forecast_data(settings_env, monkeypatch):
    _set_ha_env(monkeypatch)

    def _fake_get(url, headers=None, timeout=None):
        if "weather.openweathermap" in url:
            return _FakeResponse(json_data={"state": "cloudy", "attributes": {}})
        return _ha_sensor_responses(url, headers=headers, timeout=timeout)

    monkeypatch.setattr(weather_forecast.httpx, "get", _fake_get)

    content = weather_forecast.generate()
    assert "Bewoelkt" in content
    assert "Hoechsttemperatur" not in content


# --- mealie_shopping_list -------------------------------------------------------


def test_mealie_shopping_list_without_config_raises(settings_env):
    with pytest.raises(PresetScriptError):
        mealie_shopping_list.generate()


def test_mealie_shopping_list_formats_open_items(settings_env, monkeypatch):
    monkeypatch.setenv("MEALIE_BASE_URL", "https://mealie.example.com")
    monkeypatch.setenv("MEALIE_API_TOKEN", "token123")
    monkeypatch.setenv("MEALIE_SHOPPING_LIST_ID", "list-1")
    get_settings.cache_clear()

    def _fake_get(url, headers=None, params=None, timeout=None):
        assert url.endswith("/api/households/shopping/items")
        return _FakeResponse(
            json_data={
                "items": [
                    {"food": {"name": "Milch"}, "quantity": 2, "checked": False},
                    {"food": {"name": "Brot"}, "quantity": 0, "checked": False},
                    {"food": {"name": "Butter"}, "quantity": 1, "checked": True},
                ]
            }
        )

    monkeypatch.setattr(mealie_shopping_list.httpx, "get", _fake_get)

    assert mealie_shopping_list.generate() == "## Ohne Label\n- [ ] Milch (2)\n- [ ] Brot"


def test_mealie_shopping_list_groups_items_by_label(settings_env, monkeypatch):
    monkeypatch.setenv("MEALIE_BASE_URL", "https://mealie.example.com")
    monkeypatch.setenv("MEALIE_API_TOKEN", "token123")
    monkeypatch.setenv("MEALIE_SHOPPING_LIST_ID", "list-1")
    get_settings.cache_clear()

    def _fake_get(url, headers=None, params=None, timeout=None):
        assert url.endswith("/api/households/shopping/items")
        return _FakeResponse(
            json_data={
                "items": [
                    {
                        "food": {"name": "Milch"},
                        "quantity": 2,
                        "checked": False,
                        "label": {"name": "Kuehlregal"},
                    },
                    {
                        "food": {"name": "Erbsen"},
                        "quantity": 1,
                        "checked": False,
                        "label": {"name": "Konserven und Fertiggerichte"},
                    },
                    {
                        "food": {"name": "Butter"},
                        "quantity": 1,
                        "checked": False,
                        "label": {"name": "Kuehlregal"},
                    },
                    {"food": {"name": "Kerzen"}, "quantity": 0, "checked": False},
                ]
            }
        )

    monkeypatch.setattr(mealie_shopping_list.httpx, "get", _fake_get)

    assert mealie_shopping_list.generate() == (
        "## Konserven und Fertiggerichte\n"
        "- [ ] Erbsen (1)\n"
        "\n"
        "## Kuehlregal\n"
        "- [ ] Milch (2)\n"
        "- [ ] Butter (1)\n"
        "\n"
        "## Ohne Label\n"
        "- [ ] Kerzen"
    )


def test_mealie_shopping_list_empty_list(settings_env, monkeypatch):
    monkeypatch.setenv("MEALIE_BASE_URL", "https://mealie.example.com")
    monkeypatch.setenv("MEALIE_API_TOKEN", "token123")
    monkeypatch.setenv("MEALIE_SHOPPING_LIST_ID", "list-1")
    get_settings.cache_clear()

    monkeypatch.setattr(mealie_shopping_list.httpx, "get", lambda *a, **kw: _FakeResponse(json_data={"items": []}))

    assert mealie_shopping_list.generate() == "Die Einkaufsliste ist leer."


def test_mealie_shopping_list_http_error(settings_env, monkeypatch):
    monkeypatch.setenv("MEALIE_BASE_URL", "https://mealie.example.com")
    monkeypatch.setenv("MEALIE_API_TOKEN", "token123")
    monkeypatch.setenv("MEALIE_SHOPPING_LIST_ID", "list-1")
    get_settings.cache_clear()

    def _fake_get(*_args, **_kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(mealie_shopping_list.httpx, "get", _fake_get)

    with pytest.raises(PresetScriptError):
        mealie_shopping_list.generate()


# --- super_productivity_today ---------------------------------------------------


def _sync_payload() -> dict:
    today = date.today().strftime("%Y-%m-%d")
    return {
        "state": {
            "task": {
                "ids": ["t1", "t2"],
                "entities": {
                    "t1": {
                        "title": "Aufgabe 1",
                        "isDone": False,
                        "dueDay": today,
                        "projectId": "p1",
                        "tagIds": ["g1"],
                    },
                    "t2": {"title": "Aufgabe 2", "isDone": True, "dueDay": today, "projectId": "p1"},
                },
            },
            "project": {"entities": {"p1": {"title": "Projekt A"}}},
            "tag": {"entities": {"g1": {"title": "Wichtig"}}},
        }
    }


def _set_sp_env(monkeypatch) -> None:
    monkeypatch.setenv("SP_WEBDAV_URL", "https://webdav.example.com")
    monkeypatch.setenv("SP_WEBDAV_USERNAME", "user")
    monkeypatch.setenv("SP_WEBDAV_PASSWORD", "pass")
    get_settings.cache_clear()


def test_super_productivity_today_without_config_raises(settings_env):
    with pytest.raises(PresetScriptError):
        super_productivity_today.generate()


def test_super_productivity_today_formats_uncompressed_sync_data(settings_env, monkeypatch):
    _set_sp_env(monkeypatch)

    text = "pf_1.0__" + json.dumps(_sync_payload())
    monkeypatch.setattr(super_productivity_today.httpx, "get", lambda *a, **kw: _FakeResponse(text=text))

    assert super_productivity_today.generate() == "## Projekt A\n- [ ] Aufgabe 1 #Wichtig"


def test_super_productivity_today_formats_compressed_sync_data(settings_env, monkeypatch):
    _set_sp_env(monkeypatch)

    compressed = base64.b64encode(gzip.compress(json.dumps(_sync_payload()).encode("utf-8"))).decode("ascii")
    text = "pf_C1.0__" + compressed
    monkeypatch.setattr(super_productivity_today.httpx, "get", lambda *a, **kw: _FakeResponse(text=text))

    assert super_productivity_today.generate() == "## Projekt A\n- [ ] Aufgabe 1 #Wichtig"


def test_super_productivity_today_no_tasks_due_today(settings_env, monkeypatch):
    _set_sp_env(monkeypatch)

    payload = _sync_payload()
    payload["state"]["task"]["entities"]["t1"]["isDone"] = True
    text = "pf_1.0__" + json.dumps(payload)
    monkeypatch.setattr(super_productivity_today.httpx, "get", lambda *a, **kw: _FakeResponse(text=text))

    assert super_productivity_today.generate() == "Keine Aufgaben fuer heute eingeplant."


def test_super_productivity_today_groups_by_project_and_marks_overdue(settings_env, monkeypatch):
    _set_sp_env(monkeypatch)

    today = date.today().strftime("%Y-%m-%d")
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    payload = {
        "state": {
            "task": {
                "ids": ["t1", "t2", "t3", "t4"],
                "entities": {
                    "t1": {
                        "title": "Aufgabe 1",
                        "isDone": False,
                        "dueDay": today,
                        "projectId": "p1",
                        "tagIds": ["g1", "g2"],
                    },
                    "t2": {"title": "Aufgabe 2", "isDone": False, "dueDay": yesterday, "projectId": "p1"},
                    "t3": {"title": "Aufgabe 3", "isDone": False, "dueDay": today, "projectId": "p2"},
                    "t4": {"title": "Aufgabe 4", "isDone": False, "dueDay": today},
                },
            },
            "project": {"entities": {"p1": {"title": "Projekt A"}, "p2": {"title": "Projekt B"}}},
            "tag": {"entities": {"g1": {"title": "Wichtig"}, "g2": {"title": "Eilig"}}},
        }
    }
    text = "pf_1.0__" + json.dumps(payload)
    monkeypatch.setattr(super_productivity_today.httpx, "get", lambda *a, **kw: _FakeResponse(text=text))

    assert super_productivity_today.generate() == (
        "## Projekt A\n"
        f"- [ ] Aufgabe 2 (ueberfaellig seit {yesterday})\n"
        "- [ ] Aufgabe 1 #Wichtig #Eilig\n"
        "\n"
        "## Projekt B\n"
        "- [ ] Aufgabe 3\n"
        "\n"
        "## Ohne Projekt\n"
        "- [ ] Aufgabe 4"
    )


def test_super_productivity_today_includes_due_with_time_tasks(settings_env, monkeypatch):
    _set_sp_env(monkeypatch)

    berlin_now = datetime.now(ZoneInfo("Europe/Berlin"))
    today_morning = berlin_now.replace(hour=8, minute=0, second=0, microsecond=0)
    today_afternoon = berlin_now.replace(hour=15, minute=30, second=0, microsecond=0)
    payload = {
        "state": {
            "task": {
                "ids": ["t1", "t2"],
                "entities": {
                    "t1": {
                        "title": "Termin morgens",
                        "isDone": False,
                        "dueWithTime": int(today_morning.timestamp() * 1000),
                        "projectId": "p1",
                    },
                    "t2": {
                        "title": "Termin nachmittags",
                        "isDone": False,
                        "dueWithTime": int(today_afternoon.timestamp() * 1000),
                        "projectId": "p1",
                        "tagIds": ["g1"],
                    },
                },
            },
            "project": {"entities": {"p1": {"title": "Projekt A"}}},
            "tag": {"entities": {"g1": {"title": "Wichtig"}}},
        }
    }
    text = "pf_1.0__" + json.dumps(payload)
    monkeypatch.setattr(super_productivity_today.httpx, "get", lambda *a, **kw: _FakeResponse(text=text))

    assert super_productivity_today.generate() == (
        "## Projekt A\n"
        "- [ ] Termin morgens 08:00\n"
        "- [ ] Termin nachmittags 15:30 #Wichtig"
    )


def test_super_productivity_today_encrypted_sync_data_raises(settings_env, monkeypatch):
    _set_sp_env(monkeypatch)

    text = "pf_E1.0__irrelevant"
    monkeypatch.setattr(super_productivity_today.httpx, "get", lambda *a, **kw: _FakeResponse(text=text))

    with pytest.raises(PresetScriptError, match="verschluesselt"):
        super_productivity_today.generate()


def test_super_productivity_today_unknown_format_raises(settings_env, monkeypatch):
    _set_sp_env(monkeypatch)

    monkeypatch.setattr(super_productivity_today.httpx, "get", lambda *a, **kw: _FakeResponse(text="garbage"))

    with pytest.raises(PresetScriptError):
        super_productivity_today.generate()


def test_super_productivity_today_http_error_raises(settings_env, monkeypatch):
    _set_sp_env(monkeypatch)

    def _fake_get(*_args, **_kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(super_productivity_today.httpx, "get", _fake_get)

    with pytest.raises(PresetScriptError):
        super_productivity_today.generate()


# --- jagdtag_heute --------------------------------------------------------------


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        return False

    def execute(self, _query):
        return None

    def fetchall(self):
        return self._rows


class _FakeConnection:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        return False

    def cursor(self):
        return _FakeCursor(self._rows)


def _set_jagd_env(monkeypatch) -> None:
    monkeypatch.setenv("JAGD_DB_HOST", "jagd-db.test")
    monkeypatch.setenv("JAGD_DB_NAME", "jagddb")
    monkeypatch.setenv("JAGD_DB_USER", "user")
    monkeypatch.setenv("JAGD_DB_PASSWORD", "pass")
    get_settings.cache_clear()


def _fake_jagd_weather_get(url, headers=None, timeout=None):
    """Fake httpx.get fuer jagdtag_heute: gibt HA-Zustandsantworten zurueck."""
    if "wetterstation_outdoor_temperature" in url:
        return _FakeResponse(json_data={"state": "18.5", "attributes": {"unit_of_measurement": "°C"}})
    if "wetterstation_wind_direction" in url:
        return _FakeResponse(json_data={"state": "180", "attributes": {"unit_of_measurement": "°"}})
    if "wetterstation_wind_speed" in url:
        return _FakeResponse(json_data={"state": "12", "attributes": {"unit_of_measurement": "km/h"}})
    if "weather.openweathermap" in url:
        return _FakeResponse(json_data={
            "state": "sunny",
            "attributes": {
                "forecast": [{"temperature": 20, "templow": 10, "precipitation_probability": 30}]
            },
        })
    if "sun.sun" in url:
        return _FakeResponse(json_data={
            "state": "above_horizon",
            "attributes": {"next_setting": "2026-06-15T21:48:00+02:00"},
        })
    raise ValueError(f"Unerwartete URL: {url}")


def test_jagdtag_heute_without_db_config_raises(settings_env):
    with pytest.raises(PresetScriptError):
        jagdtag_heute.generate()


def test_jagdtag_heute_formats_output(settings_env, monkeypatch):
    _set_jagd_env(monkeypatch)
    _set_ha_env(monkeypatch)

    today = date.today()
    in_start = (today - timedelta(days=1)).strftime("%d.%m")
    in_end = (today + timedelta(days=1)).strftime("%d.%m")
    out_start = (today + timedelta(days=100)).strftime("%d.%m")
    out_end = (today + timedelta(days=110)).strftime("%d.%m")

    rows = [
        (f"{in_start} - {in_end}.", "Rehbock,Hase", None),
        ("ganzjaehrig", "Schwarzwild", None),
        ("ganzjaehrig geschont", "Wolf", "Auerhahn"),
        (f"{out_start} - {out_end}.", "Damwild", None),
        (f"{in_start} - {in_end}.", None, "Fasan,Stockente"),
        (f"{out_start} - {out_end}.", None, "Waldschnepfe"),
    ]

    monkeypatch.setattr(jagdtag_heute.psycopg, "connect", lambda **_kw: _FakeConnection(rows))
    monkeypatch.setattr(jagdtag_heute.httpx, "get", _fake_jagd_weather_get)

    content = jagdtag_heute.generate()

    assert "## Haarwild" in content
    assert "- Rehbock" in content
    assert "- Hase" in content
    assert "- Schwarzwild" in content
    assert "Damwild" not in content
    assert "Wolf" not in content
    assert "## Federwild" in content
    assert "- Fasan" in content
    assert "- Stockente" in content
    assert "Auerhahn" not in content
    assert "Waldschnepfe" not in content
    assert "Sonnig" in content
    assert "S (180 Grad)" in content
    assert "Sonnenuntergang: 21:48 Uhr" in content


def test_jagdtag_heute_no_wild_today(settings_env, monkeypatch):
    _set_jagd_env(monkeypatch)
    _set_ha_env(monkeypatch)

    monkeypatch.setattr(jagdtag_heute.psycopg, "connect", lambda **_kw: _FakeConnection([]))
    monkeypatch.setattr(jagdtag_heute.httpx, "get", _fake_jagd_weather_get)

    content = jagdtag_heute.generate()
    assert content.count("Heute nichts jagdbar.") == 2


def test_jagdtag_heute_db_error_raises(settings_env, monkeypatch):
    _set_jagd_env(monkeypatch)

    def _fake_connect(**_kwargs):
        raise psycopg.OperationalError("boom")

    monkeypatch.setattr(jagdtag_heute.psycopg, "connect", _fake_connect)

    with pytest.raises(PresetScriptError):
        jagdtag_heute.generate()


def test_jagdtag_heute_weather_error_raises(settings_env, monkeypatch):
    _set_jagd_env(monkeypatch)
    _set_ha_env(monkeypatch)

    monkeypatch.setattr(jagdtag_heute.psycopg, "connect", lambda **_kw: _FakeConnection([]))

    def _fake_get(*_args, **_kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(jagdtag_heute.httpx, "get", _fake_get)

    with pytest.raises(PresetScriptError):
        jagdtag_heute.generate()


# --- jagdtag_heute._is_jagdzeit_relevant -----------------------------------------


def test_is_jagdzeit_relevant_simple():
    assert jagdtag_heute._is_jagdzeit_relevant("01.10 - 31.12.", (11, 15)) is True
    assert jagdtag_heute._is_jagdzeit_relevant("01.10 - 31.12.", (1, 15)) is False


def test_is_jagdzeit_relevant_wraps_year_boundary():
    assert jagdtag_heute._is_jagdzeit_relevant("01.05 - 31.01.", (6, 15)) is True
    assert jagdtag_heute._is_jagdzeit_relevant("01.05 - 31.01.", (1, 10)) is True
    assert jagdtag_heute._is_jagdzeit_relevant("01.05 - 31.01.", (3, 1)) is False


def test_is_jagdzeit_relevant_ganzjaehrig():
    assert jagdtag_heute._is_jagdzeit_relevant("ganzjährig", (1, 1)) is True
    assert jagdtag_heute._is_jagdzeit_relevant("ganzjährig geschont", (1, 1)) is False


def test_is_jagdzeit_relevant_empty_or_unparseable():
    assert jagdtag_heute._is_jagdzeit_relevant(None, (1, 1)) is False
    assert jagdtag_heute._is_jagdzeit_relevant("", (1, 1)) is False


# --- jagdtag_heute._split_species ------------------------------------------------


def test_split_species():
    assert jagdtag_heute._split_species("Fuchs,Reh ,Hase") == ["Fuchs", "Reh", "Hase"]
    assert jagdtag_heute._split_species(None) == []
    assert jagdtag_heute._split_species("") == []
