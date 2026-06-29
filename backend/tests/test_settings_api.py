"""``GET``/``PUT /api/settings`` - web-configurable preset integration settings."""

from __future__ import annotations

from app.config import get_settings


def _field(body: list[dict], key: str) -> dict:
    return next(item for item in body if item["key"] == key)


def test_list_settings_returns_all_web_configurable_fields(client, auth_headers):
    response = client.get("/api/settings", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    keys = {item["key"] for item in body}
    assert "mealie_base_url" in keys
    assert "jagd_db_port" in keys
    # .env-only fields are not part of this API.
    assert "api_key" not in keys
    assert "printer_host" not in keys

    mealie_url = _field(body, "mealie_base_url")
    assert mealie_url["locked"] is False
    assert mealie_url["value"] is None
    assert mealie_url["is_set"] is False
    assert mealie_url["used_by_presets"] == ["Einkaufsliste"]


def test_list_settings_masks_secret_values(client, auth_headers):
    client.put("/api/settings", headers=auth_headers, json={"mealie_api_token": "super-secret"})

    body = client.get("/api/settings", headers=auth_headers).json()
    token = _field(body, "mealie_api_token")
    assert token["secret"] is True
    assert token["value"] is None
    assert token["is_set"] is True


def test_list_settings_marks_env_locked_fields(client, auth_headers, monkeypatch):
    monkeypatch.setenv("HOMEASSISTANT_URL", "http://ha.example.com")
    get_settings.cache_clear()

    body = client.get("/api/settings", headers=auth_headers).json()
    ha_url = _field(body, "homeassistant_url")
    assert ha_url["locked"] is True
    assert ha_url["value"] == "http://ha.example.com"


def test_put_settings_sets_and_clears_an_override(client, auth_headers):
    response = client.put("/api/settings", headers=auth_headers, json={"mealie_shopping_list_id": "list-1"})
    assert response.status_code == 200
    field = _field(response.json(), "mealie_shopping_list_id")
    assert field["value"] == "list-1"
    assert field["is_set"] is True

    response = client.put("/api/settings", headers=auth_headers, json={"mealie_shopping_list_id": None})
    field = _field(response.json(), "mealie_shopping_list_id")
    assert field["value"] is None
    assert field["is_set"] is False


def test_put_settings_with_non_empty_default_overridden_then_cleared(client, auth_headers):
    response = client.put("/api/settings", headers=auth_headers, json={"weather_location_name": "Hamburg"})
    assert _field(response.json(), "weather_location_name")["value"] == "Hamburg"

    response = client.put("/api/settings", headers=auth_headers, json={"weather_location_name": None})
    assert _field(response.json(), "weather_location_name")["value"] == "Berlin"


def test_put_settings_coerces_int_fields(client, auth_headers):
    response = client.put("/api/settings", headers=auth_headers, json={"jagd_db_port": "5432"})
    assert response.status_code == 200
    assert _field(response.json(), "jagd_db_port")["value"] == 5432


def test_put_settings_rejects_invalid_int(client, auth_headers):
    response = client.put("/api/settings", headers=auth_headers, json={"jagd_db_port": "not-a-number"})
    assert response.status_code == 400


def test_put_settings_rejects_unknown_field(client, auth_headers):
    response = client.put("/api/settings", headers=auth_headers, json={"printer_host": "10.0.0.5"})
    assert response.status_code == 400


def test_put_settings_rejects_env_locked_field(client, auth_headers, monkeypatch):
    monkeypatch.setenv("MEALIE_BASE_URL", "https://from-env.example.com")
    get_settings.cache_clear()

    response = client.put("/api/settings", headers=auth_headers, json={"mealie_base_url": "https://other.example.com"})
    assert response.status_code == 400


def test_settings_requires_api_key(client):
    response = client.get("/api/settings")
    assert response.status_code == 401
