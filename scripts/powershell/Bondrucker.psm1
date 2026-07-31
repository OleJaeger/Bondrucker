#Requires -Version 7.0

<#
    Bondrucker.psm1 - PowerShell-Modul fuer die Bondrucker REST-API.

    Siehe docs/openapi.yaml fuer die vollstaendige API-Spezifikation.

    Konfiguration der Basis-URL (in dieser Reihenfolge):

      1. Expliziter Parameter -BaseUrl auf den einzelnen Funktionen.
      2. Umgebungsvariable BONDRUCKER_API_URL.
      3. .env im Projekt-Wurzelverzeichnis (ein Verzeichnis ueber scripts/): BONDRUCKER_API_URL.
      4. Default: http://localhost:8000.

    Konfiguration des API-Keys (in dieser Reihenfolge):

      1. Expliziter Parameter -ApiKey auf den einzelnen Funktionen.
      2. Umgebungsvariable BONDRUCKER_API_KEY.
      3. Per Export-BondruckerApiKey hinterlegter Key, verschluesselt per
         Export-Clixml unter ~/.config/Bondrucker/ApiKey.xml bzw.
         %APPDATA%\Bondrucker\ApiKey.xml gespeichert.
      4. Nur als Fallback: .env im Projekt-Wurzelverzeichnis (ein Verzeichnis
         ueber scripts/), BONDRUCKER_API_KEY bzw. alternativ das dort
         bereits vorhandene API_KEY (derselbe Wert, den der Server von
         Clients im Header X-API-Key erwartet).

      Ansonsten gibt es keinen Default - der API-Key muss ueber eine der
      obigen Quellen gesetzt werden (ausser fuer Get-BondruckerHealth, das
      keine Authentifizierung benoetigt).

    Verwendung:

        Import-Module ./scripts/powershell/Bondrucker.psd1

        # Einmalig: API-Key dauerhaft fuer den aktuellen Benutzer speichern.
        Export-BondruckerApiKey

        Get-BondruckerHealth
        Get-BondruckerTemplate
        Get-BondruckerIcon
        Get-BondruckerPrinterStatus
        Get-BondruckerJob -Status queued
        Get-BondruckerJob -JobId <id>

        New-BondruckerJob -Template todo -Title 'Einkaufsliste' `
            -Icon fa-cart-shopping -Markdown "- [ ] Milch`n- [x] Brot"

        Stop-BondruckerJob -JobId <id>

        Get-BondruckerPreview -Template freitext -Markdown '# Test' -OutFile preview.png

        Get-BondruckerPreset
        Invoke-BondruckerPreset -Key wlan-qrcode
#>

Set-StrictMode -Version Latest

$script:DefaultBaseUrl = 'https://backend-bondrucker.bondrucker-app.de'
$script:JobStatuses = 'queued', 'printing', 'failed', 'completed', 'cancelled'

# --- Interne Hilfsfunktionen -----------------------------------------------------

function ConvertFrom-DotEnvFile {
    <#
        .SYNOPSIS
        Liest einfache KEY=VALUE-Zeilen aus einer .env-Datei.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $result = @{}
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $result
    }

    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $trimmed.Contains('=')) {
            continue
        }

        $parts = $trimmed.Split('=', 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()

        if ($value.Length -ge 2 -and $value[0] -eq $value[-1] -and ($value[0] -eq '"' -or $value[0] -eq "'")) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $result[$key] = $value
    }

    return $result
}

function Get-BondruckerCredentialPath {
    <#
        .SYNOPSIS
        Pfad zur Datei mit dem per Export-BondruckerApiKey gespeicherten API-Key.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param()

    if ($IsWindows) {
        $configDir = Join-Path $env:APPDATA 'Bondrucker'
    } else {
        $configDir = Join-Path $HOME '.config/Bondrucker'
    }

    Join-Path $configDir 'ApiKey.xml'
}

function Import-BondruckerApiKey {
    <#
        .SYNOPSIS
        Liest den per Export-BondruckerApiKey gespeicherten API-Key, falls vorhanden.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param()

    $path = Get-BondruckerCredentialPath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        return $null
    }

    try {
        (Import-Clixml -Path $path) | ConvertFrom-SecureString -AsPlainText
    } catch {
        Write-Verbose "Gespeicherter API-Key konnte nicht gelesen werden: $_"
        $null
    }
}

