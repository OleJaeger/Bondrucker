# Sicherheitskonzept

## Bedrohungsmodell / Einsatzkontext

Bondrucker ist für den Betrieb im **lokalen Netzwerk** (z. B. Heim-/Büronetz)
konzipiert: ein Backend-Container, ein Frontend-Container und ein
ESC/POS-Netzwerkdrucker im selben Subnetz. Es wird **kein** öffentlicher
Internetzugriff vorausgesetzt. Die wichtigsten Schutzziele:

1. Nur autorisierte Clients dürfen Druckaufträge erstellen, einsehen oder
   abbrechen (**Vertraulichkeit/Integrität der Warteschlange**).
2. Inhalte abgeschlossener Druckaufträge dürfen nicht dauerhaft gespeichert
   bleiben (**Datensparsamkeit/Privacy-by-Design**).
3. Ein einzelner fehlerhafter/böswilliger Auftrag darf weder die Anwendung noch
   den Drucker dauerhaft blockieren (**Verfügbarkeit**).

## Authentifizierung: `X-API-Key`

- Alle Endpunkte außer `GET /health` sind über die Dependency
  `require_api_key` (`app/security.py`) geschützt.
- Der erwartete Wert kommt aus der Umgebungsvariable `API_KEY` (Pflichtfeld in
  `Settings`, kein Default – die Anwendung startet ohne gesetzten `API_KEY` nicht).
- Vergleich über `secrets.compare_digest()` (zeitkonstant, verhindert
  Timing-Seitenkanäle beim Erraten des Schlüssels).
- Fehlender/falscher Schlüssel → `401 Unauthorized` mit
  `WWW-Authenticate: ApiKey`.
- Die Dependency ist als `fastapi.security.APIKeyHeader` deklariert, wodurch
  Swagger UI (`/docs`) automatisch einen "Authorize"-Dialog für alle geschützten
  Routen anzeigt.
- Es gibt **eine** gemeinsame Schlüssel-Stufe (kein rollenbasiertes Modell) – für
  den Single-Tenant-/Heimnetz-Einsatzzweck ausreichend.

### `X-API-Key` im Frontend

- Browser kennen den `API_KEY` **nicht**: `frontend/src/api/client.ts` sendet
  keinen `X-API-Key`-Header.
- Stattdessen setzt die nginx der Frontend-Anwendung (`frontend/nginx.conf.template`)
  den Header beim Reverse-Proxy von `/api/` selbst, basierend auf der
  Container-Umgebungsvariable `API_KEY` (gleicher Wert wie beim Backend, per
  `envsubst` eingesetzt).
- Das ist sicher, weil der Frontend-Container per Traefik-Middleware durch
  **Authentik** geschützt ist (`authentik-forwardauth`, siehe `docker-compose.yml`):
  nur bereits SSO-authentifizierte Nutzer erreichen die nginx und damit
  transitiv den `X-API-Key`. Der Backend-Endpunkt selbst (eigene Traefik-Route
  `BONDRUCKER_BACKEND_URL`, **ohne** Authentik-Middleware) bleibt zusätzlich
  durch `require_api_key` geschützt – die Defense-in-Depth-Ebene für direkten
  Zugriff (z. B. PowerShell-/Python-Skripte) bleibt also erhalten.
- Für die lokale Entwicklung ohne Docker (`npm run dev`) übernimmt der
  Vite-Dev-Proxy (`frontend/vite.config.ts`) dieselbe Aufgabe, basierend auf
  `API_KEY` in `frontend/.env` (siehe `frontend/.env.example`).

### Empfehlungen für den Betrieb

- `API_KEY` muss vor dem ersten Start auf einen langen, zufälligen Wert gesetzt
  werden, z. B.:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- `.env` darf nicht ins Repository/Backup ohne Zugriffsschutz gelangen (per
  `.gitignore` bereits ausgeschlossen).
- Derselbe `API_KEY`-Wert muss sowohl dem `backend`- als auch dem
  `frontend`-Service übergeben werden (siehe `docker-compose.yml`) – sonst
  schlägt entweder der nginx-Start fehl (`API_KEY` fehlt komplett) oder alle
  `/api/`-Aufrufe über die Web-UI liefern `401`.

## Transportsicherheit (TLS)

