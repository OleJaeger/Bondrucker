# Graph Report - Bondrucker  (2026-07-24)

## Corpus Check
- 149 files · ~90,804 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1557 nodes · 2689 edges · 175 communities (87 shown, 88 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 493 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `88adf4b6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Frontend API Client (TypeScript)
- Table Parsing (CSV/XLSX)
- German Architecture Docs
- Home Assistant Button Entity
- PowerShell/Python API CLI
- Frontend Build Tooling
- Printer Power Control Endpoints
- Text-Snippet Presets (IT/Positivity)
- Preset Registry & Errors
- Health & Icon Listing Endpoints
- Document Layout/Text Rendering
- Preset Script Dispatch
- Blog Post Feature Highlights
- Motif Sheet Image Cropping
- API Error Response Helpers
- Template Registry & Errors
- Document Builder & Image Blocks
- Settings & App Config Models
- Jobs API Tests
- Print Queue Worker
- PNG Preview Renderer
- Job State Transitions
- Preset Listing & Printing Endpoints
- Frontend TS Config (App)
- Print Jobs REST Endpoints
- Printer Client Errors & Fakes
- PowerShell Module Functions
- Frontend TS Config (Node)
- ESC/POS Printer Client
- Icon Rendering
- Mealie Shopping List Preset Tests
- Document IR & Markdown Parsing
- Preset/Template Loader
- Jagdtag-Heute Preset
- Jagdtag Preset Tests
- Wettervorhersage Preset
- Bitmap Text Rendering Helpers
- Settings API Tests
- Table API Tests
- HA Integration Manifest
- Test Queue Worker Stub
- Job Lookup Errors
- Preset & Template Catalog Docs
- API-Key Security Tests
- Preset Payload Builder
- Fake DB Cursor for Tests
- GitHub Sync & Leak Cleanup
- Printer Status Endpoint
- Print Preview Endpoint
- Templates Listing Endpoint
- Templates API Tests
- Custom Icon SVG Endpoint
- Font Awesome & Icon Licensing
- Frontend TS Config (Root)
- HA Dark-Mode Icon (2x)
- HA Icon Assets
- Bumblebee Icon Asset
- App Logo Icon Asset
- Animal Coloring-Page Image
- Custom Templates README
- Favicon Asset
- App Logo PNG Asset
- App Icon Asset
- Directory Structure Doc Update
- HA Integration Icon (2x)
- SVG Box Icon Asset
- test_grid_images.py
- Sicherheitskonzept
- print_preset
- Home Assistant Integration `bondrucker`
- Backend (`backend/app/`)
- Docker & Docker Compose
- PresetAttachment
- Nachricht (message) Template
- test_presets_api.py
- Bondrucker – Home Assistant Integration
- printer.py
- mealie_recipe_today.py
- Standarddruckobjekte (Presets)
- Selbstprüfung: Schwachstellen & Verbesserungsvorschläge
- PresetNotFoundError
- Datenbankschema
- OpenAPI Spec (generated)
- Markdown → ESC/POS Mapping
- security.md
- Testkonzept
- Bondrucker: Mein Bon-Drucker für Einkaufslisten, Aufgaben und Wetter – open source
- Architektur
- Konfiguration in der Web-App
- Release: Vorbereitung GitHub-Veröffentlichung
- Backend-Skripte
- Eigene SVG-Icons
- README.md
- Beispiel-Druckaufträge
- README.md
- README.md
- API-Clients (PowerShell-Modul & Python-Bibliothek/CLI)
- Font Awesome Free License
- Bondrucker Blog Post
- Smart-Home-Anbindung (Home Assistant)
- Markdown-Eingabe mit Live-Vorschau
- Persistente Warteschlange mit Retries
- Datenschutz by Design
- Druckauftraege ueber REST-API
- Vorschlaege fuer Screenshots vor Veroeffentlichung
- Standarddruckobjekte (Presets)
- V330M 80mm Thermodrucker (ESC/POS)
- Vibe-Coding mit Claude Code
- Erweiterbar ueber YAML (Vorlagen/Presets ohne Codeaenderung)
- Zwei-Container-Topologie (Frontend/Backend, Single Origin, kein CORS)
- Datenfluss Markdown → IR → ESC/POS/PNG
- Neustart-Recovery unterbrochener Druckaufträge
- build_document() – Vorlage+Markdown+Anhang zu Document
- JobRepository (print_jobs-Zugriffspunkt)
- PresetRegistry
- PrinterClient (escpos.printer.Network-Wrapper)
- QueueWorker (Hintergrundthread)
- Rendering-Pipeline (document/layout/escpos/png)
- SettingsRepository (app_settings-Zugriffspunkt)
- TemplateRegistry
- Preset config_keys-Registrierung
- Sperrlogik '.env gewinnt immer' (Settings-Layering)
- WEB_SETTINGS_FIELDS (editierbare Preset-Settings)
- Tabelle app_settings
- FIFO-Auswahl fetch_next_runnable
- Tabelle print_jobs
- Privacy-Scrub bei mark_completed
- Anhänge: Bild-Upload und QR-Code als ImageBlock
- Degradationsregeln für nicht unterstützte Markdown-Elemente
- attachment.script/generate_image()-Mechanismus
- content_script/generate()-Mechanismus
- custom/-Verzeichnisse für nicht versionierte Presets/Skripte/Vorlagen
- grid_images.py Motivtafel-Zuschnitt (rotes Raster)
- BondruckerStatusCoordinator/BondruckerPresetCoordinator
- Bondrucker PowerShell-Cmdlets
- Gemeinsame Konfigurationsauflösung (BaseUrl/ApiKey-Reihenfolge)
- X-API-Key-Authentifizierung (require_api_key)
- Synchrone ausgehende Verbindungen der Preset-Skripte
- Bedrohungsmodell: lokales Netzwerk, Heimnetz-Einsatz
- Empfehlung TLS-terminierender Reverse-Proxy
- Fehlendes Health-Signal für Worker-Thread
- Fehlendes DB-Migrationswerkzeug (Alembic)
- Fehlende Paginierung bei GET /api/jobs
- Fehlendes Rate-Limiting / Queue-Obergrenze
- Fehlendes Wall-Clock-Timeout im Worker
- Akzeptierte Coverage-Lücken
- Test-Doubles (FakePrinterClient/StubWorker/FakePrinterServer)
- index.html Entry Point (main.tsx)
- Bondrucker README
- Dokumentations-Uebersicht
- Font Awesome Icons / GET /api/icons
- MIT-Lizenz
- Wofuer kann man es nutzen?
- Datenleak-Bereinigung (ole-lab.de -> bondrucker-app.de)
- GitHub-Sync Setup (.githubignore + Gitea-Action)
- MIT-Lizenz vergeben
- README-Ueberarbeitung fuer oeffentliches Publikum
- Bondrucker Home Assistant Custom Component
- HA Entities (Queue-Sensor, Status-Sensor, Testdruck-Button)
- HA Installation (manuell / HACS)

## God Nodes (most connected - your core abstractions)
1. `PresetScriptError` - 57 edges
2. `get_settings()` - 32 edges
3. `JobRepository` - 32 edges
4. `PresetConfig` - 26 edges
5. `build_document()` - 26 edges
6. `render_document()` - 25 edges
7. `parse_markdown()` - 25 edges
8. `render_preview()` - 25 edges
9. `QueueWorker` - 23 edges
10. `_FakeResponse` - 23 edges

## Surprising Connections (you probably didn't know these)
- `backend service (docker-compose.local.yml)` --semantically_similar_to--> `backend service (docker-compose.yml, Traefik)`  [INFERRED] [semantically similar]
  docker-compose.local.yml → docker-compose.yml
- `frontend service (docker-compose.local.yml)` --semantically_similar_to--> `frontend service (docker-compose.yml, Traefik)`  [INFERRED] [semantically similar]
  docker-compose.local.yml → docker-compose.yml
- `test_random_cell_png_invalid_image_raises()` --indirect_call--> `PresetScriptError`  [INFERRED]
  backend/tests/test_grid_images.py → backend/app/exceptions.py
- `test_random_cell_png_missing_file_raises()` --indirect_call--> `PresetScriptError`  [INFERRED]
  backend/tests/test_grid_images.py → backend/app/exceptions.py
- `Jagdtag (heute) Preset` --references--> `generate()`  [EXTRACTED]
  backend/config/presets/jagdtag-heute.yaml → backend/app/presets/scripts/jagdtag_heute.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Docker-Compose-Deployment-Topologie (lokal vs. produktiv mit Traefik/Authentik)** — docker_compose_local_backend, docker_compose_local_frontend, docker_compose_backend, docker_compose_frontend, docker_compose_traefik_authentik [INFERRED 0.85]
- **Home-Assistant-Smart-Home-Integration** — blog_post_home_assistant, scripts_homeassistant_readme_component, scripts_homeassistant_readme_entities, scripts_homeassistant_readme_installation [INFERRED 0.85]
- **Font Awesome Icon Usage Across Presets and Templates** — backend_assets_fontawesome_readme, backend_config_presets_ausmalbild_preset, backend_config_presets_einkaufsliste_preset, backend_config_presets_essenplan_woche_preset, backend_config_presets_heutige_aufgaben_preset, backend_config_presets_jagdtag_heute_preset, backend_config_presets_positive_nachricht_preset, backend_config_presets_tenets_of_it_preset, backend_config_presets_wettervorhersage_preset, backend_config_presets_wlan_qrcode_preset, backend_config_templates_message_template, backend_config_templates_todo_template [INFERRED 0.85]
- **Non-Versioned Custom Overlay Directory Pattern** — backend_app_presets_scripts_custom_readme, backend_config_presets_custom_readme, backend_config_templates_custom_readme [INFERRED 0.95]
- **Shared Print Template Config Schema** — backend_config_templates_freitext_template, backend_config_templates_gemaelde_template, backend_config_templates_message_template, backend_config_templates_todo_template [INFERRED 0.85]
- **'Nie hart fehlschlagen' – Degradation statt Fehler (Markdown, Vorlagen, Presets, Icons)** — docs_markdown_mapping_degradation_rules, docs_components_templateregistry, docs_security, docs_presets [INFERRED 0.75]
- **Privacy-by-Design: Inhalte nach erfolgreichem Druck löschen** — docs_database_schema_privacy_scrub, docs_security, docs_self_review, docs_openapi_printjobresponse [INFERRED 0.85]
- **Drei Clients, dieselbe REST-API (Python, PowerShell, Home Assistant)** — docs_scripts_python_bondruckerclient, docs_scripts_powershell_cmdlets, docs_scripts_homeassistant_coordinators, docs_openapi [EXTRACTED 1.00]

## Communities (175 total, 88 thin omitted)

### Community 0 - "Frontend API Client (TypeScript)"
Cohesion: 0.06
Nodes (73): ApiError, cancelJob(), convertTable(), createJob(), fetchHealth(), fetchIcons(), fetchIconSvg(), fetchJob() (+65 more)

### Community 1 - "Table Parsing (CSV/XLSX)"
Cohesion: 0.05
Nodes (59): _parse_csv(), parse_table(), _parse_xlsx(), JSONResponse, Table file conversion endpoint (``/api/table/parse``).  Accepts a CSV or XLSX up, Parse an uploaded CSV or XLSX file and convert it to a Markdown table.      Retu, _to_markdown(), AppError (+51 more)

### Community 2 - "German Architecture Docs"
Cohesion: 0.13
Nodes (12): Hinweise, Verzeichnisstruktur, Datenschutz (Kurzfassung), Dokumentation, Entwicklung ohne Docker, Font Awesome Icons, Lizenz, Quick Start (+4 more)

### Community 3 - "Home Assistant Button Entity"
Cohesion: 0.06
Nodes (38): ButtonEntity, ConfigFlow, ConfigFlowResult, DeviceInfo, async_setup_entry(), BondruckerPresetButton, AddEntitiesCallback, Any (+30 more)

### Community 4 - "PowerShell/Python API CLI"
Cohesion: 0.08
Nodes (34): ArgumentParser, Namespace, RuntimeError, _add_job_payload_arguments(), BondruckerApiError, BondruckerClient, _build_job_payload(), build_parser() (+26 more)

### Community 5 - "Frontend Build Tooling"
Cohesion: 0.05
Nodes (43): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, @fortawesome/fontawesome-free, dependencies, @fortawesome/fontawesome-free, react (+35 more)

### Community 6 - "Printer Power Control Endpoints"
Cohesion: 0.11
Nodes (19): JobStatus, Statuses for which the queue worker may still attempt a print., Statuses that will never be picked up by the worker again., PresetInfo, PrinterPowerResponse, PrinterStatusResponse, PrintJobCreate, PrintJobResponse (+11 more)

### Community 7 - "Text-Snippet Presets (IT/Positivity)"
Cohesion: 0.28
Nodes (14): add_preset(), add_template(), _apply(), _insert_into_set_literal(), main(), prompt(), prompt_bool(), prompt_key() (+6 more)

### Community 8 - "Preset Registry & Errors"
Cohesion: 0.06
Nodes (42): list_presets(), print_preset(), PrintJobResponse, Session, List the configured standard print objects (Standarddruckobjekte)., Resolve a preset to a print job and enqueue it.      The preset's content script, _presets_using(), PresetNotFoundError (+34 more)

### Community 9 - "Health & Icon Listing Endpoints"
Cohesion: 0.10
Nodes (17): health(), Unauthenticated health check endpoint., Simple liveness probe. Does not require an API key., Print job endpoints (``/api/jobs``)., Standard print object (preset) endpoints (``/api/presets``)., Print preview endpoint (``/api/preview``)., Print template listing (``/api/templates``)., Application configuration via environment variables (.env). (+9 more)

### Community 10 - "Document Layout/Text Rendering"
Cohesion: 0.05
Nodes (85): Alignment, Heading, Paragraph, Printer-agnostic intermediate representation (IR) of a rendered document.  Both, A run of text with uniform inline styling., TableBlock, TextRun, ThematicBreak (+77 more)

### Community 11 - "Preset Script Dispatch"
Cohesion: 0.09
Nodes (31): PresetScriptError, Raised when a preset's content script fails or an external dependency     (Meali, _import_script(), Dispatches a preset's ``content_script`` name to an ``app.presets.scripts`` modu, Import ``app.presets.scripts.<name>``, falling back to     ``app.presets.scripts, Import ``app.presets.scripts.<name>`` and call its ``generate()`` function., Import ``app.presets.scripts.<name>`` and call its ``generate_image()`` function, run_content_script() (+23 more)

### Community 12 - "Blog Post Feature Highlights"
Cohesion: 0.50
Nodes (5): backend service (docker-compose.yml, Traefik), frontend service (docker-compose.yml, Traefik), backend service (docker-compose.local.yml), frontend service (docker-compose.local.yml), Traefik + Authentik Forward-Auth (frontend gated, backend needs X-API-Key)

### Community 13 - "Motif Sheet Image Cropping"
Cohesion: 0.18
Nodes (16): _clean_cell(), _find_cells(), _flatten_to_white(), _load_image(), Image, random_cell_png(), Random crops from "motif sheet" images for preset image scripts.  A motif sheet, Return PNG bytes for one random cell of the motif sheet ``filename``.      ``fil (+8 more)

### Community 14 - "API Error Response Helpers"
Cohesion: 0.16
Nodes (11): IconRenderer, Image, Path, Draw a bordered box with a short label, used when the real         FontAwesome f, Return the sorted list of icon names known to the loaded icon map         and cu, Return the SVG file backing ``icon_name``, or ``None`` if         ``icon_name``, Render ``icon_name`` onto a ``size_px`` x ``size_px`` grayscale image., test_icon_renderer_falls_back_to_placeholder_for_unreadable_custom_svg() (+3 more)

### Community 15 - "Template Registry & Errors"
Cohesion: 0.08
Nodes (28): list_templates(), List the configured print templates (key, display name, type, icon).      Used b, Raised when a job references a template that does not exist., TemplateNotFoundError, Path, In-memory registry of template configurations.      Invalid files (bad YAML or f, TemplateRegistry, DefaultFormatting (+20 more)

### Community 16 - "Document Builder & Image Blocks"
Cohesion: 0.15
Nodes (25): get_settings(), Return a cached Settings instance.      Cached so the .env file is only parsed o, build_document(), Any, Resolve ``payload`` (``template``/``title``/``icon``/``markdown``/     ``image_b, ImageBlock, An uploaded image or generated QR code, rendered as a single raster     image (a, get_template_registry() (+17 more)

### Community 17 - "Settings & App Config Models"
Cohesion: 0.16
Nodes (15): env_locked_fields(), get_effective_settings(), Names of ``Settings`` fields explicitly set via the environment or .env.      Th, ``Settings`` with web-configured overrides applied.      Layers, from lowest to, AppSetting, A single web-configured override for a Settings field (``app/config.py``)., Any, Session (+7 more)

### Community 18 - "Jobs API Tests"
Cohesion: 0.06
Nodes (13): Loads and validates standard print object (preset) configurations from YAML file, Drop the cached registry so it is reloaded on next access (tests)., reset_preset_registry(), reset_icon_renderer(), Loads and validates print template configurations from YAML files., Drop the cached registry so it is reloaded on next access (tests)., reset_template_registry(), Point the app at a temporary DB/log dir and the real template configs. (+5 more)

### Community 19 - "Print Queue Worker"
Cohesion: 0.21
Nodes (4): QueueWorker, Polls the database for runnable jobs and prints them one at a time., Requeue jobs left in ``printing`` state by an unclean shutdown.          Must be, Pick up and print one job, if any is runnable.          Returns ``True`` if a jo

### Community 20 - "PNG Preview Renderer"
Cohesion: 0.22
Nodes (21): Settings, _draw_heading(), _draw_lines(), _draw_list_item(), _draw_paragraph(), _draw_table(), _draw_thematic_break(), _draw_timestamp() (+13 more)

### Community 21 - "Job State Transitions"
Cohesion: 0.14
Nodes (16): InvalidJobStateError, Raised on illegal job state transitions (e.g. cancel of a printing job)., Current time in UTC, stored as a naive datetime (convention: all     timestamps, utcnow(), ``JobRepository`` - queue ordering, state transitions and privacy scrubbing., repo(), test_cancel_already_terminal_job_raises(), test_cancel_printing_job_raises() (+8 more)

### Community 22 - "Preset Listing & Printing Endpoints"
Cohesion: 0.24
Nodes (11): _build_response(), _coerce_value(), list_settings(), Session, Web-configurable application settings endpoints (``/api/settings``).  Exposes ex, List all web-configurable settings fields and their current/effective values., Update one or more settings fields.      ``payload`` is sparse - only keys to ch, update_settings() (+3 more)

### Community 23 - "Frontend TS Config (App)"
Cohesion: 0.09
Nodes (22): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+14 more)

### Community 24 - "Print Jobs REST Endpoints"
Cohesion: 0.27
Nodes (10): cancel_job(), create_job(), get_job(), list_jobs(), JobStatus, PrintJobCreate, PrintJobResponse, Session (+2 more)

### Community 25 - "Printer Client Errors & Fakes"
Cohesion: 0.17
Nodes (17): PrinterOfflineError, Raised when the printer cannot be reached over the network., Document, A fully resolved print job ready for rendering., FakePrinterClient, Exception, Stand-in for :class:`app.printing.client.PrinterClient`.      Records every docu, _create_job() (+9 more)

### Community 26 - "PowerShell Module Functions"
Cohesion: 0.18
Nodes (21): ConvertFrom-DotEnvFile(), ConvertTo-BondruckerImageDataUrl(), Export-BondruckerApiKey(), Get-BondruckerConfig(), Get-BondruckerCredentialPath(), Get-BondruckerErrorDetail(), Get-BondruckerHealth(), Get-BondruckerIcon() (+13 more)

### Community 27 - "Frontend TS Config (Node)"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+12 more)

### Community 28 - "ESC/POS Printer Client"
Cohesion: 0.15
Nodes (6): client(), Shared pytest fixtures.  Each test gets its own temporary SQLite database and a, ``TestClient`` with a stubbed queue worker (no background thread)., Test doubles for the printer client and queue worker., Stand-in for :class:`app.printing.worker.QueueWorker` used by the API tests., StubWorker

### Community 29 - "Icon Rendering"
Cohesion: 0.12
Nodes (13): PrintJob, A single print job.      ``payload_json`` holds the job content (template, title, JobRepository, Any, datetime, JobStatus, Session, Data-access layer for print jobs.  All queue/privacy invariants (FIFO ordering a (+5 more)

### Community 30 - "Mealie Shopping List Preset Tests"
Cohesion: 0.18
Nodes (14): _FakeResponse, _mealplan_response(), _set_sp_env(), _sync_payload(), test_mealie_mealplan_no_entries(), test_mealie_shopping_list_empty_list(), test_super_productivity_today_encrypted_sync_data_raises(), test_super_productivity_today_formats_compressed_sync_data() (+6 more)

### Community 31 - "Document IR & Markdown Parsing"
Cohesion: 0.24
Nodes (13): ListItem, base_font_size(), load_font(), FreeTypeFont, Image, Shared bitmap-rendering helpers used by both the PNG preview renderer and the ES, Largest font size whose monospace character width still fits     ``width_chars``, Render one checklist item (icon + wrapped text) onto a     ``width_px``-wide 1-b (+5 more)

### Community 32 - "Preset/Template Loader"
Cohesion: 0.19
Nodes (14): get_engine(), get_session(), get_session_factory(), init_db(), Session, SQLite/SQLAlchemy engine, session management and schema initialisation., Create all tables if they do not exist yet., FastAPI dependency that yields a database session per request. (+6 more)

### Community 33 - "Jagdtag-Heute Preset"
Cohesion: 0.27
Nodes (11): _degrees_to_compass(), _fetch_jagdbares_wild(), _fetch_weather(), _format_section(), generate(), _get_ha_state(), _is_jagdzeit_relevant(), Any (+3 more)

### Community 34 - "Jagdtag Preset Tests"
Cohesion: 0.15
Nodes (14): _fake_jagd_weather_get(), _FakeConnection, _ha_sensor_responses(), Fake httpx.get that returns HA state responses for all required entities., Fake httpx.get fuer jagdtag_heute: gibt HA-Zustandsantworten zurueck., _set_ha_env(), _set_jagd_env(), test_jagdtag_heute_db_error_raises() (+6 more)

### Community 35 - "Wettervorhersage Preset"
Cohesion: 0.31
Nodes (8): _degrees_to_compass(), generate(), _get_state(), Any, Wettervorhersage aus HomeAssistant.  Aktuelle Messwerte kommen von der lokalen W, Jagdtag (heute) Preset, Wettervorhersage Preset, Freitext Template

### Community 36 - "Bitmap Text Rendering Helpers"
Cohesion: 0.12
Nodes (16): Preset content script tests (``app/presets/scripts/*`` and ``script_runner``)., _reset_news_token_cache(), _set_mealie_env(), _set_news_env(), test_mealie_recipe_today_formats_recipe(), test_mealie_recipe_today_generate_image_no_recipe_planned_raises(), test_mealie_recipe_today_generate_image_returns_bytes(), test_mealie_recipe_today_generate_image_without_image_raises() (+8 more)

### Community 37 - "Settings API Tests"
Cohesion: 0.23
Nodes (8): _field(), ``GET``/``PUT /api/settings`` - web-configurable preset integration settings., test_list_settings_marks_env_locked_fields(), test_list_settings_masks_secret_values(), test_list_settings_returns_all_web_configurable_fields(), test_put_settings_coerces_int_fields(), test_put_settings_sets_and_clears_an_override(), test_put_settings_with_non_empty_default_overridden_then_cleared()

### Community 38 - "Table API Tests"
Cohesion: 0.26
Nodes (10): _csv_file(), ``/api/table/parse`` endpoint tests., test_parse_csv_empty_returns_400(), test_parse_csv_many_columns_triggers_warning(), test_parse_csv_pipe_in_cell_is_escaped(), test_parse_csv_row_limit_triggers_warning(), test_parse_csv_semicolon_delimiter(), test_parse_csv_simple() (+2 more)

### Community 39 - "HA Integration Manifest"
Cohesion: 0.17
Nodes (11): @olejaeger, codeowners, config_flow, dependencies, documentation, domain, iot_class, issue_tracker (+3 more)

### Community 40 - "Test Queue Worker Stub"
Cohesion: 0.40
Nodes (5): printer_status(), Request, Session, Report printer connectivity and the current queue state., PrinterStatusResponse

### Community 41 - "Job Lookup Errors"
Cohesion: 0.60
Nodes (4): _format_news(), generate(), _get_access_token(), Wichtige Nachrichten aus dem News-Aggregator (https://news.ole-lab.de).  Ruft ``

### Community 43 - "Preset & Template Catalog Docs"
Cohesion: 0.15
Nodes (12): _entry_name(), _entry_sort_key(), generate(), Essenplan der aktuellen Woche aus Mealie (https://mealie.io/), REST-API v1.  Kon, generate(), Offene Positionen der Einkaufsliste aus Mealie (https://mealie.io/), REST-API v1, generate(), Heute faellige, offene Aufgaben aus Super Productivity (WebDAV-Sync).  Liest die (+4 more)

### Community 45 - "Preset Payload Builder"
Cohesion: 0.11
Nodes (18): PrinterCommandError, Raised when the printer rejects/aborts a print job., PrinterClient, Network ESC/POS printer client (V330M, port 9100).  Wraps :class:`escpos.printer, Sends rendered :class:`Document`\\ s to the configured network printer., Render and send ``document``, then close the connection.          :raises Printe, Best-effort connectivity check for ``GET /api/printer/status``., _client_for_port() (+10 more)

### Community 47 - "GitHub Sync & Leak Cleanup"
Cohesion: 0.67
Nodes (3): Gefilterter Snapshot statt Full-Mirror (alte Leak-Commits ausschliessen), Sync to GitHub workflow, Offene manuelle Schritte (GH_PUSH_TOKEN, Repo anlegen)

### Community 48 - "Printer Status Endpoint"
Cohesion: 0.25
Nodes (8): get_icon_renderer(), Icon rendering for the receipt header.  Renders either a glyph from a Font Aweso, Render ``icon_name`` centered on a ``width_px``-wide white canvas.      The resu, render_icon_canvas(), test_icon_renderer_falls_back_to_placeholder_when_assets_missing(), test_icon_renderer_returns_none_for_empty_icon_name(), test_render_icon_canvas_returns_image_for_icon(), test_render_icon_canvas_returns_none_without_icon()

### Community 49 - "Print Preview Endpoint"
Cohesion: 0.09
Nodes (22): Beispiel: `.env` im Projekt-Wurzelverzeichnis, Beispiel: Umgebungsvariablen, Bibliotheks-Referenz, `BondruckerClient`, CLI-Referenz, `encode_image_file`, Exit-Codes, Fehlerbehandlung (+14 more)

### Community 50 - "Templates Listing Endpoint"
Cohesion: 0.11
Nodes (19): Beispiel: `.env` im Projekt-Wurzelverzeichnis, Beispiel: Umgebungsvariablen für die aktuelle Sitzung setzen, Export-BondruckerApiKey, Fehlerbehandlung, Funktionsreferenz, Get-BondruckerHealth, Get-BondruckerIcon, Get-BondruckerJob (+11 more)

### Community 52 - "Custom Icon SVG Endpoint"
Cohesion: 0.29
Nodes (6): get_icon_svg(), list_icons(), Icon listing endpoints (``/api/icons``)., List the icon names available for print jobs.      Includes both Font Awesome ic, Return the raw SVG file for a custom icon (e.g. ``svg-logo``).      Used by the, FileResponse

### Community 53 - "Font Awesome & Icon Licensing"
Cohesion: 0.40
Nodes (4): Fallback-Verhalten, Font Awesome Assets, `icon-map.json` aktualisieren / neu erzeugen, Lizenz

### Community 77 - "test_grid_images.py"
Cohesion: 0.24
Nodes (13): _load_png(), _no_grid_sheet(), Image, Tests for app.presets.grid_images (red-grid cell detection/cropping)., A 100x60 RGBA sheet: two 40x50 cells separated/framed by red lines,     each wit, test_clean_cell_removes_red_and_flattens_transparency(), test_find_cells_detects_both_cells_and_ignores_the_red_grid(), test_find_cells_returns_empty_for_sheet_without_red_grid() (+5 more)

### Community 78 - "Sicherheitskonzept"
Cohesion: 0.14
Nodes (14): Abhängigkeiten, API-Dokumentation (`/docs`, `/redoc`, `/openapi.json`), Ausgehende Verbindungen der Preset-Skripte, Authentifizierung: `X-API-Key`, Bedrohungsmodell / Einsatzkontext, CORS, Datenschutz / Datensparsamkeit, Denial-of-Service / Ressourcenschutz (+6 more)

### Community 79 - "print_preset"
Cohesion: 0.22
Nodes (6): Base, datetime, SQLAlchemy ORM models for the print job queue., Background worker thread that processes the persistent print queue.  The worker, Data-access layer for web-configured Settings overrides (``app_settings``).  See, DeclarativeBase

### Community 80 - "Home Assistant Integration `bondrucker`"
Cohesion: 0.17
Nodes (12): Buttons, Entities, Fehlerbehandlung, Fehlerbehebung, Home Assistant Integration `bondrucker`, Inhalt, Installation, Konfiguration (+4 more)

### Community 81 - "Backend (`backend/app/`)"
Cohesion: 0.18
Nodes (11): `app/api/` – REST-Endpunkte, `app/presets/` – Standarddruckobjekte (Presets), `app/printing/` – Drucker-Anbindung, `app/rendering/` – Rendering-Pipeline, `app/repositories/jobs.py`, `app/repositories/settings.py`, `app/templates/` – Vorlagensystem, Backend (`backend/app/`) (+3 more)

### Community 82 - "Docker & Docker Compose"
Cohesion: 0.18
Nodes (10): `backend`, Backend-Image (`backend/Dockerfile`), `docker-compose.yml`, Docker & Docker Compose, `frontend`, Frontend-Image (`frontend/Dockerfile`), nginx-Konfiguration (`frontend/nginx.conf.template`), Persistenz & Neustarts (+2 more)

### Community 83 - "PresetAttachment"
Cohesion: 0.50
Nodes (4): preview(), PrintJobCreate, Response, Render a print job payload to a PNG preview without enqueueing it.      Uses the

### Community 84 - "Nachricht (message) Template"
Cohesion: 0.20
Nodes (8): generate(), Liefert eine zufaellig ausgewaehlte, aufmunternde Nachricht.  Bewusst ohne Emoji, generate(), Liefert eine zufaellig ausgewaehlte, IT-Spruch zurück.  Bewusst ohne Emojis - di, Positive Nachricht Preset, Grundsätze der IT Preset, WLAN-Zugang Preset, Nachricht (message) Template

### Community 86 - "Bondrucker – Home Assistant Integration"
Cohesion: 0.20
Nodes (9): 1. Dateien kopieren, 2. Home Assistant neu starten, 3. Integration einrichten, Bereitgestellte Entities, Bondrucker – Home Assistant Integration, Fehlerbehebung, Installation (ohne HACS, manuell), Installation über HACS (Custom Repository) (+1 more)

### Community 87 - "printer.py"
Cohesion: 0.36
Nodes (8): _fetch_plug_state(), printer_power(), printer_power_toggle(), Printer endpoints (``/api/printer/…``)., Return the current power state of the printer plug (``switch.plug_016`` by defau, Toggle the printer plug via Home Assistant and return the new power state., _require_ha_config(), PrinterPowerResponse

### Community 88 - "mealie_recipe_today.py"
Cohesion: 0.38
Nodes (9): _entry_sort_key(), _format_ingredient(), _format_recipe(), generate(), generate_image(), Heutiges Rezept aus Mealie (https://mealie.io/), REST-API v1: Bild und Anleitung, _require_settings(), _todays_recipe() (+1 more)

### Community 89 - "Standarddruckobjekte (Presets)"
Cohesion: 0.22
Nodes (9): Ablauf von `POST /api/presets/{key}/print`, Beispiel: neues Preset hinzufügen, Eigene Bild-Skripte schreiben (`attachment.script`), Eigene Inhalts-Skripte schreiben (`content_script`), Eigene, nicht versionierte Presets/Skripte (`custom/`), Motivtafeln mit rotem Raster (`app/presets/grid_images.py`), Standarddruckobjekte (Presets), Vorhandene Skripte als Vorlage (+1 more)

### Community 90 - "Selbstprüfung: Schwachstellen & Verbesserungsvorschläge"
Cohesion: 0.22
Nodes (9): Datenschutz, Erweiterbarkeit, Fazit, Fehlertoleranz, Nicht umgesetzt, aber bewusst außerhalb des Scopes, Selbstprüfung: Schwachstellen & Verbesserungsvorschläge, Sicherheit, Vollständigkeit (+1 more)

### Community 92 - "Datenbankschema"
Cohesion: 0.25
Nodes (8): Datenbankschema, Datenschutz: Inhalte nach erfolgreichem Druck, DDL, ER-Diagramm, FIFO-Auswahl (`fetch_next_runnable`), Migrations-Strategie, Retry-Backoff, Statuswerte (`JobStatus`)

### Community 93 - "OpenAPI Spec (generated)"
Cohesion: 0.25
Nodes (8): OpenAPI Spec (generated), JobStatus-Enum, PresetInfo-Schema, PrinterStatusResponse-Schema, PrintJobCreate-Schema, PrintJobResponse-Schema, SettingFieldInfo-Schema, TemplateInfo-Schema

### Community 94 - "Markdown → ESC/POS Mapping"
Cohesion: 0.29
Nodes (7): Anhänge: Bild-Upload und QR-Code, Degradierte / nicht unterstützte Elemente, Icons, Layout-Parameter pro Vorlage, Limits und Validierung, Markdown → ESC/POS Mapping, Unterstützte Elemente

### Community 96 - "Testkonzept"
Cohesion: 0.29
Nodes (7): Coverage-Lücken (bewusst akzeptiert), Frontend, Manuelle Hardware-Tests (V330M), Test-Doubles (`tests/fakes.py`, `tests/conftest.py`), Testdateien, Testkonzept, Übersicht

### Community 97 - "Bondrucker: Mein Bon-Drucker für Einkaufslisten, Aufgaben und Wetter – open source"
Cohesion: 0.33
Nodes (6): Bondrucker: Mein Bon-Drucker für Einkaufslisten, Aufgaben und Wetter – open source, Die Idee, Vorschläge für Screenshots (vor Veröffentlichung aufnehmen), Warum jetzt open source?, Was die Anwendung macht, Wie es entstanden ist

### Community 98 - "Architektur"
Cohesion: 0.33
Nodes (6): Ablauf: Druckauftrag erstellen und drucken, Ablauf: Neustart während eines aktiven Druckauftrags, Architektur, Datenfluss Markdown → Ausgabe, Komponenten, Überblick

### Community 100 - "Konfiguration in der Web-App"
Cohesion: 0.40
Nodes (5): Editierbare Felder, Konfiguration in der Web-App, Presets registrieren ihre Konfiguration, `PUT /api/settings`, Sperrlogik: ".env gewinnt immer"

### Community 101 - "Release: Vorbereitung GitHub-Veröffentlichung"
Cohesion: 0.40
Nodes (4): Offene manuelle Schritte (nicht durch diesen Commit abgedeckt), Release: Vorbereitung GitHub-Veröffentlichung, Vorschlag für die Commit-Message, Was wurde gemacht

### Community 102 - "Backend-Skripte"
Cohesion: 0.50
Nodes (3): `add_config.py`, Backend-Skripte, `export_openapi.py`

## Knowledge Gaps
- **314 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+309 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **88 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JobRepository` connect `Icon Rendering` to `Table Parsing (CSV/XLSX)`, `Printer Power Control Endpoints`, `Preset Registry & Errors`, `Test Queue Worker Stub`, `Print Queue Worker`, `Job State Transitions`, `Print Jobs REST Endpoints`, `Printer Client Errors & Fakes`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `Document Builder & Image Blocks` to `Preset/Template Loader`, `Table Parsing (CSV/XLSX)`, `Preset Registry & Errors`, `Health & Icon Listing Endpoints`, `Motif Sheet Image Cropping`, `API Error Response Helpers`, `Printer Status Endpoint`, `Settings & App Config Models`, `Jobs API Tests`, `PresetAttachment`, `PNG Preview Renderer`, `Document IR & Markdown Parsing`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `Settings` connect `PNG Preview Renderer` to `Health & Icon Listing Endpoints`, `Document Layout/Text Rendering`, `Preset Payload Builder`, `API Error Response Helpers`, `Document Builder & Image Blocks`, `Settings & App Config Models`, `Print Queue Worker`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `PresetScriptError` (e.g. with `_load_image()` and `_import_script()`) actually correct?**
  _`PresetScriptError` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `get_settings()` (e.g. with `preview()` and `get_engine()`) actually correct?**
  _`get_settings()` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `JobRepository` (e.g. with `cancel_job()` and `create_job()`) actually correct?**
  _`JobRepository` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `PresetConfig` (e.g. with `PresetRegistry` and `PresetInfo`) actually correct?**
  _`PresetConfig` has 14 INFERRED edges - model-reasoned connections that need verification._