function Get-BondruckerConfig {
    <#
        .SYNOPSIS
        Loest Basis-URL und API-Key gemaess der Prioritaetsreihenfolge auf.
    #>
    [CmdletBinding()]
    param(
        [string]$BaseUrl,
        [string]$ApiKey
    )

    $envFilePath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) '.env'
    $envFile = ConvertFrom-DotEnvFile -Path $envFilePath

    if (-not $BaseUrl) { $BaseUrl = $env:BONDRUCKER_API_URL }
    if (-not $BaseUrl) { $BaseUrl = $envFile['BONDRUCKER_API_URL'] }
    if (-not $BaseUrl) { $BaseUrl = $script:DefaultBaseUrl }

    if (-not $ApiKey) { $ApiKey = $env:BONDRUCKER_API_KEY }
    if (-not $ApiKey) { $ApiKey = Import-BondruckerApiKey }
    if (-not $ApiKey) { $ApiKey = $envFile['BONDRUCKER_API_KEY'] }
    if (-not $ApiKey) { $ApiKey = $envFile['API_KEY'] }

    [PSCustomObject]@{
        BaseUrl = $BaseUrl.TrimEnd('/')
        ApiKey  = $ApiKey
    }
}

function Get-BondruckerErrorDetail {
    <#
        .SYNOPSIS
        Extrahiert eine lesbare Fehlermeldung aus einem fehlgeschlagenen Invoke-*-Aufruf.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        $ErrorRecord
    )

    $statusCode = $null
    if ($ErrorRecord.Exception.Response) {
        $statusCode = [int]$ErrorRecord.Exception.Response.StatusCode
    }

    $bodyText = $null
    if ($ErrorRecord.ErrorDetails -and $ErrorRecord.ErrorDetails.Message) {
        $bodyText = $ErrorRecord.ErrorDetails.Message
    }

    $detail = $bodyText
    if ($bodyText) {
        try {
            $json = $bodyText | ConvertFrom-Json -ErrorAction Stop
            if ($null -ne $json.detail) {
                if ($json.detail -is [string]) {
                    $detail = $json.detail
                } else {
                    $detail = ($json.detail | ConvertTo-Json -Depth 10 -Compress)
                }
            }
        } catch {
            # Body war kein JSON - Rohtext wird unverändert verwendet.
        }
    }

    if (-not $detail) {
        $detail = $ErrorRecord.Exception.Message
    }

    if ($statusCode) {
        "HTTP ${statusCode}: $detail"
    } else {
        $detail
    }
}

function Invoke-BondruckerRequest {
    <#
        .SYNOPSIS
        Fuehrt einen authentifizierten HTTP-Request gegen die Bondrucker-API aus.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Method,

        [Parameter(Mandatory)]
        [string]$Path,

        [hashtable]$QueryParameters,

        $Body,

        [switch]$NoAuth,

        [switch]$Raw,

        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    $config = Get-BondruckerConfig -BaseUrl $BaseUrl -ApiKey $ApiKey

    $uri = "$($config.BaseUrl)$Path"
    if ($QueryParameters) {
        $pairs = foreach ($key in $QueryParameters.Keys) {
            $value = $QueryParameters[$key]
            if ($null -ne $value -and "$value" -ne '') {
                "$([uri]::EscapeDataString($key))=$([uri]::EscapeDataString("$value"))"
            }
        }
        if ($pairs) {
            $uri = "$uri?$($pairs -join '&')"
        }
    }

    $headers = @{}
    if (-not $NoAuth) {
        if (-not $config.ApiKey) {
            throw 'Kein API-Key konfiguriert. Setze BONDRUCKER_API_KEY oder API_KEY ' +
                '(z.B. in der .env im Projekt-Wurzelverzeichnis) oder uebergib -ApiKey.'
        }
        $headers['X-API-Key'] = $config.ApiKey
    }

    $invokeParams = @{
        Method     = $Method
        Uri        = $uri
        Headers    = $headers
        TimeoutSec = $TimeoutSec
    }

    if ($null -ne $Body) {
        $invokeParams['Body'] = ($Body | ConvertTo-Json -Depth 10)
        $invokeParams['ContentType'] = 'application/json'
    }

    try {
        if ($Raw) {
            $response = Invoke-WebRequest @invokeParams
            return $response.Content
        }

        return Invoke-RestMethod @invokeParams
    } catch [Microsoft.PowerShell.Commands.HttpResponseException] {
        throw (Get-BondruckerErrorDetail -ErrorRecord $_)
    } catch {
        throw $_.Exception.Message
    }
}

