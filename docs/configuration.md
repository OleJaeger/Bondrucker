# Konfiguration in der Web-App

Die meiste Konfiguration (Drucker, Storage-Pfade, Security, CORS, Queue/Retry)
bleibt ausschließlich über `.env` steuerbar (siehe `.env.example`) - sie wird
einmal beim Containerstart gelesen und betrifft Infrastruktur, nicht den
laufenden Betrieb.

Die Zugangsdaten/Standardwerte der **Standarddruckobjekt-Integrationen**
(Mealie, HomeAssistant/Wetter, Super Productivity, Jagdtag) lassen sich
dagegen zusätzlich über die Web-App ändern, ohne den Container neu zu
starten - sichtbar unter "Konfiguration" im Frontend bzw. über
`GET`/`PUT /api/settings`.

## Sperrlogik: ".env gewinnt immer"

Für jedes der editierbaren Felder gilt: Ist die zugehörige Umgebungsvariable
gesetzt (in der echten Umgebung oder in einer `.env`-Datei im
Arbeitsverzeichnis des Backend-Prozesses), ist das Feld **gesperrt**
(`locked: true` in der API-Antwort) - es wird nur der aktuelle Wert
angezeigt, ein `PUT` darauf liefert `400`. Ist die Variable nicht gesetzt,
kann der Wert über die Web-App gepflegt werden und wird in der SQLite-Tabelle
`app_settings` persistiert (siehe `app/repositories/settings.py`).

Diese Entscheidung wird bei jedem Request neu getroffen
(`app.config.env_locked_fields()`) - ein nachträglich in `.env` ergänzter
Wert sperrt das Feld beim nächsten Request, ganz ohne Migration.

Layering, von niedrigster zur höchsten Priorität:

```
Feld-Default < Web-Override (app_settings) < Umgebungsvariable / .env
```

`app.config.get_effective_settings()` baut diese Schicht über die normale
`Settings`-Instanz (`get_settings()`); Preset-Inhalts-Skripte und der
Drucker-Steckdosen-Endpunkt (`GET /api/printer/power`) verwenden
`get_effective_settings()` statt `get_settings()`, damit Änderungen über die
Web-App sofort wirken.

## Editierbare Felder

Siehe `app.config.WEB_SETTINGS_FIELDS` für die vollständige, maßgebliche
Liste (Gruppe, Label, Typ, ob geheim). Aktuell:

| Gruppe | Felder |
|---|---|
| Mealie (Einkaufsliste) | `mealie_base_url`, `mealie_api_token` (geheim), `mealie_shopping_list_id` |
| Wetter / HomeAssistant | `weather_location_name`, `homeassistant_url`, `homeassistant_token` (geheim), `homeassistant_printer_plug` |
| Super Productivity | `sp_webdav_url`, `sp_webdav_username`, `sp_webdav_password` (geheim), `sp_sync_path` |
| Jagdtag | `jagd_db_host`, `jagd_db_port`, `jagd_db_name`, `jagd_db_user`, `jagd_db_password` (geheim) |

Geheime Felder (`secret: true`) geben ihren aktuellen Wert nie über die API
zurück - nur `is_set` (ob ein Wert konfiguriert ist). Ein neuer Wert kann
blind überschrieben werden, ohne den alten je gelesen zu haben.

## Presets registrieren ihre Konfiguration

Ein Preset, dessen `content_script` (oder `attachment.script`) eine dieser
Einstellungen liest, registriert sich dafür im YAML über `config_keys`:

```yaml
# backend/config/presets/einkaufsliste.yaml
content_script: "mealie_shopping_list"
config_keys: ["mealie_base_url", "mealie_api_token", "mealie_shopping_list_id"]
```

`config_keys` wird gegen `WEB_SETTINGS_FIELDS` validiert (unbekannte
Schlüssel lassen das Preset beim Laden scheitern, analog zu allen anderen
Preset-Validierungsfehlern). `GET /api/settings` löst diese Registrierung
serverseitig auf (`used_by_presets`) und zeigt so pro Feld, welche
Standarddruckobjekte es betreffen - praktisch, um z. B. zu erkennen, dass
`MEALIE_BASE_URL` nur für "Einkaufsliste" relevant ist.

## `PUT /api/settings`

Das Request-Body ist ein **sparse** JSON-Objekt - nur zu ändernde Felder
müssen enthalten sein. Ein Wert von `null` löscht den Web-Override (Feld
fällt zurück auf seinen Default):

```bash
curl -X PUT /api/settings \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mealie_base_url": "https://mealie.example.com", "mealie_shopping_list_id": null}'
```

Antwort (für `GET` und `PUT` identisch): Liste aller editierbaren Felder mit
`value`, `default`, `is_set`, `locked`, `secret`, `group`, `label` und
`used_by_presets`.
