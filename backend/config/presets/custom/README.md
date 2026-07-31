# Eigene Presets (nicht in git)

Dieses Verzeichnis ist für persönliche Standarddruckobjekte (Presets)
gedacht, die **nicht** versioniert werden sollen (z. B. weil sie private
Daten wie Adressen oder Zugangsdaten enthalten). Bis auf diese Datei ist
der Ordnerinhalt per `.gitignore` ausgeschlossen.

```
backend/config/presets/custom/
└── mein-preset.yaml
```

Eine YAML-Datei hier wird genauso geschrieben wie eine im Hauptverzeichnis
`backend/config/presets/` (siehe [`../../../docs/presets.md`](../../../docs/presets.md))
und erscheint unter dem gleichen Schema (`key` = Dateiname ohne Endung)
in `GET /api/presets`. Eine Datei hier mit dem gleichen Dateinamen wie ein
mitgeliefertes Preset überschreibt dieses also lokal.
