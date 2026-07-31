# Komponentenübersicht

## Backend (`backend/app/`)

| Modul | Zweck |
|---|---|
| `main.py` | FastAPI-App, Lifespan (DB-Init, Worker-Start/Stop, Recovery), CORS, globale Exception-Handler, Router-Registrierung. |
| `config.py` | `Settings` (pydantic-settings), liest `.env`/Umgebungsvariablen. `get_settings()` ist `lru_cache`d. |
| `database.py` | SQLAlchemy-Engine (SQLite, WAL-Modus, `check_same_thread=False`), Session-Factory, `init_db()`, `session_scope()` für Threads außerhalb der FastAPI-DI. |
| `models.py` | ORM-Modell `PrintJob`, Enum `JobStatus`, `utcnow()`-Helfer. |
| `schemas.py` | Pydantic-Request/Response-Modelle (`PrintJobCreate`, `PrintJobResponse`, `PrinterStatusResponse`, `TemplateInfo`, `PresetInfo`). |
| `security.py` | `require_api_key`-Dependency (`X-API-Key`-Header, `secrets.compare_digest`, registriert OpenAPI-Security-Schema). |
| `exceptions.py` | Anwendungsfehler (`AppError`-Subklassen), in `main.py` auf HTTP-Statuscodes gemappt. |
| `logging_config.py` | Root-Logger: Konsole + rotierende Datei unter `LOG_DIR`. |

### `app/api/` – REST-Endpunkte

| Datei | Endpunkte |
|---|---|
| `health.py` | `GET /health` (kein API-Key). |
| `jobs.py` | `POST /api/jobs`, `GET /api/jobs`, `GET /api/jobs/{id}`, `DELETE /api/jobs/{id}` (Abbruch). |
| `preview.py` | `POST /api/preview` → PNG. |
| `printer.py` | `GET /api/printer/status`. |
| `templates.py` | `GET /api/templates` (für das Frontend-Formular). |
| `presets.py` | `GET /api/presets`, `POST /api/presets/{key}/print` (Standarddruckobjekte, siehe [`presets.md`](presets.md)). |
| `settings.py` | `GET`/`PUT /api/settings` (Preset-Integrationen, siehe [`configuration.md`](configuration.md)). |

### `app/templates/` – Vorlagensystem

| Datei | Zweck |
|---|---|
| `schema.py` | Pydantic-Schema für Vorlagen-YAML (`TemplateConfig`, `LayoutConfig`, `DefaultFormatting`, `TextStyle`). |
| `loader.py` | `TemplateRegistry` lädt `*.yaml`/`*.yml` aus `TEMPLATES_DIR`. Ungültige Dateien werden geloggt und übersprungen (Anwendung startet trotzdem). `key` = Dateiname ohne Endung. |

### `app/presets/` – Standarddruckobjekte (Presets)

Siehe [`presets.md`](presets.md) für das YAML-Schema und wie eigene
Inhalts-Skripte geschrieben werden.

| Datei | Zweck |
|---|---|
| `schema.py` | Pydantic-Schema für Preset-YAML (`PresetConfig`, `PresetAttachment`). |
| `loader.py` | `PresetRegistry` lädt `*.yaml`/`*.yml` aus `PRESETS_DIR` (analog `TemplateRegistry`). |
| `builder.py` | `build_preset_payload(preset)`: führt `content_script` aus (falls gesetzt) und baut daraus ein `PrintJobCreate`-Payload inkl. Anhang (QR-Code/Bild). |
| `script_runner.py` | `run_content_script(name)`: importiert `app.presets.scripts.<name>` und ruft dessen `generate() -> str` auf. |
| `scripts/*.py` | Inhalts-Skripte (`generate() -> str`), referenziert über `content_script` im Preset-YAML. |

### `app/rendering/` – Rendering-Pipeline

