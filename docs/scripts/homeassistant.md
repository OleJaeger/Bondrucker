# Home Assistant Integration `bondrucker`

Benutzerhandbuch für die Custom Component unter
[`scripts/homeassistant/custom_components/bondrucker/`](../../scripts/homeassistant/custom_components/bondrucker/) –
eine lokale Home Assistant Integration, die eine laufende Bondrucker-Instanz anbindet und
Sensoren sowie Buttons als Entities bereitstellt.

## Inhalt

- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
  - [Manuell (ohne HACS)](#manuell-ohne-hacs)
  - [Über HACS (Custom Repository)](#über-hacs-custom-repository)
- [Konfiguration](#konfiguration)
- [Entities](#entities)
  - [Sensoren](#sensoren)
  - [Buttons](#buttons)
- [Fehlerbehandlung](#fehlerbehandlung)
- [Fehlerbehebung](#fehlerbehebung)

## Voraussetzungen

- **Home Assistant 2023.1.0 oder neuer** (definiert in [`hacs.json`](../../scripts/homeassistant/hacs.json)).
- Bondrucker läuft und ist aus Home Assistant erreichbar (z. B. `http://192.168.1.100:8000`).
- Ein gültiger API-Key aus der Bondrucker `.env`-Datei (`API_KEY=...`, siehe
  [`.env.example`](../../.env.example) bzw. [`security.md`](../security.md)).

## Installation

### Manuell (ohne HACS)

**1. Dateien kopieren**

Kopiere den Ordner `custom_components/bondrucker` in das `custom_components`-Verzeichnis deiner
Home Assistant-Konfiguration:

```
<config>/
└── custom_components/
    └── bondrucker/
        ├── __init__.py
        ├── button.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── manifest.json
        ├── sensor.py
        ├── strings.json
        └── translations/
            ├── de.json
            └── en.json
```

Wo liegt `<config>`?

| Installationsart | Pfad |
|---|---|
| Home Assistant OS / Supervised | `/config/` (per Samba-Share oder SSH erreichbar) |
| Docker (`docker run`) | Der als `-v /dein/pfad:/config` gemountete Ordner |
| Core (venv) | Das beim Start mit `--config` angegebene Verzeichnis |

Per SCP:

```bash
scp -r scripts/homeassistant/custom_components/bondrucker \
    user@homeassistant.local:/config/custom_components/
```

Per Samba-Share: `\\homeassistant\config\` im Explorer öffnen und den Ordner hineinkopieren.

**2. Home Assistant neu starten**

```
Einstellungen → System → Neu starten
```

**3. Integration einrichten**

Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**, suche nach
**Bondrucker** und trage die Verbindungsdaten ein (siehe [Konfiguration](#konfiguration)).

### Über HACS (Custom Repository)

1. HACS → drei Punkte oben rechts → **Benutzerdefinierte Repositories**
2. Repository-URL eintragen und als Typ **Integration** auswählen
3. Das Repository erscheint in HACS und kann von dort installiert werden
4. Home Assistant neu starten und Integration wie oben einrichten

> `hacs.json` und `manifest.json` sind für HACS vorkonfiguriert (`content_in_root: false`,
> `render_readme: true`).

## Konfiguration

Beim Einrichten der Integration (Config Flow) werden drei Felder abgefragt:

| Feld | Pflicht | Default | Beschreibung |
|---|---|---|---|
| **Host-URL** | ja | – | URL der Bondrucker-Instanz **ohne** trailing Slash, z. B. `http://192.168.1.100:8000`. |
| **API-Schlüssel** | ja | – | Wert aus der Bondrucker `.env`-Datei (`API_KEY=...`). |
| **Abfrageintervall** | nein | `30` | Wie oft Home Assistant den Drucker-Status abfragt (Sekunden, min. `10`, max. `3600`). |

Beim Speichern testet der Config Flow die Verbindung in zwei Schritten:

1. `GET /health` – Erreichbarkeit des Servers prüfen (ohne API-Key).
2. `GET /api/printer/status` – API-Key validieren.

Schlägt Schritt 1 fehl, erscheint der Fehler *„Verbindung fehlgeschlagen"*; schlägt Schritt 2
mit HTTP 401 fehl, erscheint *„Ungültiger API-Schlüssel"*. Derselbe Host kann nur einmal
konfiguriert werden – ein zweiter Versuch mit identischer URL bricht mit
*„Bondrucker ist bereits konfiguriert"* ab.

Der Wert des Abfrageintervalls steuert den `BondruckerStatusCoordinator` (Polling von
`/api/printer/status`). Presets werden immer alle `300` Sekunden abgefragt
(`BondruckerPresetCoordinator`, unabhängig vom eingestellten Intervall).

## Entities

Alle Entities gehören zum selben Gerät **Bondrucker** (Hersteller: *Bondrucker*, Modell:
*ESC/POS Thermodrucker*). Die Konfigurations-URL des Geräts zeigt auf die eingetragene
Host-URL.

### Sensoren

Die drei Sensoren werden aus den Daten von `GET /api/printer/status` befüllt (Koordinator:
`BondruckerStatusCoordinator`). Sie fallen in die `EntityCategory.DIAGNOSTIC`.

| Entity-Name | Unique ID (Suffix) | Icon | Beschreibung |
|---|---|---|---|
| **Drucker Status** | `_online` | `mdi:printer-check` | `"verbunden"` oder `"getrennt"`, abhängig vom `online`-Feld der API-Antwort. Typ: `SensorDeviceClass.ENUM`. |
| **Warteschlange** | `_queue_length` | `mdi:printer-pos` | Anzahl wartender/aktiver Aufträge (`queue_length`). Einheit: `Jobs`. Typ: `SensorStateClass.MEASUREMENT`. |
| **Aktueller Druckauftrag** | `_current_job` | `mdi:file-document-outline` | ID des gerade druckenden Auftrags, oder `"inaktiv"` wenn `current_job` leer/`null`. |

Solange der Koordinator noch keine Daten geliefert hat oder ein Polling-Fehler vorliegt,
geben alle drei Sensoren `None` zurück (Entity-Zustand: `unavailable`).

### Buttons

Buttons werden dynamisch aus den konfigurierten **Presets** erzeugt. Der
`BondruckerPresetCoordinator` ruft dafür `GET /api/presets` ab (alle 300 Sekunden).
Für jedes Preset, das die API zurückliefert, wird ein Button angelegt:

| Attribut | Wert |
|---|---|
| **Name** | `preset["name"]` (Anzeigename des Presets) |
| **Unique ID** | `<entry_id>_<preset["key"]>` |
| **Icon** | `mdi:printer` |

Ein Klick auf den Button sendet `POST /api/presets/{key}/print` mit dem API-Key im Header
`X-API-Key`. HTTP 200 oder 201 gilt als Erfolg. Bei einem anderen Statuscode oder einem
Verbindungsfehler wird eine `HomeAssistantError`-Exception ausgelöst, die Home Assistant als
Fehlermeldung in der UI anzeigt.

## Fehlerbehandlung

Beide Koordinatoren werfen bei einem fehlgeschlagenen Poll eine `UpdateFailed`-Exception:

| Fehlerfall | Meldung (im HA-Log) |
|---|---|
| HTTP-Fehlerantwort vom Server | `HTTP <Statuscode> von <URL>` |
| Verbindungsfehler (kein Response) | `Verbindungsfehler: <aiohttp-Meldung>` |

Home Assistant markiert in diesem Fall alle abhängigen Entities als `unavailable` und
wiederholt den Poll beim nächsten Intervall automatisch.

Der Request-Timeout beträgt für alle HTTP-Aufrufe `10` Sekunden (`REQUEST_TIMEOUT` in
[`const.py`](../../scripts/homeassistant/custom_components/bondrucker/const.py)).

## Fehlerbehebung

**Integration erscheint nicht in der Suche:**
Sicherstellen, dass der Ordner direkt unter `custom_components/bondrucker/` liegt (nicht
`custom_components/bondrucker/bondrucker/`) und Home Assistant neu gestartet wurde.

**Fehler „Verbindung fehlgeschlagen" beim Einrichten:**
- Bondrucker läuft? `http://<host>/health` im Browser aufrufen – muss `{"status":"ok"}` zurückgeben.
- Firewall / Port freigegeben?
- URL ohne trailing Slash eingeben, z. B. `http://192.168.1.100:8000`.

**Fehler „Ungültiger API-Schlüssel":**
API-Key stimmt nicht mit dem Wert in der Bondrucker `.env` (`API_KEY=...`) überein.

**Sensoren zeigen `unavailable`:**
Polling-Fehler – im HA-Log (`custom_components.bondrucker`) nachsehen. Debug-Logging
aktivieren:

```yaml
logger:
  default: warning
  logs:
    custom_components.bondrucker: debug
```

**Kein Button für ein Preset vorhanden:**
Presets werden nur beim Start und danach alle 300 Sekunden abgerufen. Entweder kurz warten
oder Home Assistant neu starten. Sicherstellen, dass unter `GET /api/presets` mindestens ein
Preset zurückgegeben wird (z. B. mit [`python.md`](python.md) oder
[`powershell.md`](powershell.md) prüfbar).
