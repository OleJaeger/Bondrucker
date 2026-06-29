# Docker & Docker Compose

## Überblick

```
docker-compose.yml
├── backend   (Port 8000)   FastAPI/Uvicorn, SQLite, Queue-Worker
└── frontend  (Port 5173→80) nginx: statische SPA + Reverse-Proxy auf backend
```

```bash
cp .env.example .env
# .env anpassen: API_KEY, PRINTER_HOST, PRINTER_PORT, ...
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend (direkt, z. B. für `/docs`): `http://localhost:8000`
- Health-Check (kein API-Key): `http://localhost:8000/health`

## Backend-Image (`backend/Dockerfile`)

- Basis: `python:3.12-slim`.
- `libjpeg62-turbo` + `zlib1g` werden installiert (Laufzeitabhängigkeiten von
  Pillow für PNG/Icon-Rendering).
- `pip install -r requirements.txt`, dann werden `app/`, `config/`, `assets/`
  in das Image kopiert.
- `/data` und `/app/logs` werden im Image angelegt, damit die Anwendung auch ohne
  gemountete Volumes (z. B. `docker run` ohne Compose) schreiben kann.
- `ENV`-Defaults setzen `DB_PATH`, `TEMPLATES_DIR`, `LOG_DIR` und die
  Font-Awesome-Pfade passend zu den Volume-Mountpoints in `docker-compose.yml`.
- `HEALTHCHECK` ruft `GET /health` über `urllib` auf (kein zusätzliches Tool im
  Image nötig).
- Startkommando: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

## Frontend-Image (`frontend/Dockerfile`)

Mehrstufiger Build:

1. **Build-Stage** (`node:22-alpine`): `npm ci`, dann `npm run build`
   (`tsc -b && vite build`) → `dist/`.
2. **Runtime-Stage** (`nginx:1.27-alpine`): kopiert `dist/` nach
   `/usr/share/nginx/html` und ein nginx-**Template**
   (`frontend/nginx.conf.template`) nach `/etc/nginx/templates/default.conf.template`.

Das offizielle nginx-Image führt beim Start `envsubst` über alle Dateien in
`/etc/nginx/templates/*.template` aus und schreibt das Ergebnis nach
`/etc/nginx/conf.d/`. Dabei wird `${BACKEND_URL}` durch die Umgebungsvariable
`BACKEND_URL` des Containers ersetzt (Default im Dockerfile:
`http://backend:8000`, in `docker-compose.yml` über `${BACKEND_URL:-...}` aus
`.env` überschreibbar). nginx-eigene Variablen (`$host`, `$remote_addr`, `$scheme`,
`$uri`, ...) bleiben unverändert, da `envsubst` nur für tatsächlich gesetzte
Container-Umgebungsvariablen ersetzt.

### nginx-Konfiguration (`frontend/nginx.conf.template`)

| Pfad | Verhalten |
|---|---|
| `/api/` | Reverse-Proxy → `${BACKEND_URL}/api/` (inkl. `X-Forwarded-*`-Header). |
| `/health` | Reverse-Proxy → `${BACKEND_URL}/health`. |
| `/assets/` | Lange Cache-Lebensdauer (`max-age=1y, immutable`) – Vite hängt Inhalts-Hashes an Dateinamen an. |
| `/` (alles andere) | `try_files $uri $uri/ /index.html` – SPA-Fallback für React-Router. |

Aus Sicht des Browsers ist alles eine einzige Origin (`http://<host>:5173`), daher
ist **kein CORS** zwischen Frontend und Backend erforderlich, wenn die Anwendung
über Compose betrieben wird.

`HEALTHCHECK` ruft `GET /` über `wget` ab (in `nginx:alpine` enthalten).

## `docker-compose.yml`

### `backend`

- `env_file: .env` – sämtliche Variablen aus `.env.example` werden 1:1 an den
  Container weitergegeben (Settings, Drucker, Layout, Storage, Icons, Queue, CORS).