| Datei | Zweck |
|---|---|
| `document.py` | Druckerunabhängige Zwischendarstellung (`Document`, `Block`-Varianten: `Heading`, `Paragraph`, `ListItem`, `TableBlock`, `ThematicBreak`, `ImageBlock`, `TextRun`). |
| `markdown.py` | `mistune`-AST → IR. Degradationsregeln für nicht unterstützte Elemente (siehe [`markdown-mapping.md`](markdown-mapping.md)). Längenlimit 50.000 Zeichen. |
| `builder.py` | `build_document(payload)`: kombiniert Vorlage (Registry) + geparstes Markdown + optionalen Anhang (Bild/QR-Code, als `ImageBlock` vor den Inhalt gestellt) zu einem `Document`. Von API, Vorschau und Worker gemeinsam genutzt. |
| `layout.py` | Wortumbruch, Tabellenspaltenbreiten, Listen-Einzug, Ausrichtung – von ESC/POS- und PNG-Renderer gemeinsam genutzt. |
| `text_image.py` | Gemeinsame Schriftverwaltung (`load_font`, `base_font_size` – verhindert Zeilenumbruch-Überlauf in der PNG-Vorschau) und `render_checklist_item` (rendert Checkbox-Icon + Aufgabentext als gemeinsame Bitmap für ESC/POS und PNG). |
| `icons.py` | `IconRenderer`: rendert ein Font-Awesome-Glyph aus TTF + Codepoint-Map zu einer Bitmap; Fallback auf Platzhalter-Box, falls Assets fehlen/Icon unbekannt. |
| `attachments.py` | `decode_uploaded_image`/`generate_qr_image`: wandeln ein hochgeladenes Bild bzw. einen QR-Code-Inhalt in eine zentrierte Schwarz/Weiß-Bitmap (Modus `"1"`) für `ImageBlock` um (siehe [`markdown-mapping.md`](markdown-mapping.md#anhänge-bild-upload-und-qr-code)). |
| `escpos_renderer.py` | `Document` → ESC/POS-Befehle (Ausrichtung, Fett/Unterstrichen, Schriftgröße, Tabellen, Icon-/Anhangsbilder als Raster, Vorschub, Schnitt). |
| `png_renderer.py` | `Document` → PNG (für `/api/preview`), nutzt dieselbe Layout-Engine wie der ESC/POS-Renderer. |

### `app/printing/` – Drucker-Anbindung

| Datei | Zweck |
|---|---|
| `client.py` | `PrinterClient`: `escpos.printer.Network`-Wrapper. `print_document()` (wirft `PrinterOfflineError`/`PrinterCommandError`), `is_online()` (best-effort Verbindungstest für den Statusendpunkt). |
| `worker.py` | `QueueWorker`: Hintergrundthread, FIFO-Polling, Retry mit exponentiellem Backoff (unbegrenzt), `recover_interrupted_jobs()` beim Start, Privacy-Scrub bei Erfolg. |

### `app/repositories/jobs.py`

`JobRepository` – einzige Stelle mit Lese-/Schreibzugriff auf `print_jobs`. Kapselt:

- FIFO-Auswahl über Status `queued` + fällige `failed` (`fetch_next_runnable`),
- Statusübergänge (`mark_printing`, `mark_completed`, `mark_failed`, `cancel`),
- Privacy-Scrub (`mark_completed` löscht `payload_json`/`error_message`),
- Wiederherstellung nach Neustart (`recover_interrupted`).

### `app/repositories/settings.py`

`SettingsRepository` – Lese-/Schreibzugriff auf `app_settings` (Web-Overrides
der Preset-Integrationen, siehe [`configuration.md`](configuration.md)):
`get_all()`, `set(key, value)`, `delete(key)` (Override entfernen → Default).

## Frontend (`frontend/src/`)

| Pfad | Zweck |
|---|---|
| `main.tsx`, `App.tsx` | Einstiegspunkt, Router (7 Routen unter gemeinsamem `Layout`). |
| `api/types.ts` | TypeScript-Typen, die die Backend-Schemas spiegeln. |
| `api/client.ts` | Fetch-Wrapper: Fehlerbehandlung (`ApiError`), Funktionen für alle Endpunkte. Sendet keinen `X-API-Key` - das übernimmt nginx (siehe [`security.md`](security.md)). |
| `components/Layout.tsx` | Sidebar-Navigation. |
| `components/IconPicker.tsx` | Icon-Auswahl (Font-Awesome + benutzerdefinierte SVGs). |
| `components/IconGlyph.tsx` | Rendert ein Icon-Glyph (Font-Awesome-Ligatur oder SVG-`<img>`), genutzt von `IconPicker` und `Presets`. |
| `components/JobList.tsx` | Wiederverwendbare Job-Tabelle (mit optionalem "Abbrechen"). |
| `components/PreviewPane.tsx` | Live-Vorschau (debounced PNG-Fetch von `/api/preview`). |
| `components/StatusBadge.tsx` | Status-/Online-Badges mit deutschen Labels. |
| `pages/Dashboard.tsx` | Übersicht: Warteschlange, fehlgeschlagene Jobs, Druckerstatus (Polling). |
| `pages/CreateJob.tsx` | Formular für neue Druckaufträge inkl. Live-Vorschau. |
| `pages/Presets.tsx` | Standarddruckobjekte als Karten (Icon, Name, Beschreibung), Drucken per Klick. |
| `pages/Queue.tsx` | Aktuelle Warteschlange (`queued`/`printing`), Abbrechen. |
| `pages/FailedJobs.tsx` | Fehlgeschlagene Jobs, Abbrechen. |
| `pages/PrinterStatus.tsx` | Detaillierter Druckerstatus + aktueller Job. |
| `pages/Settings.tsx` | Konfiguration der Preset-Integrationen (Mealie, HomeAssistant/Wetter, Super Productivity, Jagdtag); per .env gesperrte Felder werden deaktiviert angezeigt. |

## Externe Abhängigkeiten

| Bibliothek | Zweck |
|---|---|
| `fastapi`, `uvicorn` | HTTP-API. |
| `sqlalchemy` | ORM/Datenzugriff (SQLite). |
| `pydantic-settings` | Konfiguration aus Umgebungsvariablen/`.env`. |
| `python-escpos` | ESC/POS-Protokoll für den Netzwerkdrucker. |
| `mistune` | Markdown-Parser (AST-Modus, Tabellen/Task-Lists/Strikethrough-Plugins). |
| `Pillow` | Icon-/Checkbox-/Bild-Rendering (Font Awesome, Anhänge → Bitmap) und PNG-Vorschau. |
| `qrcode` | Generiert QR-Code-Bitmaps für den `qr_code`-Anhang. |
| `PyYAML` | Vorlagen- und Preset-Konfiguration. |
| `httpx` | HTTP-Client für Preset-Inhalts-Skripte (Mealie, Open-Meteo, Super Productivity). |
| React, react-router-dom, Vite, TypeScript | Frontend-SPA. |