function ConvertTo-BondruckerImageDataUrl {
    <#
        .SYNOPSIS
        Liest eine Bilddatei und gibt eine base64 data:-URL fuer image_base64 zurueck.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $resolvedPath = Resolve-Path -LiteralPath $Path
    $bytes = [System.IO.File]::ReadAllBytes($resolvedPath)

    $mimeType = switch ([System.IO.Path]::GetExtension($resolvedPath.Path).ToLowerInvariant()) {
        '.png'  { 'image/png' }
        '.jpg'  { 'image/jpeg' }
        '.jpeg' { 'image/jpeg' }
        '.gif'  { 'image/gif' }
        '.bmp'  { 'image/bmp' }
        '.webp' { 'image/webp' }
        default { 'application/octet-stream' }
    }

    $encoded = [Convert]::ToBase64String($bytes)
    "data:${mimeType};base64,$encoded"
}

function New-BondruckerJobPayload {
    <#
        .SYNOPSIS
        Baut den JSON-Body fuer POST /api/jobs bzw. POST /api/preview.
    #>
    [CmdletBinding()]
    [OutputType([System.Collections.Specialized.OrderedDictionary])]
    param(
        [Parameter(Mandatory)]
        [string]$Template,

        [string]$Title = '',
        [string]$Icon,
        [string]$Markdown = '',
        [string]$MarkdownFile,
        [switch]$NoTimestamp,
        [string]$ImagePath,
        [string]$QrCode
    )

    if ($MarkdownFile -and $Markdown) {
        throw 'Markdown und MarkdownFile sind exklusiv - nur eines von beiden angeben.'
    }
    if ($ImagePath -and $QrCode) {
        throw 'ImagePath und QrCode sind exklusiv - nur eines von beiden angeben.'
    }

    $markdownContent = $Markdown
    if ($MarkdownFile) {
        $markdownContent = Get-Content -LiteralPath $MarkdownFile -Raw
    }

    $body = [ordered]@{
        template        = $Template
        print_timestamp = -not $NoTimestamp
    }
    if ($Title) { $body['title'] = $Title }
    if ($Icon) { $body['icon'] = $Icon }
    if ($markdownContent) { $body['markdown'] = $markdownContent }
    if ($ImagePath) { $body['image_base64'] = ConvertTo-BondruckerImageDataUrl -Path $ImagePath }
    if ($QrCode) { $body['qr_code'] = $QrCode }

    return $body
}

# --- Oeffentliche Funktionen ------------------------------------------------------

function Export-BondruckerApiKey {
    <#
        .SYNOPSIS
        Speichert den Bondrucker-API-Key verschluesselt fuer den aktuellen Benutzer.
        .DESCRIPTION
        Der Key wird per Export-Clixml unter ~/.config/Bondrucker/ApiKey.xml bzw.
        %APPDATA%\Bondrucker\ApiKey.xml abgelegt (siehe Get-BondruckerCredentialPath)
        und von Get-BondruckerConfig als letzter Fallback verwendet, wenn weder
        -ApiKey-Parameter, Umgebungsvariablen noch .env einen API-Key liefern.
        .EXAMPLE
        Export-BondruckerApiKey
        .EXAMPLE
        Export-BondruckerApiKey -ApiKey (ConvertTo-SecureString 'mein-key' -AsPlainText -Force)
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Low')]
    param(
        [securestring]$ApiKey
    )

    if (-not $ApiKey) {
        $ApiKey = Read-Host -Prompt 'Bondrucker API-Key' -AsSecureString
    }

    $path = Get-BondruckerCredentialPath
    $directory = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -Path $directory -ItemType Directory -Force | Out-Null
    }

    if ($PSCmdlet.ShouldProcess($path, 'API-Key speichern')) {
        $ApiKey | Export-Clixml -Path $path -Force
    }
}

