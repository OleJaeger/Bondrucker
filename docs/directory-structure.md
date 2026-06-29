# Verzeichnisstruktur

```
Bondrucker/
├── README.md
├── LICENSE                        # MIT
├── docker-compose.yml
├── docker-compose.local.yml        # Lokale Entwicklung ohne Traefik/Authentik
├── .env.example                   # Vorlage für die docker-compose-Umgebung
├── .gitignore
├── .githubignore                  # Zusätzliche Ausschlüsse für den GitHub-Mirror
│
├── docs/                          # Diese Dokumentation
│   ├── architecture.md
│   ├── components.md
│   ├── database-schema.md
│   ├── directory-structure.md
│   ├── docker.md
│   ├── presets.md
│   ├── configuration.md
│   ├── security.md
│   ├── testing.md
│   ├── markdown-mapping.md
│   ├── self-review.md
│   ├── scripts/                    # Benutzerhandbücher für scripts/*
│   │   ├── README.md
│   │   ├── powershell.md
│   │   ├── python.md
│   │   └── homeassistant.md
│   └── openapi.yaml               # generiert: backend/scripts/export_openapi.py
│
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt           # Laufzeit-Abhängigkeiten
│   ├── requirements-dev.txt       # + Test-/Dev-Werkzeuge
│   │
│   ├── app/
│   │   ├── main.py                # FastAPI-App, Lifespan, Router-Registrierung
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── database.py            # SQLAlchemy Engine/Session (SQLite, WAL)
│   │   ├── models.py              # ORM-Modell PrintJob, JobStatus-Enum
│   │   ├── schemas.py             # Pydantic Request-/Response-Modelle
│   │   ├── security.py            # X-API-Key Dependency
│   │   ├── exceptions.py          # Anwendungsfehler → HTTP-Mapping
│   │   ├── logging_config.py      # Konsole + rotierende Logdatei
│   │   │
│   │   ├── api/                   # REST-Endpunkte
│   │   │   ├── health.py          # GET /health
│   │   │   ├── jobs.py            # /api/jobs (CRUD + Abbruch)
│   │   │   ├── presets.py         # /api/presets (Standarddruckobjekte)
│   │   │   ├── preview.py         # POST /api/preview (PNG)
│   │   │   ├── printer.py         # GET /api/printer/status
│   │   │   ├── icons.py           # GET /api/icons (verfügbare Icon-Namen)
│   │   │   ├── settings.py        # /api/settings (Preset-Integrationen, siehe configuration.md)
│   │   │   ├── table.py           # Tabellen-Hilfsendpunkt für Markdown-Tabellen
│   │   │   └── templates.py       # GET /api/templates
│   │   │
│   │   ├── templates/              # Vorlagensystem
│   │   │   ├── schema.py          # Pydantic-Schema für Vorlagen-YAML
│   │   │   └── loader.py          # TemplateRegistry (lädt config/templates/*.yaml)
│   │   │
│   │   ├── presets/                 # Standarddruckobjekte (siehe presets.md)
│   │   │   ├── schema.py           # Pydantic-Schema für Preset-YAML
│   │   │   ├── loader.py           # PresetRegistry (lädt config/presets/*.yaml)
│   │   │   ├── builder.py          # build_preset_payload(preset)
│   │   │   ├── script_runner.py    # run_content_script(name)
│   │   │   ├── grid_images.py      # Hilfsfunktionen für Bild-Anhänge (Ausmalbild, ...)
│   │   │   └── scripts/             # Inhalts-Skripte (generate() -> str)
│   │   │       ├── positive_message.py
│   │   │       ├── tenets_of_it.py
│   │   │       ├── random_animal.py
│   │   │       ├── weather_forecast.py
│   │   │       ├── mealie_shopping_list.py
│   │   │       ├── super_productivity_today.py
│   │   │       ├── jagdtag_heute.py
│   │   │       └── custom/             # Eigene Skripte, nicht in git (siehe presets.md)
│   │   │           ├── README.md
│   │   │           └── __init__.py
│   │   │
│   │   ├── rendering/              # Markdown → IR → ESC/POS / PNG
│   │   │   ├── document.py        # Zwischendarstellung (Document, Block-Typen)
│   │   │   ├── markdown.py        # mistune-AST → IR, Degradationsregeln
│   │   │   ├── builder.py         # build_document(payload)
│   │   │   ├── layout.py          # Wortumbruch, Tabellen, Einzug
│   │   │   ├── icons.py           # Font-Awesome-Icon-Rendering
│   │   │   ├── attachments.py     # QR-Code-/Bild-Anhänge
│   │   │   ├── text_image.py      # Text → Bitmap (für PNG-Vorschau/ESC/POS)
│   │   │   ├── escpos_renderer.py # IR → ESC/POS-Befehle
│   │   │   └── png_renderer.py    # IR → PNG (Vorschau)
│   │   │
│   │   ├── printing/                # Drucker-Anbindung
│   │   │   ├── client.py          # PrinterClient (escpos.printer.Network)
│   │   │   └── worker.py          # QueueWorker (Hintergrundthread, Retry/Backoff)
│   │   │
│   │   └── repositories/
│   │       ├── jobs.py            # JobRepository (einziger DB-Zugriffspunkt fuer print_jobs)
│   │       └── settings.py        # SettingsRepository (app_settings - Web-Overrides, siehe configuration.md)
│   │
│   ├── config/
│   │   ├── templates/               # Vorlagenkonfigurationen (YAML, editierbar)
│   │   │   ├── freitext.yaml
│   │   │   ├── todo.yaml
│   │   │   ├── message.yaml
│   │   │   ├── gemaelde.yaml
│   │   │   └── custom/               # Eigene Vorlagen, nicht in git (siehe presets.md)
│   │   │       └── README.md
│   │   └── presets/                 # Standarddruckobjekte (YAML, editierbar)
│   │       ├── wlan-qrcode.yaml
│   │       ├── positive-nachricht.yaml
│   │       ├── tenets-of-it.yaml
│   │       ├── heutige-aufgaben.yaml
│   │       ├── einkaufsliste.yaml
│   │       ├── wettervorhersage.yaml
│   │       ├── jagdtag-heute.yaml
│   │       ├── ausmalbild.yaml
│   │       ├── fridge-art.yaml
│   │       └── custom/               # Eigene Presets, nicht in git (siehe presets.md)
│   │           └── README.md
│   │
│   ├── assets/
│   │   ├── fontawesome/            # Font-Awesome-Webfont + Icon-Map (SIL OFL 1.1)
│   │   │   ├── README.md
│   │   │   ├── LICENSE.txt
│   │   │   ├── fa-solid-900.ttf
│   │   │   └── icon-map.json
│   │   ├── icons/                  # Eigene SVG-Icons (siehe README.md)
│   │   │   ├── README.md
│   │   │   ├── hummel.svg
│   │   │   └── logo.svg
│   │   └── images/                 # Bildmaterial für Bild-Presets (z. B. Ausmalbild)
│   │       ├── README.md
│   │       └── animals.png
│   │
│   ├── examples/                   # Beispiel-Druckauftrags-Payloads (JSON)
│   │   ├── README.md
│   │   ├── job-freitext.json
│   │   ├── job-todo.json
│   │   └── job-table.json
│   │
│   ├── scripts/
│   │   ├── README.md
│   │   ├── add_config.py           # legt neue Presets/Templates an (siehe README.md)
│   │   └── export_openapi.py       # generiert docs/openapi.yaml aus der laufenden App
│   │
│   ├── data/                        # SQLite-DB (Docker-Volume, .db* gitignored)
│   ├── logs/                        # Logdateien (Docker-Volume, *.log gitignored)
│   │
│   └── tests/                       # pytest-Suite (siehe testing.md)
│       ├── conftest.py
│       ├── fakes.py                # FakePrinterClient/-Server, StubWorker
│       ├── test_attachments.py
│       ├── test_config.py
│       ├── test_grid_images.py
│       ├── test_jobs_api.py
│       ├── test_layout.py
│       ├── test_markdown.py
│       ├── test_preset_scripts.py
│       ├── test_presets.py
│       ├── test_presets_api.py
│       ├── test_printer_client.py
│       ├── test_rendering.py
│       ├── test_repository.py
│       ├── test_security.py
│       ├── test_settings_api.py
│       ├── test_table_api.py
│       ├── test_templates.py
│       ├── test_templates_api.py
│       └── test_worker.py
│
├── frontend/
│   ├── Dockerfile                   # Multi-Stage: Vite-Build → nginx
│   ├── .dockerignore
│   ├── nginx.conf.template          # Reverse-Proxy /api, /health → Backend, setzt X-API-Key
│   ├── package.json
│   ├── vite.config.ts               # Dev-Proxy /api, /health → localhost:8000, setzt X-API-Key
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                   # Router (7 Routen unter Layout)
│       ├── index.css                 # Design-System (Sidebar, Karten, Formulare, ...)
│       │
│       ├── api/
│       │   ├── types.ts              # TS-Typen passend zu app/schemas.py
│       │   └── client.ts             # Fetch-Wrapper, ApiError
│       │
│       ├── context/
│       │   └── ToastContext.tsx      # Globale Toast-/Benachrichtigungs-Anzeige
│       │
│       ├── components/
│       │   ├── Layout.tsx            # Sidebar-Navigation
│       │   ├── IconPicker.tsx        # Icon-Auswahl (Font-Awesome + SVG)
│       │   ├── IconGlyph.tsx         # Icon-Glyph-Darstellung (FA-Ligatur/SVG)
│       │   ├── JobList.tsx           # Job-Tabelle mit Abbrechen
│       │   ├── PreviewPane.tsx        # Live-PNG-Vorschau (debounced)
│       │   └── StatusBadge.tsx        # Status-/Online-Badges
│       │
│       └── pages/
│           ├── Dashboard.tsx
│           ├── CreateJob.tsx
│           ├── Presets.tsx
│           ├── Queue.tsx
│           ├── FailedJobs.tsx
│           ├── PrinterStatus.tsx
│           └── Settings.tsx          # /settings (Preset-Integrationen, siehe configuration.md)
│
├── scripts/                          # API-Clients & Integrationen (siehe docs/scripts/)
│   ├── powershell/
│   │   ├── Bondrucker.psd1           # Modul-Manifest
│   │   └── Bondrucker.psm1           # Cmdlets für die REST-API
│   ├── python/
│   │   ├── bondrucker_api.py          # Bibliothek + CLI für die REST-API
│   │   └── requirements.txt
│   └── homeassistant/                 # Home Assistant Custom Component (HACS)
│       ├── README.md
│       ├── hacs.json
│       └── custom_components/bondrucker/
│           ├── manifest.json
│           ├── __init__.py
│           ├── config_flow.py         # UI-Konfiguration (Host, API-Key)
│           ├── coordinator.py         # Polling des Drucker-Status
│           ├── sensor.py              # Drucker-Status-Sensor
│           ├── button.py              # Buttons zum Auslösen von Presets
│           ├── const.py
│           ├── strings.json / translations/
│           └── brand/                 # Icons für den HA-Brand-Katalog
│
└── src/icon.icon/                    # macOS-Icon-Quelle für icon.png (Icon Composer)
```