Backend und Frontend sprechen intern **HTTP** (kein TLS). Für ein internes,
vertrauenswürdiges Netzwerk ist das ein akzeptabler Kompromiss gegenüber der
zusätzlichen Zertifikatsverwaltung. Soll die Anwendung aus einem weniger
vertrauenswürdigen Netzwerk (z. B. Gäste-WLAN, VPN-Einwahl) erreichbar sein,
**muss** ein TLS-terminierender Reverse-Proxy (Caddy, Traefik, nginx mit
Zertifikat) vorgeschaltet werden – siehe [`docker.md`](docker.md). Der API-Key
wird sonst im Klartext übertragen.

## API-Dokumentation (`/docs`, `/redoc`, `/openapi.json`)

- Über `DOCS_ENABLED` (Default `true`) steuerbar. Bei `false` werden alle drei
  Routen vollständig deaktiviert (`docs_url=None` etc. in `main.py`), nicht nur
  versteckt.
- Auch wenn aktiviert, sind die zugrunde liegenden Endpunkte weiterhin durch
  `X-API-Key` geschützt (Swagger UI fragt den Schlüssel ab). Für
  produktionsnahe Deployments wird trotzdem empfohlen, `DOCS_ENABLED=false` zu
  setzen oder `/docs`/`/redoc`/`/openapi.json` zusätzlich am Reverse-Proxy zu
  blocken, um die API-Struktur nicht unnötig offenzulegen.

## CORS

- `CORS_ORIGINS` (kommagetrennte Liste, Default leer = keine Cross-Origin-Zugriffe
  erlaubt) steuert `CORSMiddleware`.
- Im regulären Compose-Betrieb ist CORS **nicht** erforderlich: der Browser sieht
  nur die nginx-Origin, die `/api`/`/health` serverseitig weiterleitet (siehe
  [`docker.md`](docker.md)).
- Relevant nur für lokale Entwicklung ohne nginx (Vite-Dev-Server auf einem
  anderen Port) oder wenn ein separates Tool die API direkt von einer anderen
  Origin aus aufruft. `allow_credentials=False`, da Authentifizierung über einen
  Header (kein Cookie) erfolgt.

## Eingabevalidierung

- `PrintJobCreate` (Pydantic) validiert Typen/Pflichtfelder.
- `template` muss eine in `TEMPLATES_DIR` konfigurierte Vorlage referenzieren
  (`TemplateNotFoundError` → `400`).
- `markdown` wird **vor** dem Einreihen geparst (`build_document` in
  `POST /api/jobs` und `POST /api/preview`); unparsbares oder zu langes Markdown
  (> 50.000 Zeichen) → `InvalidMarkdownError` → `400`. Damit kann kein Job mit
  garantiert fehlschlagendem Inhalt in die Warteschlange gelangen.
- Ungültige Vorlagen-YAML-Dateien werden beim Laden übersprungen und geloggt,
  bringen die Anwendung aber nicht zum Absturz (`TemplateRegistry.reload`).
- Fehlende/defekte Font-Awesome-Assets degradieren zu einem Platzhalter-Icon
  (`IconRenderer`), führen nie zu einem Druckfehler.

## Datenschutz / Datensparsamkeit

Siehe [`database-schema.md`](database-schema.md) für die genauen Feldänderungen.
Kurzfassung:

- Nach **erfolgreichem** Druck (`status=completed`) werden `payload_json`
  (`template`, `title`, `icon`, `markdown`) und `error_message` aus der
  Datenbank gelöscht. Es verbleiben nur `id`, `status`, `created_at`,
  `updated_at`, `completed_at`, `retry_count`.
- Für `queued`/`printing`/`failed`/`cancelled` bleiben Inhalt und ggf.
  Fehlermeldung erhalten (notwendig für Anzeige, Retry, Abbruch).
- Es gibt **keine** zusätzliche Tabelle/Log-Datei mit dauerhaftem Klartext
  gedruckter Inhalte.
- **Logging**: Das Backend loggt Job-IDs, Statusübergänge und
  Fehlermeldungen (z. B. "Drucker nicht erreichbar"), aber **niemals** den
  Inhalt (`title`/`markdown`/`icon`) eines Jobs (siehe `app/printing/worker.py`).
  Logdateien (`backend/logs/app.log*`, rotierend, 5 Dateien × 5 MB) enthalten
  daher keine Druckinhalte.
- Die SQLite-Datei (`backend/data/app.db`) sollte trotzdem wie jeder Datenträger
  mit potenziell sensiblen Inhalten (Notizen, Einkaufslisten, ...) behandelt
  werden, solange Jobs sich im Status `queued`/`failed` befinden.

