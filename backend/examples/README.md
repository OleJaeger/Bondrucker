# Beispiel-Druckaufträge

Diese JSON-Dateien entsprechen dem Request-Body von `POST /api/jobs` und
`POST /api/preview` (Schema `PrintJobCreate`, siehe
[`../../docs/openapi.yaml`](../../docs/openapi.yaml)).

| Datei | Vorlage | Demonstriert |
|---|---|---|
| `job-todo.json` | `todo` | Checkboxen (`- [ ]` / `- [x]`), Standard-Icon der Vorlage. |
| `job-freitext.json` | `freitext` | Überschrift, Fett/Kursiv, Liste, Trennlinie. |
| `job-table.json` | `freitext` | Markdown-Tabelle mit Spaltenausrichtung, eigenes Icon. |

## Verwendung

In eine PNG-Vorschau rendern (kein Druckauftrag wird angelegt):

```bash
curl -s -X POST http://localhost:8000/api/preview \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @job-todo.json \
  -o preview.png
```

Als Druckauftrag einreihen:

```bash
curl -s -X POST http://localhost:8000/api/jobs \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d @job-todo.json
```

Die Antwort enthält die generierte `id`, z. B. um den Status abzufragen:

```bash
curl -s http://localhost:8000/api/jobs/<id> -H "X-API-Key: $API_KEY"
```

oder den Auftrag abzubrechen (nur solange `status` `queued` oder `failed` ist):

```bash
curl -s -X DELETE http://localhost:8000/api/jobs/<id> -H "X-API-Key: $API_KEY"
```
