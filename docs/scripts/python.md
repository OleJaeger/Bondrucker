# Python-Client `bondrucker_api`

Benutzerhandbuch für [`scripts/python/bondrucker_api.py`](../../scripts/python/bondrucker_api.py) –
gleichzeitig **Bibliothek** (`BondruckerClient`) und **CLI**, die alle Endpunkte der
Bondrucker REST-API ([`../openapi.yaml`](../openapi.yaml)) abbildet.

## Inhalt

- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Fehlerbehandlung](#fehlerbehandlung)
- [Bibliotheks-Referenz](#bibliotheks-referenz)
  - [`BondruckerClient`](#bondruckerclient)
  - [`encode_image_file`](#encode_image_file)
- [CLI-Referenz](#cli-referenz)
- [Exit-Codes](#exit-codes)

## Voraussetzungen

- Python 3.10 oder neuer (getestet mit 3.11/3.12).
- Paket `requests` (siehe [`requirements.txt`](../../scripts/python/requirements.txt)).
- Netzwerkzugriff auf die Bondrucker-API (Default `https://bondrucker.bondrucker-app.de`, siehe
  [Konfiguration](#konfiguration)).
- Ein gültiger API-Key für alle Endpunkte ausser `GET /health` (siehe
  [`.env.example`](../../.env.example) bzw. [`security.md`](../security.md)).

## Installation

```bash
pip install -r scripts/python/requirements.txt
```

Das Skript ist eine einzelne Datei ohne Paketinstallation – es kann direkt importiert oder
ausgeführt werden:

```bash
python scripts/python/bondrucker_api.py --help
```

## Konfiguration

Basis-URL und API-Key werden in dieser Reihenfolge aufgelöst:

1. Explizite Argumente: `BondruckerClient(base_url=..., api_key=...)` bzw. die
   CLI-Optionen `--url` / `--api-key`.
2. Umgebungsvariablen `BONDRUCKER_API_URL` / `BONDRUCKER_API_KEY`.
3. `.env` im Projekt-Wurzelverzeichnis (`Bondrucker/.env`): `BONDRUCKER_API_URL` /
   `BONDRUCKER_API_KEY`, für den API-Key alternativ das dort bereits vorhandene `API_KEY`
   (derselbe Wert, den der Server im Header `X-API-Key` erwartet).
4. Default für die Basis-URL: `https://bondrucker.bondrucker-app.de`. Für den API-Key gibt es
   ansonsten keinen Default.

### Beispiel: Umgebungsvariablen

```bash
export BONDRUCKER_API_URL=http://localhost:8000
export BONDRUCKER_API_KEY=mein-api-key
```

### Beispiel: `.env` im Projekt-Wurzelverzeichnis

```env
BONDRUCKER_API_URL=http://localhost:8000
API_KEY=mein-api-key
```

(`API_KEY` ist die Variable aus [`.env.example`](../../.env.example), die der Server
selbst verwendet – sie wird hier als Fallback für `BONDRUCKER_API_KEY` wiederverwendet,
sodass für lokale Entwicklung eine einzige `.env` reicht.)

Fehlt der API-Key für einen authentifizierten Aufruf, wird folgender Fehler ausgelöst
(`BondruckerApiError`, `status_code == 0`):

```
Kein API-Key konfiguriert. Setze BONDRUCKER_API_KEY oder API_KEY (z.B. in der .env im
Projekt-Wurzelverzeichnis) oder uebergib --api-key / api_key=...
```

## Fehlerbehandlung

Alle Fehler werden als `BondruckerApiError(RuntimeError)` ausgelöst (Bibliothek) bzw. als
`Fehler: ...` auf `stderr` ausgegeben (CLI, siehe [Exit-Codes](#exit-codes)):

| Attribut | Bedeutung |
|---|---|
| `status_code` | HTTP-Statuscode der Antwort, oder `0` bei einem Verbindungsfehler (kein Response erhalten, z. B. Timeout/DNS). |
| `detail` | Lesbare Fehlermeldung – bei einer JSON-Antwort mit `detail`-Feld dessen Inhalt (String oder JSON-serialisiertes Objekt, siehe `HTTPValidationError` in [`../openapi.yaml`](../openapi.yaml)), sonst der Roh-Text bzw. die `reason`-Phrase. |
| `str(exc)` | `"HTTP <status_code>: <detail>"`, bzw. nur `detail` bei `status_code == 0`. |

```python
from bondrucker_api import BondruckerClient, BondruckerApiError

client = BondruckerClient()
try:
    client.create_job(template="todo", markdown="- [ ] Punkt 1")
except BondruckerApiError as exc:
    print(f"Druckauftrag fehlgeschlagen ({exc.status_code}): {exc.detail}")
```

Beispiel für eine Fehlermeldung bei ungültigem API-Key:

```
HTTP 401: Invalid or missing API key
```

## Bibliotheks-Referenz

```python
from bondrucker_api import BondruckerClient, BondruckerApiError, encode_image_file

client = BondruckerClient()
print(client.list_templates())

job = client.create_job(
    template="todo",
    title="Einkaufsliste",
    icon="fa-cart-shopping",
    markdown="- [ ] Milch\n- [x] Brot",
)
print(job["id"], job["status"])
```

### `BondruckerClient`

```python
BondruckerClient(base_url: str | None = None, api_key: str | None = None, timeout: float = 30.0)
```

`base_url` und `api_key` werden, falls nicht angegeben, gemäß [Konfiguration](#konfiguration)
aufgelöst. `timeout` ist der Request-Timeout in Sekunden (Default `30.0`).

| Methode | HTTP | Rückgabe | Beschreibung |
|---|---|---|---|
| `health()` | `GET /health` | `dict` | Liveness-Check, **ohne** API-Key. |
| `list_templates()` | `GET /api/templates` | `list[dict]` | Konfigurierte Vorlagen (`key`, `name`, `type`, `icon`). |
| `list_icons()` | `GET /api/icons` | `list[str]` | Verfügbare Font-Awesome-Icon-Namen. |
| `printer_status()` | `GET /api/printer/status` | `dict` | `online`, `queue_length`, `current_job`. |
| `list_jobs(status=None)` | `GET /api/jobs[?status=...]` | `list[dict]` | Druckaufträge auflisten, optional gefiltert nach `status` (`queued`/`printing`/`failed`/`completed`/`cancelled`). |
| `get_job(job_id)` | `GET /api/jobs/{job_id}` | `dict` | Einzelnen Auftrag abrufen. |
| `create_job(template, *, title="", icon=None, markdown="", print_timestamp=True, image_base64=None, qr_code=None)` | `POST /api/jobs` | `dict` | Neuen Auftrag anlegen und einreihen (Status zunächst `queued`). |
| `cancel_job(job_id)` | `DELETE /api/jobs/{job_id}` | `dict` | Auftrag abbrechen (nur `queued`/`failed`); liefert den aktualisierten Auftrag (`cancelled`). |
| `preview(template, *, title="", icon=None, markdown="", print_timestamp=True, image_base64=None, qr_code=None)` | `POST /api/preview` | `bytes` | PNG-Vorschau, **ohne** Auftrag anzulegen. Gibt die rohen PNG-Bytes zurück. |

`create_job` und `preview` nehmen identische Schlüsselwortargumente entgegen
(`_build_job_payload`):

- `image_base64` und `qr_code` sind **exklusiv** – werden beide übergeben, wirft die
  Methode ein `ValueError`:

  ```
  image_base64 und qr_code sind exklusiv - nur eines von beiden angeben.
  ```

- `image_base64` (Base64, optional als `data:`-URL) ist auf 7.000.000 Zeichen begrenzt
  (~5 MB binär), `qr_code` auf 2.000 Zeichen (siehe `PrintJobCreate` in
  [`../openapi.yaml`](../openapi.yaml)). Für `image_base64` kann
  [`encode_image_file`](#encode_image_file) genutzt werden.
- `title`, `icon`, `markdown`, `image_base64` und `qr_code` werden nur in den
  Request-Body übernommen, wenn sie nicht leer bzw. nicht `None` sind – `template` und
  `print_timestamp` werden immer gesendet.

Im Gegensatz zum [PowerShell-Modul](powershell.md#new-bondruckerjob) gibt es **kein**
`markdown_file`-Argument auf Bibliotheksebene – das Lesen einer Datei (`--markdown-file`
in der CLI) erfolgt vor dem Aufruf, der Inhalt wird als `markdown`-String übergeben.

### `encode_image_file`

```python
encode_image_file(path: str | Path) -> str
```

Liest eine Bilddatei und gibt eine base64-kodierte `data:`-URL zurück (MIME-Type wird aus
der Dateiendung via `mimetypes` ermittelt, Fallback `application/octet-stream`), geeignet
für `image_base64`:

```python
job = client.create_job(
    template="freitext",
    title="Foto",
    image_base64=encode_image_file("foto.png"),
)
```

## CLI-Referenz

```
python bondrucker_api.py [-h] [--url URL] [--api-key API_KEY] [--timeout TIMEOUT]
                          {health,templates,icons,printer-status,jobs,preview} ...
```

**Globale Optionen** (vor dem Subcommand):

| Option | Beschreibung |
|---|---|
| `--url URL` | Basis-URL der API (Default: `BONDRUCKER_API_URL` / `.env` / `https://bondrucker.bondrucker-app.de`). |
| `--api-key API_KEY` | API-Key (Default: `BONDRUCKER_API_KEY` / `API_KEY` aus der `.env`). |
| `--timeout TIMEOUT` | Timeout in Sekunden für HTTP-Requests (Default: `30`). |

Ergebnisse werden – ausser bei `preview` – als JSON (`json.dumps(..., indent=2, ensure_ascii=False)`)
auf `stdout` ausgegeben.

### `health`

`GET /health`, ohne API-Key.

```bash
python bondrucker_api.py health
```

```json
{
  "status": "ok"
}
```

### `templates`

`GET /api/templates` – konfigurierte Druckvorlagen auflisten.

```bash
python bondrucker_api.py templates
```

### `icons`

`GET /api/icons` – verfügbare Font-Awesome-Icon-Namen auflisten.

```bash
python bondrucker_api.py icons
```

### `printer-status`

`GET /api/printer/status` – Drucker-Konnektivität und Warteschlange.

```bash
python bondrucker_api.py printer-status
```

### `jobs list`

`GET /api/jobs[?status=...]` – Druckaufträge auflisten.

```bash
python bondrucker_api.py jobs list
python bondrucker_api.py jobs list --status queued
```

`--status` akzeptiert `queued`, `printing`, `failed`, `completed`, `cancelled`.

### `jobs get`

`GET /api/jobs/{job_id}` – einzelnen Druckauftrag abrufen.

```bash
python bondrucker_api.py jobs get <job_id>
```

### `jobs create`

`POST /api/jobs` – neuen Druckauftrag anlegen und einreihen.

```
python bondrucker_api.py jobs create --template TEMPLATE [--title TITLE] [--icon ICON]
    [--markdown MARKDOWN | --markdown-file PATH] [--no-timestamp]
    [--image PATH | --qr-code QR_CODE]
```

| Option | Beschreibung |
|---|---|
| `--template TEMPLATE` | **Pflicht.** Key einer konfigurierten Vorlage, z. B. `todo`. |
| `--title TITLE` | Titel des Druckauftrags. |
| `--icon ICON` | Font-Awesome-Icon-Name, z. B. `fa-cart-shopping`. |
| `--markdown MARKDOWN` | Markdown-Inhalt als Text. Exklusiv zu `--markdown-file`. |
| `--markdown-file PATH` | Datei, deren Inhalt als Markdown gesendet wird. Exklusiv zu `--markdown`. |
| `--no-timestamp` | Zeitstempel unten rechts **nicht** drucken (Default: drucken). |
| `--image PATH` | Bilddatei, wird base64-kodiert als `image_base64` gesendet. Exklusiv zu `--qr-code`. |
| `--qr-code QR_CODE` | Inhalt für QR-Code (URL, WLAN, vCard, `geo:...`, ...). Exklusiv zu `--image`. |

`--markdown`/`--markdown-file` sowie `--image`/`--qr-code` sind jeweils als
`argparse`-`mutually_exclusive_group` definiert – werden beide einer Gruppe angegeben,
bricht `argparse` mit Exit-Code `2` ab.

**Beispiele**

```bash
python bondrucker_api.py jobs create --template todo --title Einkaufsliste \
    --markdown "- [ ] Milch\n- [x] Brot" --icon fa-cart-shopping

python bondrucker_api.py jobs create --template freitext --title WLAN \
    --qr-code 'WIFI:T:WPA;S:MeinNetz;P:geheim;;'
```

### `jobs cancel`

`DELETE /api/jobs/{job_id}` – Druckauftrag abbrechen (nur Status `queued` oder `failed`).

```bash
python bondrucker_api.py jobs cancel <job_id>
```

### `preview`

`POST /api/preview` – rendert dieselbe Eingabe wie `jobs create` als PNG-Vorschau, ohne
einen Druckauftrag anzulegen.

```
python bondrucker_api.py preview --template TEMPLATE [--title TITLE] [--icon ICON]
    [--markdown MARKDOWN | --markdown-file PATH] [--no-timestamp]
    [--image PATH | --qr-code QR_CODE] [-o PATH]
```

Nimmt dieselben Inhalts-Optionen wie [`jobs create`](#jobs-create) entgegen, zusätzlich:

| Option | Beschreibung |
|---|---|
| `-o PATH`, `--output PATH` | Zieldatei für die PNG-Vorschau (Default: `preview.png`). |

```bash
python bondrucker_api.py preview --template freitext --markdown "# Test" -o preview.png
```

```
Vorschau gespeichert: preview.png (1234 Bytes)
```

## Exit-Codes

| Code | Bedeutung |
|---|---|
| `0` | Erfolg. |
| `1` | `BondruckerApiError` (z. B. HTTP-Fehler, Verbindungsfehler, fehlender API-Key), `ValueError` (z. B. `image_base64`/`qr_code` gleichzeitig angegeben) oder `OSError` (z. B. Datei für `--markdown-file`/`--image` nicht lesbar). Meldung wird als `Fehler: ...` auf `stderr` ausgegeben. |
| `2` | Ungültige CLI-Argumente (von `argparse` ausgelöst, z. B. fehlendes `--template`, unbekannter Subcommand, gleichzeitige Angabe sich ausschliessender Optionen). |
