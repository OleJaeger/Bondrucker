# Eigene Vorlagen (nicht in git)

Dieses Verzeichnis ist für persönliche Druckvorlagen gedacht, die **nicht**
versioniert werden sollen. Bis auf diese Datei ist der Ordnerinhalt per
`.gitignore` ausgeschlossen.

```
backend/config/templates/custom/
└── meine-vorlage.yaml
```

Eine YAML-Datei hier wird genauso geschrieben wie eine im Hauptverzeichnis
`backend/config/templates/` und erscheint unter dem gleichen Schema (`key` =
Dateiname ohne Endung) in `GET /api/templates`. Eine Datei hier mit dem
gleichen Dateinamen wie eine mitgelieferte Vorlage überschreibt diese also
lokal.
