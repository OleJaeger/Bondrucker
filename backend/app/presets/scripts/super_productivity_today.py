"""Heute faellige, offene Aufgaben aus Super Productivity (WebDAV-Sync).

Liest dieselbe ``sync-data.json`` wie der WebDAV-Sync von Super Productivity
(https://super-productivity.com/), konfiguriert ueber ``SP_WEBDAV_URL``/
``SP_WEBDAV_USERNAME``/``SP_WEBDAV_PASSWORD`` (erforderlich) und
``SP_SYNC_PATH`` (optional, Default "super-productivity"). Format-Details
siehe ``super_productivity_tasks.sync_file`` im Projekt
``super-productivity/scripts/SuperProductivityTasksPy``.
"""

from __future__ import annotations

import base64
import gzip
import json
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx

from app.config import get_effective_settings
from app.exceptions import PresetScriptError

_TIMEOUT = 10.0
_TZ = ZoneInfo("Europe/Berlin")

# "pf_[C][E]<modelVersion>__<payload>" - C = gzip+base64 compressed,
# E = encrypted (not supported here).
_PREFIX_RE = re.compile(r"^pf_(C)?(E)?([\d.]+)__")


def generate() -> str:
    settings = get_effective_settings()
    if not (settings.sp_webdav_url and settings.sp_webdav_username and settings.sp_webdav_password):
        raise PresetScriptError(
            "Super Productivity ist nicht konfiguriert "
            "(SP_WEBDAV_URL/SP_WEBDAV_USERNAME/SP_WEBDAV_PASSWORD fehlen)."
        )

    sync_path = settings.sp_sync_path.strip("/")
    url = f"{settings.sp_webdav_url.rstrip('/')}/{sync_path}/sync-data.json"

    try:
        response = httpx.get(
            url,
            auth=(settings.sp_webdav_username, settings.sp_webdav_password),
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise PresetScriptError(f"Super-Productivity-Daten konnten nicht geladen werden: {exc}") from exc

    raw = response.text
    match = _PREFIX_RE.match(raw)
    if not match:
        raise PresetScriptError("Unbekanntes Format der Super-Productivity-Sync-Datei.")

    if match.group(2):
        raise PresetScriptError(
            "Die Super-Productivity-Sync-Datei ist verschluesselt und wird nicht unterstuetzt."
        )

    payload = raw[match.end():]
    try:
        if match.group(1):
            json_text = gzip.decompress(base64.b64decode(payload)).decode("utf-8")
        else:
            json_text = payload
        data = json.loads(json_text)
        task_state = data["state"]["task"]
        project_state = data["state"]["project"]
        tag_state = data["state"].get("tag", {})
    except (ValueError, KeyError) as exc:
        raise PresetScriptError(f"Super-Productivity-Daten konnten nicht gelesen werden: {exc}") from exc

    today = datetime.now(_TZ).strftime("%Y-%m-%d")
    projects = project_state.get("entities", {})
    tags = tag_state.get("entities", {})

    no_project = "Ohne Projekt"
    groups: dict[str, list[tuple[dict, str, str | None]]] = {}
    for task_id in task_state.get("ids", []):
        entity = task_state["entities"][task_id]
        if entity.get("isDone"):
            continue

        due_day = entity.get("dueDay")
        due_time = None
        if not due_day:
            due_with_time = entity.get("dueWithTime")
            if not due_with_time:
                continue
            local_dt = datetime.fromtimestamp(int(due_with_time) / 1000, tz=timezone.utc).astimezone(_TZ)
            due_day = local_dt.strftime("%Y-%m-%d")
            due_time = local_dt.strftime("%H:%M")

        if due_day > today:
            continue

        project_id = entity.get("projectId")
        project_title = projects.get(project_id, {}).get("title") if project_id else None
        groups.setdefault(project_title or no_project, []).append((entity, due_day, due_time))

    if not groups:
        return "Keine Aufgaben fuer heute eingeplant."

    lines: list[str] = []
    for project_title in sorted(groups, key=lambda name: (name == no_project, name.lower())):
        if lines:
            lines.append("")
        lines.append(f"## {project_title}")
        for entity, due_day, due_time in sorted(groups[project_title], key=lambda item: (item[1], item[2] or "")):
            line = f"- [ ] {entity['title']}"
            if due_time:
                line += f" {due_time}"
            tag_titles = [tags[tid]["title"] for tid in (entity.get("tagIds") or []) if tid in tags]
            for tag_title in tag_titles:
                line += f" #{tag_title}"
            if due_day < today:
                line += f" (ueberfaellig seit {due_day})"
            lines.append(line)

    return "\n".join(lines)
