"""Wichtige Nachrichten aus dem News-Aggregator (https://news.ole-lab.de).

Ruft ``GET /api/v1/news`` ab, das bereits absteigend nach Score priorisiert
ist (siehe News-Projekt ``app/api/v1/news.py::list_news``) - die ersten
``_LIMIT`` Eintraege sind also die "wichtigen" Nachrichten.

Die API ist hinter Authentik (OIDC) geschuetzt und verlangt ein Bearer-JWT.
Dieses Skript authentifiziert sich per OAuth2-Client-Credentials-Flow gegen
den Authentik-Token-Endpoint (``NEWS_AUTHENTIK_TOKEN_URL``). Authentik
authentifiziert diesen Flow **nicht** ueber ein klassisches
client_id/client_secret-Paar, sondern ueber Benutzername + App-Passwort
(Token) eines Service-Accounts (Authentik: Directory -> Tokens and App
passwords bzw. "Create Service account") - siehe
https://docs.goauthentik.io/add-secure-apps/providers/oauth2/machine_to_machine/.
``NEWS_CLIENT_ID`` muss dabei die Client-ID des OAuth2-Providers sein, den
die News-App selbst fuer ihren eigenen Login verwendet (deren
``AUTHENTIK_CLIENT_ID``) - das News-Backend prueft beim Validieren des
Access-Tokens ``audience == eigene client_id`` (News-Projekt
``app/auth/authentik.py::_verify_jwt``); ein separat angelegter Provider mit
eigener Client-ID wuerde mit "Invalid audience" abgelehnt.

Das Access-Token wird bis kurz vor Ablauf im Prozess zwischengespeichert, um
nicht bei jedem Druck neu zu authentifizieren.

Konfiguration: NEWS_BASE_URL, NEWS_AUTHENTIK_TOKEN_URL, NEWS_CLIENT_ID,
NEWS_AUTHENTIK_USERNAME, NEWS_AUTHENTIK_PASSWORD (siehe .env.example).
"""

from __future__ import annotations

import time

import httpx

from app.config import get_effective_settings
from app.exceptions import PresetScriptError

_TIMEOUT = 10.0
_LIMIT = 10
# Sicherheitsabstand, um das Token nicht erst im Moment seines Ablaufs
# (Zeitversatz zwischen Cache-Check und tatsaechlichem API-Aufruf) zu nutzen.
_TOKEN_EXPIRY_MARGIN_SECONDS = 30

_cached_token: str | None = None
_cached_token_expires_at: float = 0.0


def _get_access_token(token_url: str, client_id: str, username: str, password: str) -> str:
    global _cached_token, _cached_token_expires_at

    if _cached_token is not None and time.monotonic() < _cached_token_expires_at:
        return _cached_token

    try:
        response = httpx.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "username": username,
                "password": password,
                "scope": "profile",
            },
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise PresetScriptError(f"Authentik-Token konnte nicht abgerufen werden: {exc}") from exc

    token = data.get("access_token")
    if not token:
        raise PresetScriptError("Authentik-Antwort enthaelt kein access_token.")

    expires_in = data.get("expires_in") or 60
    _cached_token = token
    _cached_token_expires_at = time.monotonic() + max(expires_in - _TOKEN_EXPIRY_MARGIN_SECONDS, 0)
    return token


def _format_news(items: list[dict]) -> str:
    if not items:
        return "Aktuell liegen keine wichtigen Nachrichten vor."

    lines = ["## Wichtige Nachrichten"]
    for item in items:
        title = item.get("canonical_title") or "?"
        category = item.get("category")
        lines.append("")
        lines.append(f"### {title}" + (f" ({category})" if category else ""))
        summary = (item.get("canonical_summary") or "").strip()
        if summary:
            lines.append(summary)

    return "\n".join(lines)


def generate() -> str:
    settings = get_effective_settings()
    if not (
        settings.news_base_url
        and settings.news_authentik_token_url
        and settings.news_client_id
        and settings.news_authentik_username
        and settings.news_authentik_password
    ):
        raise PresetScriptError(
            "News-Aggregator ist nicht konfiguriert (NEWS_BASE_URL/"
            "NEWS_AUTHENTIK_TOKEN_URL/NEWS_CLIENT_ID/NEWS_AUTHENTIK_USERNAME/"
            "NEWS_AUTHENTIK_PASSWORD fehlen)."
        )

    token = _get_access_token(
        settings.news_authentik_token_url,
        settings.news_client_id,
        settings.news_authentik_username,
        settings.news_authentik_password,
    )

    base_url = settings.news_base_url.rstrip("/")
    try:
        response = httpx.get(
            f"{base_url}/api/v1/news",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": _LIMIT},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        items = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise PresetScriptError(f"Nachrichten konnten nicht geladen werden: {exc}") from exc

    return _format_news(items)
