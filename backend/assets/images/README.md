# Motivtafeln für Bild-Skripte

Hier liegen PNG-Dateien, die von Bild-Skripten (`attachment.script`, siehe
[`../../../docs/presets.md`](../../../docs/presets.md#eigene-bild-skripte-schreiben-attachmentscript))
verwendet werden, z. B. `animals.png` für das Preset "Ausmalbild"
(`random_animal.py`).

Eine **Motivtafel** ist eine einzelne Bilddatei mit mehreren Einzelmotiven,
durch ein **rotes Raster** voneinander getrennt:

```
backend/assets/images/
└── animals.png   -> 15 Tiermotive, durch rote Linien getrennt
```

`app/presets/grid_images.random_cell_png(filename)` erkennt das rote Raster
automatisch (keine manuelle Koordinaten-Pflege nötig), schneidet zufällig
ein Motiv aus und entfernt dabei das Raster (rote Pixel werden weiß).
Enthält eine Datei kein rotes Raster, wird sie als Ganzes verwendet.

## Hinweise

- Rasterlinien müssen kräftig rot sein (`#FF0000`-artig, nicht z. B. Orange
  oder Rosa) und jede Zelle vollständig umschließen, sonst werden
  benachbarte Zellen als eine einzige erkannt.
- Transparente Bereiche werden beim Drucken auf Weiß gelegt (nicht Schwarz).
- Das Verzeichnis ist über die Umgebungsvariable `IMAGES_DIR` konfigurierbar
  (Default `assets/images`), falls ein anderer Ort verwendet werden soll.
- Nach dem Hinzufügen einer neuen Motivtafel muss zusätzlich ein kleines
  Bild-Skript angelegt werden (siehe `random_animal.py` als Vorlage) sowie
  ein Preset, das es referenziert.
