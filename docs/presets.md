# Standarddruckobjekte (Presets)

Standarddruckobjekte sind vorkonfigurierte Druckaufträge, die im Frontend
unter "Standarddruckobjekte" als Karten mit Icon, Name und Beschreibung
erscheinen und per Klick auf "Drucken" sofort in die Warteschlange eingereiht
werden (`POST /api/presets/{key}/print`). Jedes Preset wird durch eine
YAML-Datei in `backend/config/presets/` definiert; der `key` ist der
Dateiname ohne Endung.

Diese Datei beschreibt das YAML-Schema und wie eigene **Inhalts-Skripte**
(`content_script`) geschrieben werden.

## YAML-Schema (`PresetConfig`)

```yaml
name: "Wettervorhersage"            # Pflicht, nicht leer - Anzeigename
description: "Wettervorhersage fuer heute"  # Pflicht, nicht leer - Kartentext
icon: "fa-cloud-sun"                # Pflicht, nicht leer - siehe IconPicker/GET /api/icons
template: "freitext"                # Pflicht, nicht leer - Key aus GET /api/templates

title: "Wettervorhersage"           # optional, Default ""
print_timestamp: true                # optional, Default true

# optionale Registrierung: Settings-Felder (app.config.WEB_SETTINGS_FIELDS),
# die das content_script/attachment.script dieses Presets liest - siehe
# configuration.md. Macht das Preset in GET /api/settings ("used_by_presets")
# sichtbar; unbekannte Schluessel lassen das Preset beim Laden scheitern.
config_keys: ["homeassistant_url", "homeassistant_token"]

# Inhalt: genau eine der beiden Optionen (exklusiv)
content: "Statischer Markdown-Text"  # ODER:
content_script: "weather_forecast"   # Name eines Moduls in app/presets/scripts/

# optionaler Anhang (QR-Code oder Bild)
attachment:
  type: "qr_code"                    # "qr_code" oder "image"
  content: "WIFI:T:WPA;S:...;P:...;;" # erforderlich fuer type: qr_code
  # genau eine der beiden Optionen ist fuer type: image erforderlich:
  # path: "logo.png"                 # statisch, relativ zu backend/config/presets/
  # script: "random_animal"          # dynamisch, Modul in app/presets/scripts/
```

Felder im Detail:

- **`name`**, **`description`**, **`icon`**, **`template`** sind
  Pflichtfelder und dürfen nicht leer sein. `icon` ist ein Font-Awesome-Key
  (`fa-...`) oder ein benutzerdefiniertes SVG (siehe `GET /api/icons` bzw.
  `IconPicker`/`IconGlyph` im Frontend). `template` muss eine über
  `GET /api/templates` verfügbare Vorlage referenzieren.
- **`title`** und **`print_timestamp`** entsprechen den gleichnamigen Feldern
  von `POST /api/jobs` (`PrintJobCreate`).
- **`config_keys`** (optional, Default `[]`) registriert die
  `Settings`-Felder, die `content_script`/`attachment.script` dieses Presets
  liest - siehe [`configuration.md`](configuration.md). Jeder Eintrag muss
  ein Schlüssel aus `app.config.WEB_SETTINGS_FIELDS` sein.
- **`content`** und **`content_script`** sind **exklusiv** - genau eines der
  beiden Felder (oder keines, dann ist der Inhalt leer) darf gesetzt sein.
  - `content`: statischer Markdown-Text, direkt in der YAML-Datei.
  - `content_script`: Name eines Python-Moduls in `app/presets/scripts/`
    (ohne `.py`), das den Inhalt zur Druckzeit erzeugt (siehe unten). Der
    Name muss dem Muster `^[a-z][a-z0-9_]*$` entsprechen (gültiger
    Python-Modulname, verhindert Pfad-/Modul-Injection beim dynamischen
    Import).