function Get-BondruckerHealth {
    <#
        .SYNOPSIS
        GET /health - Liveness-Check, ohne API-Key.
        .EXAMPLE
        Get-BondruckerHealth
    #>
    [CmdletBinding()]
    param(
        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    Invoke-BondruckerRequest -Method Get -Path '/health' -NoAuth `
        -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
}

function Get-BondruckerTemplate {
    <#
        .SYNOPSIS
        GET /api/templates - konfigurierte Druckvorlagen auflisten.
        .EXAMPLE
        Get-BondruckerTemplate
    #>
    [CmdletBinding()]
    param(
        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    Invoke-BondruckerRequest -Method Get -Path '/api/templates' `
        -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
}

function Get-BondruckerIcon {
    <#
        .SYNOPSIS
        GET /api/icons - verfuegbare Font-Awesome-Icon-Namen auflisten.
        .EXAMPLE
        Get-BondruckerIcon
    #>
    [CmdletBinding()]
    param(
        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    Invoke-BondruckerRequest -Method Get -Path '/api/icons' `
        -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
}

function Get-BondruckerPreset {
    <#
        .SYNOPSIS
        GET /api/presets - konfigurierte Standarddruckobjekte auflisten.
        .EXAMPLE
        Get-BondruckerPreset
    #>
    [CmdletBinding()]
    param(
        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    Invoke-BondruckerRequest -Method Get -Path '/api/presets' `
        -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
}

function Invoke-BondruckerPreset {
    <#
        .SYNOPSIS
        POST /api/presets/{key}/print - Standarddruckobjekt drucken und einreihen.
        .EXAMPLE
        Invoke-BondruckerPreset -Key wlan-qrcode
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Low')]
    param(
        [Parameter(Mandatory, Position = 0)]
        [string]$Key,

        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    if ($PSCmdlet.ShouldProcess($Key, 'Standarddruckobjekt drucken')) {
        Invoke-BondruckerRequest -Method Post -Path "/api/presets/$([uri]::EscapeDataString($Key))/print" `
            -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
    }
}

function Get-BondruckerPrinterStatus {
    <#
        .SYNOPSIS
        GET /api/printer/status - Drucker-Konnektivitaet und Warteschlange.
        .EXAMPLE
        Get-BondruckerPrinterStatus
    #>
    [CmdletBinding()]
    param(
        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    Invoke-BondruckerRequest -Method Get -Path '/api/printer/status' `
        -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
}

function Get-BondruckerJob {
    <#
        .SYNOPSIS
        GET /api/jobs bzw. GET /api/jobs/{id} - Druckauftraege auflisten oder abrufen.
        .EXAMPLE
        Get-BondruckerJob
        .EXAMPLE
        Get-BondruckerJob -Status queued
        .EXAMPLE
        Get-BondruckerJob -JobId 3f9e...
    #>
    [CmdletBinding()]
    param(
        [Parameter(Position = 0)]
        [string]$JobId,

        [ValidateSet('queued', 'printing', 'failed', 'completed', 'cancelled')]
        [string]$Status,

        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    if ($JobId) {
        if ($Status) {
            throw 'JobId und Status sind exklusiv - JobId fuer einen einzelnen Auftrag, Status fuer die Liste.'
        }
        Invoke-BondruckerRequest -Method Get -Path "/api/jobs/$([uri]::EscapeDataString($JobId))" `
            -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
    } else {
        $query = @{}
        if ($Status) { $query['status'] = $Status }
        Invoke-BondruckerRequest -Method Get -Path '/api/jobs' -QueryParameters $query `
            -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
    }
}

function New-BondruckerJob {
    <#
        .SYNOPSIS
        POST /api/jobs - neuen Druckauftrag anlegen und einreihen.
        .DESCRIPTION
        ImagePath und QrCode sind exklusiv, ebenso Markdown und MarkdownFile.
        .EXAMPLE
        New-BondruckerJob -Template todo -Title 'Einkaufsliste' -Icon fa-cart-shopping -Markdown "- [ ] Milch`n- [x] Brot"
        .EXAMPLE
        New-BondruckerJob -Template freitext -Title 'WLAN' -QrCode 'WIFI:T:WPA;S:MeinNetz;P:geheim;;'
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Low')]
    param(
        [Parameter(Mandatory)]
        [string]$Template,

        [string]$Title = '',
        [string]$Icon,
        [string]$Markdown = '',
        [string]$MarkdownFile,
        [switch]$NoTimestamp,
        [string]$ImagePath,
        [string]$QrCode,

        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    $body = New-BondruckerJobPayload -Template $Template -Title $Title -Icon $Icon `
        -Markdown $Markdown -MarkdownFile $MarkdownFile -NoTimestamp:$NoTimestamp `
        -ImagePath $ImagePath -QrCode $QrCode

    if ($PSCmdlet.ShouldProcess($Template, 'Druckauftrag anlegen')) {
        Invoke-BondruckerRequest -Method Post -Path '/api/jobs' -Body $body `
            -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
    }
}

function Stop-BondruckerJob {
    <#
        .SYNOPSIS
        DELETE /api/jobs/{id} - Druckauftrag abbrechen (nur Status 'queued' oder 'failed').
        .EXAMPLE
        Stop-BondruckerJob -JobId 3f9e...
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
    param(
        [Parameter(Mandatory, Position = 0)]
        [string]$JobId,

        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    if ($PSCmdlet.ShouldProcess($JobId, 'Druckauftrag abbrechen')) {
        Invoke-BondruckerRequest -Method Delete -Path "/api/jobs/$([uri]::EscapeDataString($JobId))" `
            -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
    }
}

function Get-BondruckerPrinterPower {
    <#
        .SYNOPSIS
        GET /api/printer/power - Aktuellen Steckdosen-Zustand abrufen.
        .EXAMPLE
        Get-BondruckerPrinterPower
    #>
    [CmdletBinding()]
    param(
        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    Invoke-BondruckerRequest -Method Get -Path '/api/printer/power' `
        -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
}

function Invoke-BondruckerPrinterPower {
    <#
        .SYNOPSIS
        POST /api/printer/power/toggle - Steckdose umschalten und neuen Zustand zurueckgeben.
        .EXAMPLE
        Invoke-BondruckerPrinterPower
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
    param(
        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    if ($PSCmdlet.ShouldProcess('switch.plug_016', 'Steckdose umschalten')) {
        Invoke-BondruckerRequest -Method Post -Path '/api/printer/power/toggle' `
            -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec
    }
}

function Get-BondruckerPreview {
    <#
        .SYNOPSIS
        POST /api/preview - PNG-Vorschau rendern, ohne einen Druckauftrag anzulegen.
        .DESCRIPTION
        ImagePath und QrCode sind exklusiv, ebenso Markdown und MarkdownFile.
        .EXAMPLE
        Get-BondruckerPreview -Template freitext -Markdown '# Test' -OutFile preview.png
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Template,

        [string]$Title = '',
        [string]$Icon,
        [string]$Markdown = '',
        [string]$MarkdownFile,
        [switch]$NoTimestamp,
        [string]$ImagePath,
        [string]$QrCode,

        [Parameter(Mandatory)]
        [string]$OutFile,

        [string]$BaseUrl,
        [string]$ApiKey,
        [int]$TimeoutSec = 30
    )

    $body = New-BondruckerJobPayload -Template $Template -Title $Title -Icon $Icon `
        -Markdown $Markdown -MarkdownFile $MarkdownFile -NoTimestamp:$NoTimestamp `
        -ImagePath $ImagePath -QrCode $QrCode

    $bytes = Invoke-BondruckerRequest -Method Post -Path '/api/preview' -Body $body -Raw `
        -BaseUrl $BaseUrl -ApiKey $ApiKey -TimeoutSec $TimeoutSec

    $resolvedPath = $PSCmdlet.GetUnresolvedProviderPathFromPSPath($OutFile)
    [System.IO.File]::WriteAllBytes($resolvedPath, $bytes)

    Get-Item -LiteralPath $resolvedPath
}

Export-ModuleMember -Function @(
    'Export-BondruckerApiKey'
    'Get-BondruckerHealth'
    'Get-BondruckerTemplate'
    'Get-BondruckerIcon'
    'Get-BondruckerPreset'
    'Invoke-BondruckerPreset'
    'Get-BondruckerPrinterStatus'
    'Get-BondruckerPrinterPower'
    'Invoke-BondruckerPrinterPower'
    'Get-BondruckerJob'
    'New-BondruckerJob'
    'Stop-BondruckerJob'
    'Get-BondruckerPreview'
)
