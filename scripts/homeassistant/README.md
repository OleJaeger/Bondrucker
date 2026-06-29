# Bondrucker – Home Assistant Integration

Lokale Custom Component für Home Assistant. Bindet eine laufende Bondrucker-Instanz an Home Assistant an und stellt Sensoren (Queue-Status, Druckerstatus) sowie Buttons (Testdruck) bereit.

## Voraussetzungen

- Home Assistant (mind. 2023.1.0)
- Bondrucker läuft und ist aus Home Assistant erreichbar (z. B. `http://192.168.1.100:8000`)
- API-Key aus der Bondrucker `.env`-Datei

---

## Installation (ohne HACS, manuell)

### 1. Dateien kopieren

Kopiere den Ordner `custom_components/bondrucker` in das `custom_components`-Verzeichnis deiner Home Assistant-Konfiguration:

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

**Wo liegt `<config>`?**

| Installationsart | Pfad |
|---|---|
| Home Assistant OS / Supervised | `/config/` (im HA-Dateisystem, per Samba-Share oder SSH erreichbar) |
| Docker (`docker run`) | Der Ordner, den du als `-v /dein/pfad:/config` gemountet hast |
| Core (venv) | Das Verzeichnis, das du beim Start mit `--config` angegeben hast |

**Per SCP (Beispiel):**

```bash
scp -r scripts/homeassistant/custom_components/bondrucker \
    user@homeassistant.local:/config/custom_components/
```

**Per Samba-Share:** Öffne `\\homeassistant\config\` im Windows Explorer und kopiere den Ordner dort hinein.

### 2. Home Assistant neu starten

```
Einstellungen → System → Neu starten
```

### 3. Integration einrichten

1. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**
2. Suche nach **Bondrucker**
3. Trage die Verbindungsdaten ein:
   - **Host**: URL deiner Bondrucker-Instanz, z. B. `http://192.168.1.100:8000`
   - **API-Key**: Wert aus deiner `.env`-Datei (`API_KEY=...`)
   - **Scan-Intervall**: Wie oft HA den Status abfragt (Standard: 30 Sekunden, min. 10 s)

---

## Installation über HACS (Custom Repository)

Falls HACS installiert ist, kann das Repository als benutzerdefiniertes Repository hinzugefügt werden, ohne es im HACS-Store zu veröffentlichen.

1. HACS → drei Punkte oben rechts → **Benutzerdefinierte Repositories**
2. Repository-URL eintragen (z. B. die Gitea-URL) und als Typ **Integration** auswählen
3. Das Repository erscheint in HACS und kann installiert werden
4. Nach der Installation Home Assistant neu starten und Integration wie oben einrichten

> Das `hacs.json` und die `manifest.json` sind bereits für HACS vorkonfiguriert.

---

## Bereitgestellte Entities

| Entity | Typ | Beschreibung |
|---|---|---|
| `sensor.bondrucker_queue_length` | Sensor | Anzahl der Aufträge in der Queue |
| `sensor.bondrucker_printer_status` | Sensor | Aktueller Druckerstatus |
| `button.bondrucker_test_print` | Button | Löst einen Testdruck aus |

---

## Fehlerbehebung

**Integration erscheint nicht in der Suche:**
Sicherstellen, dass der Ordner `bondrucker` direkt unter `custom_components/` liegt (nicht `custom_components/bondrucker/bondrucker/`) und HA neu gestartet wurde.

**"Cannot connect"-Fehler beim Einrichten:**
- Bondrucker läuft? → `http://<host>/health` im Browser aufrufen, muss `{"status":"ok"}` zurückgeben
- Firewall/Port freigegeben?
- URL ohne trailing Slash eingeben, z. B. `http://192.168.1.100:8000`

**"Invalid auth"-Fehler:**
API-Key stimmt nicht mit dem Wert in der Bondrucker `.env` (`API_KEY=...`) überein.

**Logs aktivieren** (in `configuration.yaml`):

```yaml
logger:
  default: warning
  logs:
    custom_components.bondrucker: debug
```