- **`attachment`** (optional) erzeugt denselben Anhang wie bei
  `POST /api/jobs` (siehe [`markdown-mapping.md`](markdown-mapping.md#anhänge-bild-upload-und-qr-code)):
  - `type: qr_code` mit `content`: der zu kodierende Text (z. B.
    WLAN-Zugangsdaten im Format `WIFI:T:<Verschlüsselung>;S:<SSID>;
    P:<Passwort>;;`).
  - `type: image` mit **genau einer** der beiden Optionen (exklusiv):
    - `path`: Pfad zu einer Bilddatei relativ zu `backend/config/presets/`
      (wird beim Drucken als Base64-Data-URL eingebettet).
    - `script`: Name eines Python-Moduls in `app/presets/scripts/` (ohne
      `.py`), das das Bild zur Druckzeit erzeugt (siehe unten, analog zu
      `content_script`). Name muss ebenfalls `^[a-z][a-z0-9_]*$` entsprechen.

Ungültige YAML-Dateien (Schema-Fehler, defektes YAML) werden beim Start
geloggt und übersprungen - die Anwendung startet trotzdem (analog zu
`app/templates/loader.py::TemplateRegistry`).

## Ablauf von `POST /api/presets/{key}/print`

1. `PresetRegistry.get(key)` lädt die Konfiguration (unbekannter Key →
   `404 PresetNotFoundError`).
2. `build_preset_payload(preset)`:
   - falls `content_script` gesetzt ist, wird
     `run_content_script(content_script)` aufgerufen (siehe unten); schlägt
     dies fehl, wird `502 PresetScriptError` zurückgegeben und **kein**
     Druckauftrag angelegt.
   - sonst wird `content` (oder ein leerer String) als Markdown verwendet.
   - ein konfigurierter `attachment` wird zu `qr_code`/`image_base64`
     aufgelöst.
3. Das resultierende Payload wird wie bei `POST /api/jobs` validiert
   (`PrintJobCreate.model_validate`) und mit `build_document` eager
   validiert (ungültige Vorlage/Markdown → `400`, bevor ein Job angelegt
   wird).
4. Bei Erfolg wird ein Job mit Status `queued` angelegt und wie bei
   `POST /api/jobs` als `201` zurückgegeben (`PrintJobResponse`).

## Eigene Inhalts-Skripte schreiben (`content_script`)

Ein Inhalts-Skript ist ein Python-Modul in `backend/app/presets/scripts/`
mit genau einer Funktion:

```python
# backend/app/presets/scripts/mein_skript.py
"""Kurzbeschreibung, was dieses Skript druckt."""

from __future__ import annotations


def generate() -> str:
    """Gibt den Markdown-Inhalt des Druckauftrags zurueck."""

    return "# Ueberschrift\n\nMarkdown-Text..."
```

Anforderungen:

- Die Funktion heißt **`generate`**, nimmt keine Argumente und gibt einen
  **`str`** (Markdown) zurück.
- Referenziert wird das Skript im Preset-YAML über
  `content_script: "mein_skript"` (Modulname **ohne** `.py`, muss
  `^[a-z][a-z0-9_]*$` entsprechen).
- Fehler werden als `PresetScriptError` an die API durchgereicht
  (`502 Bad Gateway`), **ohne** dass ein Druckauftrag angelegt wird:
  - Modul nicht vorhanden oder keine `generate()`-Funktion,
  - `generate()` wirft eine Exception (z. B. HTTP-Fehler),
  - `generate()` gibt keinen `str` zurück.
  Eigene, fehlende Konfiguration sollte ebenfalls als `PresetScriptError`
  mit einer klaren deutschen Meldung signalisiert werden, z. B.:

  ```python
  from app.exceptions import PresetScriptError

  if not settings.mealie_base_url:
      raise PresetScriptError("MEALIE_BASE_URL ist nicht konfiguriert")
  ```

- Zugriff auf Konfiguration (z. B. API-URLs, Zugangsdaten) erfolgt über
  `app.config.get_effective_settings()` (nicht `get_settings()`) - dadurch
  greifen auch Werte, die über die Web-App gesetzt wurden (siehe
  [`configuration.md`](configuration.md)), ohne Neustart des Containers. Neue
  Einstellungen werden in `Settings` (`app/config.py`) als optionale Felder
  mit sinnvollem Default ergänzt, damit die Anwendung auch ohne diese
  Variablen startet - das jeweilige Skript liefert dann einen
  `PresetScriptError` statt eines Druckauftrags. Soll die Einstellung auch
  über die Web-App konfigurierbar sein, in `WEB_SETTINGS_FIELDS`
  (`app/config.py`) eintragen und im Preset-YAML unter `config_keys`
  registrieren.
- Für ausgehende HTTP-Aufrufe wird `httpx` verwendet (Laufzeit-Abhängigkeit,
  siehe `backend/requirements.txt`). Diese Aufrufe laufen **synchron im
  API-Prozess** während `POST /api/presets/{key}/print` (siehe
  [`security.md`](security.md#ausgehende-verbindungen-der-preset-skripte)).
- Da die Font A des ESC/POS-Druckers nur einen begrenzten Zeichensatz
  unterstützt, sollten Skripte auf Emojis und exotische Unicode-Zeichen
  verzichten.

### Vorhandene Skripte als Vorlage

| Skript | Zweck | Konfiguration |
|---|---|---|
| `positive_message.py` | Wählt zufällig einen von ~15 aufmunternden Sätzen (keine externen Aufrufe). | - |
| `weather_forecast.py` | Ruft die Tagesvorhersage von Open-Meteo ab und formatiert sie als Markdown. | `WEATHER_LATITUDE`, `WEATHER_LONGITUDE`, `WEATHER_LOCATION_NAME` (Default: Berlin) |
| `mealie_shopping_list.py` | Lädt offene Positionen einer Mealie-Einkaufsliste (API v1) als Markdown-Checkliste. | `MEALIE_BASE_URL`, `MEALIE_API_TOKEN`, optional `MEALIE_SHOPPING_LIST_ID` |
| `super_productivity_today.py` | Liest die für heute fälligen, offenen Aufgaben aus dem Super-Productivity-WebDAV-Sync. | `SP_WEBDAV_URL`, `SP_WEBDAV_USERNAME`, `SP_WEBDAV_PASSWORD`, `SP_SYNC_PATH` |
| `jagdtag_heute.py` | Liest heute jagdbares Haar- und Federwild aus der PostgreSQL-Tabelle `jagdzeiten` und ergänzt Wetter, Windrichtung und Sonnenuntergang von Open-Meteo. | `JAGD_DB_HOST`, `JAGD_DB_PORT`, `JAGD_DB_NAME`, `JAGD_DB_USER`, `JAGD_DB_PASSWORD`; `WEATHER_LATITUDE`/`WEATHER_LONGITUDE`/`WEATHER_LOCATION_NAME` |

Alle Variablen werden in `.env.example` dokumentiert und sind optional - ohne
Konfiguration liefert das jeweilige Preset einen `502 PresetScriptError`
statt eines Druckauftrags.

## Eigene Bild-Skripte schreiben (`attachment.script`)

Analog zu `content_script` kann ein Anhang vom Typ `image` statt eines
statischen `path` ein **Bild-Skript** verwenden: ein Modul in
`backend/app/presets/scripts/` mit genau einer Funktion:

```python
# backend/app/presets/scripts/mein_bild_skript.py
"""Kurzbeschreibung, was dieses Skript druckt."""

from __future__ import annotations


def generate_image() -> bytes:
    """Gibt die Bilddaten (z. B. PNG-Bytes) des Druckauftrags zurueck."""

    return ...
```

Anforderungen:

- Die Funktion heißt **`generate_image`**, nimmt keine Argumente und gibt
  **`bytes`** (Bilddaten, z. B. PNG) zurück.
- Referenziert wird das Skript im Preset-YAML über
  `attachment: {type: image, script: "mein_bild_skript"}` (Modulname **ohne**
  `.py`, muss `^[a-z][a-z0-9_]*$` entsprechen).
- Fehler werden wie bei `content_script` als `PresetScriptError`
  (`502 Bad Gateway`) an die API durchgereicht, **ohne** dass ein
  Druckauftrag angelegt wird.

### Motivtafeln mit rotem Raster (`app/presets/grid_images.py`)

`random_animal.py` zeigt das Muster für ein **erweiterbares Bilderverzeichnis**
(`settings.images_dir`, Default `backend/assets/images/`): eine "Motivtafel"
ist eine einzelne PNG-Datei mit mehreren Einzelmotiven, durch ein **rotes
Raster** voneinander getrennt (z. B. mehrere Tiere zum Ausmalen auf einem
Bogen). `grid_images.random_cell_png(filename)` übernimmt das gesamte
Handling:

1. Erkennt die roten Rasterlinien (per reiner Pillow-Flood-Fill, ohne
   numpy/scipy-Abhängigkeit) und ermittelt so die Zellgrenzen - es ist
   **keine** manuelle Koordinaten-Pflege nötig.
2. Schneidet zufällig **eine** Zelle aus, entfernt das rote Raster
   (verbleibende Pixel werden weiß) und legt Transparenz auf weißem
   Hintergrund ab.
3. Hat eine Bilddatei **kein** rotes Raster, wird sie als Ganzes (geflättet)
   zurückgegeben - eine künftige Motivtafel ohne Raster benötigt also keine
   Codeänderung.

Eine neue Motivtafel hinzuzufügen heißt also nur: PNG-Datei (optional mit
rotem Raster) nach `backend/assets/images/` legen und ein kleines Skript wie
`random_animal.py` schreiben, das `random_cell_png("<dateiname>.png")`
aufruft.

| Skript | Zweck |
|---|---|
| `random_animal.py` | Schneidet ein zufälliges Tiermotiv aus `assets/images/animals.png` aus (Raster wird entfernt). |

## Eigene, nicht versionierte Presets/Skripte (`custom/`)

`backend/config/presets/` und `backend/app/presets/scripts/` enthalten je
ein Unterverzeichnis `custom/`, dessen Inhalt (bis auf eine `README.md`,
bzw. zusätzlich `__init__.py` bei den Skripten) per `.gitignore`
ausgeschlossen ist - gedacht für persönliche Presets/Skripte, die nicht
versioniert werden sollen (z. B. weil sie private Daten oder
Zugangsdaten enthalten, analog zum bisherigen Beispiel `jagdtag-heute.yaml`/
`jagdtag_heute.py`).

- Eine YAML-Datei in `backend/config/presets/custom/` wird genauso geladen
  wie eine im Hauptverzeichnis (`PresetRegistry`, siehe
  `app/presets/loader.py`) - `custom/` wird **nach** dem Hauptverzeichnis
  eingelesen, eine Datei dort mit gleichem Dateinamen überschreibt also
  lokal ein mitgeliefertes Preset.
- Ein Skript in `backend/app/presets/scripts/custom/` wird über den
  **gleichen** Namen wie ein Skript im Hauptverzeichnis referenziert
  (`content_script`/`attachment.script`) - `run_content_script`/
  `run_image_script` (`app/presets/script_runner.py`) suchen zuerst in
  `app/presets/scripts/`, dann in `app/presets/scripts/custom/`.
- Analog gibt es `backend/config/templates/custom/` für nicht versionierte
  Vorlagen (`TemplateRegistry`, siehe `app/templates/loader.py`).

Siehe die `README.md` in den jeweiligen `custom/`-Verzeichnissen.

## Beispiel: neues Preset hinzufügen

1. YAML-Datei in `backend/config/presets/` anlegen, z. B.
   `geburtstagskarte.yaml`:

   ```yaml
   name: "Geburtstagskarte"
   description: "Druckt eine Geburtstagskarte mit Glueckwunsch"
   icon: "fa-cake-candles"
   template: "message"
   title: "Alles Gute!"
   content: "Wir wuenschen dir einen wundervollen Tag!"
   ```

2. Backend-Container neu starten (oder Registry neu laden) - das Preset
   erscheint danach unter `GET /api/presets` und im Frontend unter
   "Standarddruckobjekte".
3. Für dynamische Inhalte stattdessen `content_script` setzen und ein
   passendes Modul in `backend/app/presets/scripts/` anlegen (siehe oben).
   Für dynamische Bild-Anhänge analog `attachment.script` setzen (siehe
   "Eigene Bild-Skripte schreiben" oben).
