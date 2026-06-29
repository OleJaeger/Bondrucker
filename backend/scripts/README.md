# Backend-Skripte

Hilfsskripte für die Entwicklung, ausgeführt aus dem `backend`-Verzeichnis mit
dem dortigen virtualenv (`.venv/bin/python`).

| Skript | Zweck |
|---|---|
| [`add_config.py`](add_config.py) | Legt interaktiv eine neue Vorlage (Template) oder ein neues Standarddruckobjekt (Preset) an und ergänzt die zugehörigen Tests. |
| [`export_openapi.py`](export_openapi.py) | Exportiert das OpenAPI-Schema der laufenden App nach `docs/openapi.yaml`. |

## `add_config.py`

```bash
.venv/bin/python scripts/add_config.py preset
.venv/bin/python scripts/add_config.py template
```

Fragt interaktiv die nötigen Felder ab (Key, Name, Icon, ...) und legt
anschließend zwei Dinge an:

1. Die YAML-Datei unter `config/presets/<key>.yaml` bzw.
   `config/templates/<key>.yaml`, im Stil der vorhandenen Configs
   (Kommentarkopf + auskommentierte optionale Felder als Vorlage). Das
   vollständige Schema ist in [`../../docs/presets.md`](../../docs/presets.md)
   beschrieben (Templates analog über `app/templates/schema.py`).
2. Den neuen Key in den Tests, die alle ausgelieferten Presets/Templates
   aufzählen, damit ein vergessener Eintrag dort sofort als fehlschlagender
   Test auffällt statt unbemerkt zu bleiben:
   - Preset: `tests/test_presets.py`, `tests/test_presets_api.py`
   - Template: `tests/test_templates.py`

Der Key muss mit einem Kleinbuchstaben beginnen und darf nur
Kleinbuchstaben, Ziffern und `-` enthalten (`^[a-z][a-z0-9-]*$`); bereits
vergebene Keys werden abgelehnt. Pflichtfelder ohne Eingabe werden erneut
abgefragt.

Nach dem Anlegen muss das Backend neu gestartet werden, damit die neue
Konfiguration geladen wird (Presets/Templates werden beim Start einmalig
eingelesen, siehe `app/presets/loader.py` / `app/templates/loader.py`).

Für `content_script`-Presets (dynamisch erzeugter Inhalt) muss zusätzlich
ein Modul in `app/presets/scripts/` angelegt werden - siehe
[`../../docs/presets.md`](../../docs/presets.md#eigene-inhalts-skripte-schreiben-content_script).

## `export_openapi.py`

```bash
.venv/bin/python scripts/export_openapi.py
```

Generiert `docs/openapi.yaml` direkt aus der FastAPI-App (Routen,
Pydantic-Modelle, Docstrings), damit die Spezifikation nie vom tatsächlichen
Code abweicht. Sollte nach Änderungen an der API erneut ausgeführt werden.