## Netzwerkzugriff auf den Drucker

- Ausschließlich der **Queue-Worker** (Hintergrundthread im Backend) öffnet
  TCP-Verbindungen zum Drucker (`PRINTER_HOST:PRINTER_PORT`).
  `GET /api/printer/status` nutzt denselben Client lediglich für einen
  Connect/Disconnect-Test (`is_online()`), sendet keine Druckdaten.
- Der V330M-Drucker selbst bietet auf ESC/POS-Netzwerkports i. d. R. keine
  Authentifizierung – jeder Host im selben Netzwerk könnte direkt drucken.
  Bondrucker kann dieses Risiko nicht beseitigen, reduziert es aber, indem es
  als kontrollierter, authentifizierter Zugangspunkt fungiert. Eine
  Netzwerksegmentierung (Drucker in einem eigenen VLAN, das nur vom
  Backend-Host erreichbar ist) wird empfohlen.

## Ausgehende Verbindungen der Preset-Skripte

- `POST /api/presets/{key}/print` kann – abhängig vom konfigurierten
  `content_script` (siehe [`presets.md`](presets.md)) – **synchron im
  API-Prozess** ausgehende Anfragen an externe Dienste auslösen:
  HTTPS an Mealie (`MEALIE_BASE_URL`), Open-Meteo (`api.open-meteo.com`) und
  die WebDAV-Sync von Super Productivity (`SP_WEBDAV_URL`), sowie eine
  PostgreSQL-Verbindung zur Jagdzeiten-Datenbank (`JAGD_DB_HOST`/
  `JAGD_DB_PORT`, `jagdtag_heute.py`). Dies ist die einzige Stelle, an der das
  Backend selbst (statt nur des Queue-Workers) Verbindungen zu Hosts außerhalb
  des Containers aufbaut.
- Anmeldedaten für diese Dienste (`MEALIE_API_TOKEN`, `SP_WEBDAV_USERNAME`/
  `SP_WEBDAV_PASSWORD`, `JAGD_DB_USER`/`JAGD_DB_PASSWORD`) werden ausschließlich
  aus Umgebungsvariablen gelesen (`app/config.py`) und nicht protokolliert. Ist
  ein Dienst nicht konfiguriert, liefert das jeweilige Skript einen
  `PresetScriptError` (`502`), **ohne** einen Druckauftrag anzulegen.
- Open-Meteo erfordert keinen API-Key; es werden lediglich die in
  `WEATHER_LATITUDE`/`WEATHER_LONGITUDE` konfigurierten Koordinaten übertragen.
- Da diese Aufrufe synchron im Request-Handler erfolgen, hängt die
  Antwortzeit von `POST /api/presets/{key}/print` von der Erreichbarkeit und
  Latenz des jeweiligen externen Dienstes ab. Ein nicht erreichbarer Dienst
  führt zu `502`, blockiert aber nicht die Warteschlange oder andere
  Endpunkte.

## Denial-of-Service / Ressourcenschutz

- Markdown-Längenlimit (50.000 Zeichen) verhindert pathologische
  Rendering-/Layout-Laufzeiten.
- Die Warteschlange ist unbegrenzt groß (SQLite) – ein Client mit gültigem
  API-Key könnte beliebig viele Jobs einreihen. Da der API-Key bereits den
  Zugriff auf einen vertrauenswürdigen Nutzerkreis beschränkt, wird dies als
  akzeptables Risiko bewertet; siehe [`self-review.md`](self-review.md) für eine
  mögliche Erweiterung (Rate-Limiting, Queue-Obergrenze).
- Unbegrenzte Retries bei dauerhaft offline Drucker erzeugen keine wachsende
  Datenmenge (ein Job bleibt ein Datensatz, nur `retry_count`/`error_message`
  werden aktualisiert) und keinen unbegrenzten Netzwerkverkehr (Backoff bis
  `RETRY_MAX_DELAY_SECONDS`).

## Abhängigkeiten

- Python-Abhängigkeiten sind in `requirements.txt`/`requirements-dev.txt` mit
  Versionsangaben gepinnt; Frontend-Abhängigkeiten in `package-lock.json`.
  Regelmäßige Updates (`pip list --outdated`, `npm outdated`/`npm audit`) werden
  empfohlen, sind aber nicht automatisiert (siehe
  [`self-review.md`](self-review.md)).
