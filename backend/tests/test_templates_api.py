"""``GET /api/templates`` - lets the frontend populate the template selector."""

from __future__ import annotations


def test_list_templates_returns_configured_templates(client, auth_headers):
    response = client.get("/api/templates", headers=auth_headers)
    assert response.status_code == 200

    templates = {t["key"]: t for t in response.json()}
    assert templates["freitext"] == {
        "key": "freitext",
        "name": "Freitext",
        "type": "freitext",
        "icon": None,
        "allow_markdown": True,
        "allow_attachment": True,
        "default_markdown": None,
    }
    assert templates["todo"] == {
        "key": "todo",
        "name": "Aufgabenliste",
        "type": "todo",
        "icon": "fa-list-check",
        "allow_markdown": True,
        "allow_attachment": True,
        "default_markdown": None,
    }
    gemaelde = templates["gemaelde"]
    assert gemaelde["name"] == "Gemälde"
    assert gemaelde["icon"] == "fa-paintbrush"
    assert gemaelde["allow_markdown"] is False
    assert gemaelde["allow_attachment"] is False
    assert gemaelde["default_markdown"]


def test_list_templates_requires_api_key(client):
    response = client.get("/api/templates")
    assert response.status_code == 401