## Hinweise

- **`backend/config/templates/`** wird in `docker-compose.yml` read-only in den
  Container gemountet – neue Vorlagen können durch Hinzufügen einer `*.yaml`-Datei
  in diesem Verzeichnis (und Neustart des Backend-Containers) ergänzt werden, ohne
  das Image neu zu bauen.
- **`backend/config/presets/`** wird ebenso read-only gemountet – neue
  Standarddruckobjekte können durch Hinzufügen einer `*.yaml`-Datei in diesem
  Verzeichnis ergänzt werden (siehe [`presets.md`](presets.md)).
- **`backend/assets/fontawesome/`** enthält die Font-Awesome-Free-Solid-Schriftdatei
  und die Icon-Map (SIL OFL 1.1 / CC BY 4.0); siehe `backend/assets/fontawesome/README.md`.
- **`backend/data/`** und **`backend/logs/`** sind als Bind-Mounts in
  `docker-compose.yml` eingebunden und enthalten zur Laufzeit erzeugte Dateien
  (SQLite-DB, Logs) – beide sind bis auf `.gitkeep` per `.gitignore` ausgeschlossen.
- **`custom/`**-Unterverzeichnisse von `backend/config/templates/`,
  `backend/config/presets/` und `backend/app/presets/scripts/` sind (bis auf
  je eine `README.md`/`__init__.py`) per `.gitignore` ausgeschlossen - gedacht
  für persönliche Vorlagen/Presets/Skripte, die nicht versioniert werden
  sollen (siehe [`presets.md`](presets.md#eigene-nicht-versionierte-presetsskripte-custom)).
- **`docs/openapi.yaml`** ist generiert (`backend/scripts/export_openapi.py`) und
  sollte nach Änderungen an `app/api/*` oder `app/schemas.py` neu erzeugt werden.
- **`.githubignore`** ist kein von Git ausgewertetes Standardformat, sondern eine
  Liste von Pfaden, die der Gitea-Action `.gitea/workflows/sync-github.yml` beim
  Spiegeln dieses (intern gehosteten) Repos nach GitHub zusätzlich ausschließt.
