# Architektur

## Überblick

Bondrucker besteht aus zwei Containern, die über `docker-compose.yml` miteinander
verbunden sind, sowie einem externen, netzwerkfähigen ESC/POS-Drucker (V330M, 80mm,
TCP-Port 9100).

```mermaid
flowchart LR
    subgraph Client["Browser"]
        UI[React SPA]
    end

    subgraph FE["Frontend-Container (nginx)"]
        Static[Statische Dateien]
        Proxy["Reverse-Proxy /api, /health"]
    end

    subgraph BE["Backend-Container (FastAPI / Uvicorn)"]
        API[REST-API]
        Presets["Preset-Skripte\n(app/presets/scripts/*)"]
        Worker["Queue-Worker (Thread)"]
        Render["Rendering-Pipeline\n(Markdown → IR → ESC/POS / PNG)"]
        DB[(SQLite\nprint_jobs)]
    end

    Printer["V330M Thermodrucker\n(Netzwerk, ESC/POS, Port 9100)"]
    External["Externe Dienste\n(Mealie, Open-Meteo,\nSuper Productivity WebDAV)"]

    UI -->|HTTP| Static
    UI -->|"/api/*, /health"| Proxy
    Proxy -->|HTTP| API

    API -->|"CRUD"| DB
    API -->|build & validate| Render
    API -->|"POST /api/presets/{key}/print"| Presets
    Presets -->|"HTTPS"| External

    Worker -->|"poll FIFO"| DB
    Worker --> Render
    Render -->|"ESC/POS (TCP 9100)"| Printer
    Worker -->|scrub on success| DB
```

## Komponenten

- **Frontend-Container** (`frontend/`): React/TypeScript-SPA, gebaut mit Vite und von
  nginx als statische Dateien ausgeliefert. nginx leitet `/api/*` und `/health` an den
  Backend-Container weiter (siehe [`docker.md`](docker.md)). Aus Sicht des Browsers ist
  alles eine einzige Origin – kein CORS notwendig.
- **Backend-Container** (`backend/`): FastAPI-Anwendung (Uvicorn). Enthält:
  - die **REST-API** (`app/api/*`) für Jobs, Vorschau, Druckerstatus, Vorlagen,
    Standarddruckobjekte und Health-Check,
  - die **Preset-Skripte** (`app/presets/scripts/*`, siehe [`presets.md`](presets.md)),
    die bei `POST /api/presets/{key}/print` synchron im API-Prozess laufen und dabei
    ausgehende HTTPS-Aufrufe an externe Dienste (Mealie, Open-Meteo, Super
    Productivity WebDAV) machen können – im Gegensatz zu allen anderen Endpunkten
    macht die API hier also selbst Verbindungen nach außen, nicht nur der
    Queue-Worker zum Drucker,
  - die **Rendering-Pipeline** (`app/rendering/*`), die Markdown + Vorlage in eine
    druckerunabhängige Zwischendarstellung (`Document`) übersetzt, aus der sowohl
    ESC/POS-Befehle als auch die PNG-Vorschau erzeugt werden,
  - den **Queue-Worker** (`app/printing/worker.py`), einen Hintergrundthread, der die
    persistente Warteschlange abarbeitet und den Drucker über `app/printing/client.py`
    anspricht,
  - die **Datenschicht** (`app/repositories/jobs.py`, `app/database.py`,
    `app/models.py`) auf Basis von SQLite (WAL-Modus, gleichzeitiger Zugriff durch
    API-Threads und Worker-Thread).
- **SQLite-Datenbank**: einzelne Tabelle `print_jobs` (siehe
  [`database-schema.md`](database-schema.md)), als Datei in einem Docker-Volume
  persistiert.
- **V330M-Drucker**: wird ausschließlich vom Queue-Worker über
  `escpos.printer.Network` (TCP, Port 9100) angesprochen. Die API selbst greift nie
  direkt auf den Drucker zu (außer für den reinen Erreichbarkeits-Check in
  `GET /api/printer/status`).

## Ablauf: Druckauftrag erstellen und drucken

```mermaid
sequenceDiagram
    autonumber
    participant FE as Frontend (SPA)
    participant API as Backend-API
    participant DB as SQLite
    participant W as Queue-Worker
    participant P as V330M-Drucker

    FE->>API: POST /api/jobs {template, title, icon, markdown}
    API->>API: build_document() – Vorlage laden,\nMarkdown parsen (eager validation)
    alt ungültige Vorlage / Markdown
        API-->>FE: 400 Bad Request
    else gültig
        API->>DB: INSERT print_jobs (status=queued, payload_json=...)
        API-->>FE: 201 Created {id, status: "queued", ...}
    end

    loop Poll-Schleife (QUEUE_POLL_INTERVAL_SECONDS)
        W->>DB: fetch_next_runnable() – ältester\nqueued/fällige failed-Job (FIFO)
        DB-->>W: Job
        W->>DB: UPDATE status=printing
        W->>W: build_document(payload)
        W->>P: ESC/POS-Befehle (TCP 9100)
        alt Druck erfolgreich
            P-->>W: ok
            W->>DB: UPDATE status=completed,\npayload_json=NULL, error_message=NULL
        else Drucker offline / Fehler
            P-->>W: Fehler / Timeout
            W->>DB: UPDATE status=failed,\nretry_count+=1, next_retry_at=jetzt+backoff
        end
    end
```

## Ablauf: Neustart während eines aktiven Druckauftrags

```mermaid
sequenceDiagram
    autonumber
    participant App as Backend (Lifespan-Startup)
    participant DB as SQLite

    Note over App: Container wurde während eines laufenden\nDruckvorgangs neu gestartet
    App->>DB: SELECT * FROM print_jobs WHERE status='printing'
    DB-->>App: 0..n Jobs (in der Regel max. 1)
    App->>DB: UPDATE status=failed,\nerror_message='Druckvorgang durch Neustart...\nunterbrochen - wird erneut versucht',\nnext_retry_at=jetzt
    Note over App: Jobs werden vom Worker beim nächsten\nPoll-Zyklus regulär (mit Backoff ab Versuch 1)\nerneut versucht
```

## Datenfluss Markdown → Ausgabe

Sowohl der ESC/POS-Renderer als auch die PNG-Vorschau verwenden dieselbe
Zwischendarstellung (`app/rendering/document.py`), wodurch die Vorschau exakt dem
gedruckten Ergebnis entspricht:

```mermaid
flowchart LR
    MD[Markdown-Text] --> Parse["mistune (AST)\napp/rendering/markdown.py"]
    Parse --> IR["Document / Block-IR\napp/rendering/document.py"]
    Tmpl["Vorlage (YAML)\napp/templates/*.yaml"] --> IR
    IR --> Layout["Layout-Engine\n(Umbruch, Tabellen, Einzug)\napp/rendering/layout.py"]
    Layout --> ESC["ESC/POS-Renderer\n→ V330M"]
    Layout --> PNG["PNG-Renderer\n→ POST /api/preview"]
```

Details zur Markdown-Abbildung und zu nicht unterstützten Elementen siehe
[`markdown-mapping.md`](markdown-mapping.md).
