# Eigene Inhalts-/Bild-Skripte (nicht in git)

Dieses Verzeichnis ist für persönliche `content_script`/`attachment.script`-
Module gedacht, die **nicht** versioniert werden sollen (z. B. weil sie
private Zugangsdaten im Code enthalten oder einfach nur lokal relevant
sind). Bis auf diese Datei und `__init__.py` ist der Ordnerinhalt per
`.gitignore` ausgeschlossen.

```
backend/app/presets/scripts/custom/
└── mein_skript.py
```

Ein Skript hier wird genauso geschrieben wie eines in
`backend/app/presets/scripts/` (siehe
[`../../../../docs/presets.md`](../../../../docs/presets.md#eigene-inhalts-skripte-schreiben-content_script)):
`generate() -> str` bzw. `generate_image() -> bytes`.

Referenziert wird es im Preset-YAML mit dem **gleichen** Namen wie ein
Skript im Hauptverzeichnis (`content_script: "mein_skript"` bzw.
`attachment: {type: image, script: "mein_skript"}`) -
`app/presets/script_runner.py` sucht zuerst in
`app/presets/scripts/`, dann in `app/presets/scripts/custom/`. Ein Skript
hier mit dem gleichen Namen wie ein mitgeliefertes Skript überschreibt
dieses also lokal.