- Volumes (Bind-Mounts, relativ zum Repo):
  | Host-Pfad | Container-Pfad | Zweck |
  |---|---|---|
  | `./backend/data` | `/data` | SQLite-Datenbankdatei – persistiert über Neustarts/Updates. |
  | `./backend/logs` | `/app/logs` | Rotierende Logdateien. |
  | `./backend/config/templates` | `/app/config/templates` (read-only) | Vorlagen-YAML – direkt im Repo editierbar, ohne Image-Rebuild. |
  | `./backend/assets/fontawesome` | `/app/assets/fontawesome` (read-only) | Font-Awesome-Webfont + Icon-Map (im Repo enthalten, vom Betreiber überschreibbar). |
- `ports: 8000:8000` – ermöglicht direkten API-Zugriff (z. B. Swagger UI unter
  `/docs`, sofern `DOCS_ENABLED=true`).

Bind-Mounts statt benannter Volumes wurden für `config/templates` und
`assets/fontawesome` bewusst gewählt: beide Verzeichnisse sollen vom Betreiber
direkt im Checkout editiert werden (neue Vorlage hinzufügen, Font-Datei ablegen),
ohne in einen Container oder ein Docker-Volume wechseln zu müssen. `data/` und
`logs/` sind aus demselben Grund Bind-Mounts (einfacher Zugriff/Backup), enthalten
aber laufzeitgenerierte Dateien und sind per `.gitignore` ausgeschlossen.

### `frontend`

- `environment: BACKEND_URL` – Default `http://backend:8000` (Compose-internes
  DNS, Servicename `backend`), override über `.env`.
- `environment: API_KEY` – derselbe Wert wie beim `backend`-Service, aus `.env`.
  nginx setzt damit `X-API-Key` auf proxied `/api/`-Requests, siehe
  [`security.md`](security.md). Pflichtfeld, kein Default – fehlt die Variable,
  startet der nginx-Container nicht (`envsubst` lässt `${API_KEY}` sonst als
  ungültige nginx-Variable im Config-File stehen).
- `ports: 5173:80`.
- `depends_on: backend: condition: service_healthy` – startet erst, wenn der
  Backend-`HEALTHCHECK` erfolgreich war.

## Persistenz & Neustarts

- Die SQLite-Datei in `./backend/data` überlebt `docker compose down` /
  `docker compose up` sowie Image-Updates (solange das Volume nicht entfernt wird).
- Wird der Backend-Container während eines aktiven Druckauftrags (`status=printing`)
  beendet, markiert `recover_interrupted_jobs()` diesen Job beim nächsten Start als
  `failed` mit `next_retry_at=jetzt`, sodass er regulär (mit Backoff) erneut
  versucht wird – siehe [`architecture.md`](architecture.md).
- `docker compose down -v` entfernt **keine** Bind-Mounts (das sind reguläre
  Verzeichnisse im Checkout) – zum vollständigen Zurücksetzen müssen
  `backend/data/*.db*` manuell gelöscht werden.

## Produktionsbetrieb

- `API_KEY` **muss** vor dem ersten Start in `.env` auf einen langen,
  zufälligen Wert gesetzt werden (siehe [`security.md`](security.md)).
- `DOCS_ENABLED=false` setzen, um `/docs`, `/redoc` und `/openapi.json`
  vollständig zu deaktivieren.
- Beide Container exponieren HTTP (kein TLS). Für einen Internet- oder
  WLAN-übergreifenden Zugriff sollte ein TLS-terminierender Reverse-Proxy (z. B.
  Traefik/Caddy/nginx) vorgeschaltet werden – siehe [`security.md`](security.md).
- `PRINTER_HOST`/`PRINTER_PORT` müssen aus dem Backend-Container heraus erreichbar
  sein (gleiches Netzwerk bzw. Routing zum Drucker-Subnetz).
