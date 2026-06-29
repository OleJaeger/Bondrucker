# Scripts: API-Clients

Zwei schlanke Clients für die Bondrucker REST-API ([`../openapi.yaml`](../openapi.yaml)) –
gedacht für die interaktive Nutzung (PowerShell-Konsole bzw. Shell/Automatisierung) und als
Vorlage für eigene Integrationen.

| Client | Quelldatei | Benutzerhandbuch |
|---|---|---|
| PowerShell-Modul | [`scripts/powershell/Bondrucker.psm1`](../../scripts/powershell/Bondrucker.psm1) (Manifest [`Bondrucker.psd1`](../../scripts/powershell/Bondrucker.psd1)) | [`powershell.md`](powershell.md) |
| Python-Bibliothek + CLI | [`scripts/python/bondrucker_api.py`](../../scripts/python/bondrucker_api.py) | [`python.md`](python.md) |
| Home Assistant Integration | [`scripts/homeassistant/custom_components/bondrucker/`](../../scripts/homeassistant/custom_components/bondrucker/) | [`homeassistant.md`](homeassistant.md) |

Beide Clients bilden dieselben Endpunkte ab: `/health`, `/api/templates`, `/api/icons`,
`/api/printer/status`, `/api/jobs` (Liste/Abruf/Anlegen/Abbrechen) und `/api/preview`. Für
die genaue Bedeutung der Felder (z. B. `markdown`, `image_base64`, `qr_code`,
`print_timestamp`, Größenlimits, Fehlerformate) ist [`../openapi.yaml`](../openapi.yaml)
die maßgebliche Referenz – diese Dokumente beschreiben nur die jeweilige
Client-Oberfläche.

## Gemeinsame Konfiguration

Beide Clients lösen Basis-URL und API-Key in derselben Reihenfolge auf:

1. **Explizite Angabe** an der jeweiligen Funktion/Methode bzw. CLI-Option
   (`-BaseUrl`/`-ApiKey` in PowerShell, `--url`/`--api-key` bzw.
   `BondruckerClient(base_url=..., api_key=...)` in Python).
2. **Umgebungsvariablen** `BONDRUCKER_API_URL` / `BONDRUCKER_API_KEY`.
3. **`.env` im Projekt-Wurzelverzeichnis** (`Bondrucker/.env`, also eine Ebene über
   `scripts/`): `BONDRUCKER_API_URL` / `BONDRUCKER_API_KEY`, für den API-Key
   alternativ das dort ohnehin vorhandene `API_KEY` – derselbe Wert, den der Server von
   Clients im Header `X-API-Key` erwartet (siehe [`../../.env.example`](../../.env.example)).
4. **Nur PowerShell**: ein per `Export-BondruckerApiKey` verschlüsselt abgelegter Key
   (siehe [`powershell.md`](powershell.md#export-bondruckerapikey)).
5. **Default für die Basis-URL**: `https://bondrucker.bondrucker-app.de`. Für den API-Key gibt es
   sonst keinen Default – er muss über eine der obigen Quellen gesetzt werden (ausser für
   `GET /health`, das keine Authentifizierung benötigt).

Details, alle Funktionen/Befehle und Beispiele siehe [`powershell.md`](powershell.md) bzw.
[`python.md`](python.md).
