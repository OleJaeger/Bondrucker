"""``/api/presets`` endpoint tests.

Uses the stubbed queue worker (see ``conftest.py``), so created jobs stay in
``queued`` state.
"""

from __future__ import annotations

import httpx

from app.presets.scripts import positive_message, weather_forecast


def test_list_presets_returns_configured_presets(client, auth_headers):
    response = client.get("/api/presets", headers=auth_headers)
    assert response.status_code == 200

    presets = {p["key"]: p for p in response.json()}
    assert set(presets) == {
        "wlan-qrcode",
        "positive-nachricht",
        "heutige-aufgaben",
        "einkaufsliste",
        "wettervorhersage",
        "tenets-of-it",
        "jagdtag-heute",
        "fridge-art",
        "ausmalbild",
    }

    wlan = presets["wlan-qrcode"]
    assert wlan["name"] == "WLAN-Zugang"
    assert wlan["icon"] == "fa-wifi"
    assert wlan["template"] == "message"
    assert wlan["category"] == "Information"
    assert "description" in wlan


def test_list_presets_requires_api_key(client):
    response = client.get("/api/presets")
    assert response.status_code == 401


def test_print_wlan_qrcode_preset_returns_201_with_qr_code(client, auth_headers):
    response = client.post("/api/presets/wlan-qrcode/print", headers=auth_headers)
    assert response.status_code == 201

    body = response.json()
    assert body["status"] == "queued"
    assert body["template"] == "message"
    assert body["qr_code"] is not None
    assert body["qr_code"].startswith("WIFI:")
    assert body["image_base64"] is None


def test_print_positive_nachricht_preset_returns_201_with_script_content(client, auth_headers):
    response = client.post("/api/presets/positive-nachricht/print", headers=auth_headers)
    assert response.status_code == 201

    body = response.json()
    assert body["status"] == "queued"
    assert body["template"] == "message"
    assert body["markdown"] in positive_message._MESSAGES


def test_print_ausmalbild_preset_returns_201_with_image(client, auth_headers):
    response = client.post("/api/presets/ausmalbild/print", headers=auth_headers)
    assert response.status_code == 201

    body = response.json()
    assert body["status"] == "queued"
    assert body["template"] == "gemaelde"
    assert body["image_base64"] is not None
    assert body["image_base64"].startswith("data:image/png;base64,")


def test_print_unknown_preset_returns_404(client, auth_headers):
    response = client.post("/api/presets/does-not-exist/print", headers=auth_headers)
    assert response.status_code == 404


def test_print_preset_requires_api_key(client):
    response = client.post("/api/presets/wlan-qrcode/print")
    assert response.status_code == 401


def test_print_preset_with_failing_script_returns_502_and_creates_no_job(client, auth_headers, monkeypatch):
    def _broken_get(*_args, **_kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(weather_forecast.httpx, "get", _broken_get)

    response = client.post("/api/presets/wettervorhersage/print", headers=auth_headers)
    assert response.status_code == 502

    jobs = client.get("/api/jobs", headers=auth_headers).json()
    assert jobs == []
