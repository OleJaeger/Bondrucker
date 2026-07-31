# Font Awesome Assets

Die Kopf-Icons der Druckaufträge werden aus einer Font-Awesome-Schriftdatei
gerendert. Dieses Verzeichnis enthält die dafür benötigten Dateien:

```
backend/assets/fontawesome/
├── fa-solid-900.ttf   # Font Awesome Free - Solid (Webfont, v6.7.2)
├── icon-map.json      # Icon-Name -> Unicode-Codepoint (hex, ohne "U+")
└── LICENSE.txt        # Font Awesome Free Lizenz (Icons: CC BY 4.0, Fonts: SIL OFL 1.1)
```

Pfade sind über `FONTAWESOME_FONT_PATH` und `FONTAWESOME_MAP_PATH`
konfigurierbar (siehe `.env.example`), falls eine andere Version/Quelle
verwendet werden soll.

## Lizenz

Font Awesome Free ist unter https://fontawesome.com/license/free verfügbar.
Die Webfont-Datei `fa-solid-900.ttf` steht unter der SIL OFL 1.1 (siehe
`LICENSE.txt`), die Weitergabe mit der Anwendung ist ausdrücklich erlaubt.

## `icon-map.json` aktualisieren / neu erzeugen

`icon-map.json` ist ein einfaches JSON-Objekt `{"fa-icon-name": "f0ab", ...}`
und wird aus den Metadaten des `@fortawesome/fontawesome-free`-npm-Pakets
erzeugt (alle Icons mit "solid"-Stil):

```python
import json

with open("metadata/icon-families.json", encoding="utf-8") as f:
    icons = json.load(f)

mapping = {
    f"fa-{name}": data["unicode"]
    for name, data in icons.items()
    if "solid" in data.get("svgs", {}).get("classic", {})
}

with open("icon-map.json", "w", encoding="utf-8") as f:
    json.dump(mapping, f, indent=2, sort_keys=True)
```

Die Liste der verfügbaren Icon-Namen wird über `GET /api/icons` an das
Frontend ausgeliefert (Such-/Auswahlfeld bei der Druckauftrags-Erstellung).

## Fallback-Verhalten

Sollten `fa-solid-900.ttf` und/oder `icon-map.json` (z.B. nach einer
Konfigurationsänderung) fehlen, unlesbar sein, oder ein in einem
Druckauftrag referenziertes Icon nicht in der Map enthalten sein, wird
stattdessen ein einfacher Platzhalter (umrahmte Box mit Kürzel) gedruckt.
Der Druckauftrag schlägt dadurch **nicht** fehl ("defekte Icons" werden
sauber degradiert).
