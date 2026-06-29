<p align="center">
  <img src="icon.png" alt="Bondrucker Logo" width="96" height="96" />
</p>

<h1 align="center">Bondrucker</h1>

<p align="center">
    <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" />
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" />
    <img src="https://img.shields.io/badge/React-TypeScript-61DAFB?logo=react&logoColor=black" />
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" />
    <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white" />
    <img src="https://img.shields.io/badge/License-MIT-green.svg" />
</p>

Produktionsreife Web-Anwendung zur Ansteuerung eines netzwerkfähigen **V330M 80mm
ESC/POS-Thermodruckers**. Druckaufträge (Freitext, Aufgabenlisten, ... ) werden über eine
REST-API entgegengenommen, in einer persistenten FIFO-Queue verwaltet und mit
automatischen Wiederholungsversuchen an den Drucker gesendet.

## Wofür kann man es nutzen?

- **Eigene Druckaufträge** über die REST-API, das Web-Frontend, ein PowerShell-Modul
  oder eine Python-Bibliothek/CLI (siehe [`docs/scripts/`](docs/scripts/README.md)).
- **Automatisierte "Standarddruckobjekte"** (Presets): z. B. die heutigen Aufgaben aus
  Super Productivity, die Einkaufsliste aus Mealie oder ein Wetter-Briefing aus Home
  Assistant – per Zeitplan oder Knopfdruck gedruckt, ohne manuelles Formatieren.
- **Smart-Home-Integration**: eine eigene Home Assistant Custom Component (siehe
  [`scripts/homeassistant/`](scripts/homeassistant/README.md)) macht den Drucker als
  Entität verfügbar, z. B. um Automationen Bondrucker-Ausdrucke auslösen zu lassen.
- **Als Vorlage/Referenz**, wenn du selbst eine FastAPI + React-Anwendung mit
  persistenter Queue, YAML-getriebenen Vorlagen und einem Markdown→ESC/POS-Renderer
  bauen möchtest – die Dokumentation in [`docs/`](docs/) beschreibt Architektur,
  Datenbankschema, Sicherheitskonzept und Testkonzept im Detail.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLite (SQLAlchemy), `python-escpos`, Pillow, `mistune`
- **Frontend**: React, TypeScript, Vite
- **Deployment**: Docker / Docker Compose

## Quick Start

```bash
cp .env.example .env
# Edit .env: set API_KEY, PRINTER_HOST, PRINTER_PORT, ...

docker compose up --build
```

- Frontend: http://localhost:5173 (nginx attaches `X-API-Key` for you, see [`docs/security.md`](docs/security.md))
- Backend API: http://localhost:8000 (API docs at `/docs`, protected by `X-API-Key`)
- Health check (no auth): http://localhost:8000/health

Direct backend requests (except `/health`) require the header:

```
X-API-Key: <API_KEY aus .env>
```

## Dokumentation

Eine vollständige Dokumentation befindet sich in [`docs/`](docs/):

| Dokument | Inhalt |
|---|---|
| [`architecture.md`](docs/architecture.md) | Architekturdiagramm & Datenflüsse |
| [`components.md`](docs/components.md) | Komponentenübersicht |
| [`database-schema.md`](docs/database-schema.md) | Datenbankschema (DDL + ER-Diagramm) |
| [`openapi.yaml`](docs/openapi.yaml) | API-Spezifikation (OpenAPI 3.1, generiert) |
| [`directory-structure.md`](docs/directory-structure.md) | Verzeichnisstruktur |
| [`configuration.md`](docs/configuration.md) | Konfiguration in der Web-App (Preset-Integrationen, .env-Sperrlogik) |
| [`docker.md`](docs/docker.md) | Docker- & Compose-Konfiguration |
| [`security.md`](docs/security.md) | Sicherheitskonzept |
| [`markdown-mapping.md`](docs/markdown-mapping.md) | Markdown → ESC/POS Mapping & Degradation |
| [`scripts/`](docs/scripts/README.md) | Benutzerhandbuch für die API-Clients (PowerShell-Modul & Python-Bibliothek/CLI) |

## Datenschutz (Kurzfassung)

Nach **erfolgreichem** Druck werden Inhalt (`markdown`, `title`, `icon`, gerenderte Druckdaten)
sowie eine eventuelle Fehlermeldung aus der Datenbank gelöscht. Es bleiben nur `id`, `status`,
`created_at` und `completed_at` erhalten. Bei nicht erfolgreich gedruckten Aufträgen
(`queued`, `printing`, `failed`, `cancelled`) bleiben Inhalt und Fehlermeldung erhalten, damit
sie erneut versucht, eingesehen oder abgebrochen werden können. Details siehe
[`docs/security.md`](docs/security.md).

## Font Awesome Icons

Die Kopf-Icons werden aus der mitgelieferten Font-Awesome-Free-Schriftdatei (Solid, SIL OFL 1.1)
gerendert — siehe [`backend/assets/fontawesome/README.md`](backend/assets/fontawesome/README.md).
Über `GET /api/icons` kann das Frontend die Liste der verfügbaren Icon-Namen für eine
Such-/Auswahlkomponente abrufen. Fehlen die Asset-Dateien (z. B. nach einer
Pfad-Umkonfiguration) oder ist ein Icon-Name unbekannt, wird ein Platzhalter gedruckt (kein
Fehler).

## Entwicklung ohne Docker

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Tests

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

## Lizenz

[MIT](LICENSE) – Nutzung, Anpassung und Weiterverbreitung sind frei, solange Lizenz- und
Copyright-Hinweis erhalten bleiben.
