# PowerShell-Modul `Bondrucker`

Benutzerhandbuch für [`scripts/powershell/Bondrucker.psm1`](../../scripts/powershell/Bondrucker.psm1)
(Manifest [`Bondrucker.psd1`](../../scripts/powershell/Bondrucker.psd1)) – ein
PowerShell-Modul, das alle Endpunkte der Bondrucker REST-API
([`../openapi.yaml`](../openapi.yaml)) als Cmdlets bereitstellt.

## Inhalt

- [Voraussetzungen](#voraussetzungen)
- [Installation / Import](#installation--import)
- [Konfiguration](#konfiguration)
- [Fehlerbehandlung](#fehlerbehandlung)
- [Funktionsreferenz](#funktionsreferenz)
  - [Export-BondruckerApiKey](#export-bondruckerapikey)
  - [Get-BondruckerHealth](#get-bondruckerhealth)
  - [Get-BondruckerTemplate](#get-bondruckertemplate)
  - [Get-BondruckerIcon](#get-bondruckericon)
  - [Get-BondruckerPrinterStatus](#get-bondruckerprinterstatus)
  - [Get-BondruckerJob](#get-bondruckerjob)
  - [New-BondruckerJob](#new-bondruckerjob)
  - [Stop-BondruckerJob](#stop-bondruckerjob)
  - [Get-BondruckerPreview](#get-bondruckerpreview)
- [-WhatIf / -Confirm](#-whatif---confirm)

## Voraussetzungen

- **PowerShell 7.0 oder neuer** (`#Requires -Version 7.0`), plattformunabhängig
  (Windows, macOS, Linux).
- Netzwerkzugriff auf die Bondrucker-API (Default `https://bondrucker.bondrucker-app.de`, siehe
  [Konfiguration](#konfiguration)).
- Ein gültiger API-Key für alle Endpunkte ausser `GET /health` (siehe
  [`.env.example`](../../.env.example) bzw. [`security.md`](../security.md)).

## Installation / Import

Das Modul muss nicht installiert werden – es wird direkt aus dem Checkout importiert:

```powershell
Import-Module ./scripts/powershell/Bondrucker.psd1
```

Mit `-Force` neu laden (z. B. nach Änderungen am Modul):

```powershell
Import-Module ./scripts/powershell/Bondrucker.psd1 -Force
```

Alle exportierten Befehle anzeigen:

```powershell
Get-Command -Module Bondrucker
```

Zu jedem Befehl steht Hilfe per `Get-Help <Cmdlet> -Full` zur Verfügung (Syntax, Parameter,
Beispiele – Auszüge davon sind unten in der [Funktionsreferenz](#funktionsreferenz)
enthalten).

## Konfiguration

Basis-URL und API-Key werden von **jedem** Cmdlet (ausser `Get-BondruckerHealth`, das
keinen API-Key benötigt) in dieser Reihenfolge aufgelöst:

1. Die Parameter `-BaseUrl` / `-ApiKey` des jeweiligen Cmdlets.
2. Umgebungsvariablen `BONDRUCKER_API_URL` / `BONDRUCKER_API_KEY`.
3. `.env` im Projekt-Wurzelverzeichnis (`Bondrucker/.env`): `BONDRUCKER_API_URL` /
   `BONDRUCKER_API_KEY`, für den API-Key alternativ das dort bereits vorhandene `API_KEY`
   (derselbe Wert, den der Server im Header `X-API-Key` erwartet).
4. Ein per [`Export-BondruckerApiKey`](#export-bondruckerapikey) hinterlegter Key.
5. Default für die Basis-URL: `https://bondrucker.bondrucker-app.de`. Für den API-Key gibt es
   ansonsten keinen Default.

Ist nach Schritt 1–4 kein API-Key vorhanden, brechen authentifizierte Cmdlets mit folgender
Meldung ab:

```
Kein API-Key konfiguriert. Setze BONDRUCKER_API_KEY oder API_KEY (z.B. in der .env im
Projekt-Wurzelverzeichnis) oder uebergib -ApiKey.
```

### Beispiel: Umgebungsvariablen für die aktuelle Sitzung setzen

```powershell
$env:BONDRUCKER_API_URL = 'http://localhost:8000'
$env:BONDRUCKER_API_KEY = 'mein-api-key'
```

### Beispiel: `.env` im Projekt-Wurzelverzeichnis

```env
BONDRUCKER_API_URL=http://localhost:8000
API_KEY=mein-api-key
```

(`API_KEY` ist die Variable aus [`.env.example`](../../.env.example), die der Server
selbst verwendet – sie wird hier als Fallback für `BONDRUCKER_API_KEY` wiederverwendet,
sodass für lokale Entwicklung eine einzige `.env` reicht.)

## Fehlerbehandlung

Schlägt ein API-Aufruf fehl, werfen alle Cmdlets eine `Exception` mit lesbarem
Text – Fehler also z. B. mit `try`/`catch` oder `$Error` behandeln:

- Bei einer HTTP-Fehlerantwort: `"HTTP <Statuscode>: <detail>"`, wobei `<detail>` aus dem
  `detail`-Feld der JSON-Fehlerantwort stammt (siehe `HTTPValidationError`/`detail` in
  [`../openapi.yaml`](../openapi.yaml)), z. B.:

  ```
  HTTP 401: Invalid or missing API key
  ```

  ```
  HTTP 422: [{"loc":["body","template"],"msg":"...","type":"..."}]
  ```

- Bei einem Verbindungsfehler (Server nicht erreichbar, Timeout, ...): die rohe
  `.NET`-Exception-Meldung (kein `HTTP <code>:`-Präfix).

```powershell
try {
    New-BondruckerJob -Template todo -Title 'Test' -Markdown '- [ ] Punkt 1'
} catch {
    Write-Error "Druckauftrag fehlgeschlagen: $_"
}
```

## Funktionsreferenz

### Export-BondruckerApiKey

Speichert den API-Key verschlüsselt für den aktuellen Benutzer, sodass er nicht jedes Mal
über Umgebungsvariable/`.env`/Parameter angegeben werden muss (Schritt 4 der
[Konfiguration](#konfiguration)).

```powershell
Export-BondruckerApiKey [[-ApiKey] <SecureString>] [-WhatIf] [-Confirm]
```

- **`-ApiKey`** *(optional, `SecureString`)* – wird der Parameter weggelassen, fragt das
  Cmdlet den Key interaktiv per `Read-Host -AsSecureString` ab (Eingabe wird nicht
  angezeigt).
- Speicherort: `~/.config/Bondrucker/ApiKey.xml` (macOS/Linux) bzw.
  `%APPDATA%\Bondrucker\ApiKey.xml` (Windows), verschlüsselt per `Export-Clixml`
  (an den aktuellen Benutzer/Rechner gebunden – die Datei lässt sich nicht einfach auf
  einen anderen Rechner/Benutzer kopieren und dort entschlüsseln).
- `SupportsShouldProcess` (`ConfirmImpact = 'Low'`): `-WhatIf` zeigt nur an, dass die Datei
  geschrieben würde, ohne sie tatsächlich zu schreiben.

**Beispiele**

```powershell
# Interaktiv abfragen und speichern
Export-BondruckerApiKey

# Ohne Eingabeaufforderung speichern
Export-BondruckerApiKey -ApiKey (ConvertTo-SecureString 'mein-key' -AsPlainText -Force)
```

### Get-BondruckerHealth

`GET /health` – Liveness-Check, **ohne API-Key**.

```powershell
Get-BondruckerHealth [-BaseUrl <String>] [-ApiKey <String>] [-TimeoutSec <Int32> = 30]
```

**Rückgabewert**: `PSCustomObject` mit `status`.

```powershell
PS> Get-BondruckerHealth

status
------
ok
```

### Get-BondruckerTemplate

`GET /api/templates` – konfigurierte Druckvorlagen auflisten (Key, Anzeigename, Typ,
Standard-Icon). Damit lässt sich z. B. ermitteln, welche `-Template`-Werte für
[`New-BondruckerJob`](#new-bondruckerjob) gültig sind.

```powershell
Get-BondruckerTemplate [-BaseUrl <String>] [-ApiKey <String>] [-TimeoutSec <Int32> = 30]
```

**Rückgabewert**: Array von Objekten mit `key`, `name`, `type`, `icon` (`TemplateInfo`,
siehe [`../openapi.yaml`](../openapi.yaml)).

```powershell
PS> Get-BondruckerTemplate

key       name          type      icon
---       ----          ----      ----
todo      Aufgabenliste todo      fa-list-check
freitext  Freitext      freitext
```

### Get-BondruckerIcon

`GET /api/icons` – verfügbare Font-Awesome-Icon-Namen auflisten (für `-Icon` bei
[`New-BondruckerJob`](#new-bondruckerjob) / [`Get-BondruckerPreview`](#get-bondruckerpreview)).

```powershell
Get-BondruckerIcon [-BaseUrl <String>] [-ApiKey <String>] [-TimeoutSec <Int32> = 30]
```

**Rückgabewert**: Array von Strings, z. B. `fa-cart-shopping`, `fa-list-check`, ...

### Get-BondruckerPrinterStatus

`GET /api/printer/status` – Drucker-Konnektivität und aktuelle Warteschlange.

```powershell
Get-BondruckerPrinterStatus [-BaseUrl <String>] [-ApiKey <String>] [-TimeoutSec <Int32> = 30]
```

**Rückgabewert**: `PSCustomObject` mit:

| Feld | Typ | Bedeutung |
|---|---|---|
| `online` | `bool` | Ob der Drucker aktuell erreichbar ist. |
| `queue_length` | `int` | Anzahl wartender/aktiver Aufträge. |
| `current_job` | `string` oder `null` | ID des gerade verarbeiteten Auftrags, falls vorhanden. |

### Get-BondruckerJob

`GET /api/jobs` bzw. `GET /api/jobs/{id}` – Druckaufträge auflisten oder einen einzelnen
Auftrag abrufen.

```powershell
Get-BondruckerJob [[-JobId] <String>] [-Status <String>] `
    [-BaseUrl <String>] [-ApiKey <String>] [-TimeoutSec <Int32> = 30]
```

- **`-JobId`** *(optional, Position 0)* – ruft `GET /api/jobs/{JobId}` ab (einzelner
  Auftrag).
- **`-Status`** *(optional)* – filtert die Liste (`GET /api/jobs?status=...`). Gültige
  Werte: `queued`, `printing`, `failed`, `completed`, `cancelled`.
- **`-JobId`** und **`-Status`** sind **exklusiv** – werden beide angegeben, wirft das
  Cmdlet:

  ```
  JobId und Status sind exklusiv - JobId fuer einen einzelnen Auftrag, Status fuer die Liste.
  ```

**Rückgabewert**: `PrintJobResponse`-Objekt(e) – siehe [`../openapi.yaml`](../openapi.yaml).
Für Aufträge im Status `completed` sind `template`, `title`, `icon`, `markdown` und
`error_message` immer `null` (Inhalte werden nach erfolgreichem Druck aus der Datenbank
gelöscht – siehe [`security.md`](../security.md)).

**Beispiele**

```powershell
# Alle Aufträge
Get-BondruckerJob

# Nur wartende Aufträge
Get-BondruckerJob -Status queued

# Einzelnen Auftrag abrufen
Get-BondruckerJob -JobId 3f9e1c2a-...
```

### New-BondruckerJob

`POST /api/jobs` – neuen Druckauftrag anlegen und in die Warteschlange einreihen.

```powershell
New-BondruckerJob [-Template] <String> [[-Title] <String>] [[-Icon] <String>] `
    [[-Markdown] <String>] [[-MarkdownFile] <String>] [-NoTimestamp] `
    [[-ImagePath] <String>] [[-QrCode] <String>] `
    [-BaseUrl <String>] [-ApiKey <String>] [-TimeoutSec <Int32> = 30] [-WhatIf] [-Confirm]
```

| Parameter | Pflicht | Beschreibung |
|---|---|---|
| `-Template` | ja | Key einer konfigurierten Vorlage, z. B. `todo` oder `freitext` (siehe [`Get-BondruckerTemplate`](#get-bondruckertemplate)). |
| `-Title` | nein | Titel, der über dem Inhalt gedruckt wird. |
| `-Icon` | nein | Font-Awesome-Icon-Name, z. B. `fa-cart-shopping` (siehe [`Get-BondruckerIcon`](#get-bondruckericon)). Ohne Angabe wird ggf. das Standard-Icon der Vorlage verwendet. |
| `-Markdown` | nein | Markdown-Inhalt als Text. Exklusiv zu `-MarkdownFile`. |
| `-MarkdownFile` | nein | Pfad zu einer Datei, deren Inhalt als Markdown gesendet wird. Exklusiv zu `-Markdown`. |
| `-NoTimestamp` | nein | Unterdrückt den Zeitstempel unten rechts (Default: Zeitstempel **wird** gedruckt, d. h. `print_timestamp = $true`). |
| `-ImagePath` | nein | Pfad zu einer Bilddatei (`.png`/`.jpg`/`.jpeg`/`.gif`/`.bmp`/`.webp`), wird base64-kodiert als `image_base64` gesendet (max. 7.000.000 Zeichen, siehe [`../openapi.yaml`](../openapi.yaml)). Exklusiv zu `-QrCode`. |
| `-QrCode` | nein | Inhalt für einen QR-Code (URL, `WIFI:...`, vCard, `geo:...`, max. 2.000 Zeichen). Exklusiv zu `-ImagePath`. |

Werden `-Markdown` und `-MarkdownFile` bzw. `-ImagePath` und `-QrCode` zusammen angegeben,
wirft das Cmdlet jeweils:

```
Markdown und MarkdownFile sind exklusiv - nur eines von beiden angeben.
ImagePath und QrCode sind exklusiv - nur eines von beiden angeben.
```

`SupportsShouldProcess` (`ConfirmImpact = 'Low'`) – siehe [-WhatIf / -Confirm](#-whatif---confirm).

**Rückgabewert**: das neu angelegte `PrintJobResponse`-Objekt (Status zunächst `queued`).

**Beispiele**

```powershell
# Aufgabenliste mit Checkboxen
New-BondruckerJob -Template todo -Title 'Einkaufsliste' -Icon fa-cart-shopping `
    -Markdown "- [ ] Milch`n- [x] Brot"

# Freitext mit QR-Code (z. B. WLAN-Zugangsdaten)
New-BondruckerJob -Template freitext -Title 'WLAN' `
    -QrCode 'WIFI:T:WPA;S:MeinNetz;P:geheim;;'

# Inhalt aus Datei, ohne Zeitstempel
New-BondruckerJob -Template freitext -Title 'Notiz' -MarkdownFile notiz.md -NoTimestamp

# Vorab prüfen, ohne den Auftrag tatsächlich anzulegen
New-BondruckerJob -Template todo -Title 'Test' -Markdown '- [ ] Punkt' -WhatIf
```

### Stop-BondruckerJob

`DELETE /api/jobs/{id}` – Druckauftrag abbrechen. Funktioniert nur für Aufträge im Status
`queued` oder `failed`; für andere Status liefert die API einen Fehler (siehe
[`../openapi.yaml`](../openapi.yaml)).

```powershell
Stop-BondruckerJob [-JobId] <String> `
    [-BaseUrl <String>] [-ApiKey <String>] [-TimeoutSec <Int32> = 30] [-WhatIf] [-Confirm]
```

`SupportsShouldProcess` (`ConfirmImpact = 'Medium'`) – siehe [-WhatIf / -Confirm](#-whatif---confirm).

**Rückgabewert**: das aktualisierte `PrintJobResponse`-Objekt (Status `cancelled`).

**Beispiel**

```powershell
Stop-BondruckerJob -JobId 3f9e1c2a-...

# Mit Bestätigungsabfrage
Stop-BondruckerJob -JobId 3f9e1c2a-... -Confirm
```

### Get-BondruckerPreview

`POST /api/preview` – rendert dieselbe Eingabe wie [`New-BondruckerJob`](#new-bondruckerjob)
als PNG-Vorschau, **ohne** einen Druckauftrag anzulegen oder etwas zu drucken.

```powershell
Get-BondruckerPreview [-Template] <String> [[-Title] <String>] [[-Icon] <String>] `
    [[-Markdown] <String>] [[-MarkdownFile] <String>] [-NoTimestamp] `
    [[-ImagePath] <String>] [[-QrCode] <String>] `
    -OutFile <String> `
    [-BaseUrl <String>] [-ApiKey <String>] [-TimeoutSec <Int32> = 30]
```

- Nimmt **dieselben Inhalts-Parameter** wie `New-BondruckerJob` entgegen, inklusive der
  Exklusivitätsregeln (`-Markdown`/`-MarkdownFile`, `-ImagePath`/`-QrCode`).
- **`-OutFile`** *(Pflicht)* – Zielpfad für die PNG-Datei (wird überschrieben, falls
  bereits vorhanden).
- Kein `SupportsShouldProcess` – das Cmdlet erzeugt keinen Druckauftrag und unterstützt
  daher kein `-WhatIf`/`-Confirm`.

**Rückgabewert**: `System.IO.FileInfo` der geschriebenen PNG-Datei (`Get-Item`).

**Beispiel**

```powershell
Get-BondruckerPreview -Template freitext -Title 'Test' -Markdown '# Überschrift' `
    -OutFile preview.png
```

## -WhatIf / -Confirm

[`New-BondruckerJob`](#new-bondruckerjob) (`ConfirmImpact = 'Low'`) und
[`Stop-BondruckerJob`](#stop-bondruckerjob) (`ConfirmImpact = 'Medium'`) sowie
[`Export-BondruckerApiKey`](#export-bondruckerapikey) (`ConfirmImpact = 'Low'`)
implementieren `SupportsShouldProcess`:

- **`-WhatIf`** zeigt an, welche Aktion ausgeführt würde, **ohne** den HTTP-Request zu
  senden.
- **`-Confirm`** erzwingt eine interaktive Bestätigung vor der Ausführung, unabhängig vom
  `ConfirmImpact`-Wert.
- Ohne `-Confirm` fragt PowerShell standardmäßig **nicht** nach, da der Default von
  `$ConfirmPreference` (`High`) über `Low`/`Medium` liegt. Wer für `Stop-BondruckerJob`
  generell eine Bestätigung möchte, kann `$ConfirmPreference = 'Medium'` in der Sitzung
  setzen.
