# n8n-Node `n8n-nodes-bondrucker`

Community-Node für [n8n](https://n8n.io/) unter
[`scripts/n8n/`](../../scripts/n8n/) – bildet dieselben Endpunkte der
Bondrucker REST-API ([`../openapi.yaml`](../openapi.yaml)) ab wie der
[Python-Client](python.md) und das [PowerShell-Modul](powershell.md):
Druckaufträge anlegen/abrufen/auflisten/abbrechen, Standarddruckobjekte
auflisten und drucken, Druckerstatus/-steckdose abfragen und umschalten,
Vorlagen/Icons auflisten sowie eine PNG-Vorschau rendern.

> **Warum TypeScript?** n8n-Nodes müssen als TypeScript/JavaScript-Paket
> vorliegen (n8n selbst ist eine Node.js-Anwendung und jeder Node
> implementiert das `INodeType`-Interface aus `n8n-workflow`). Es gibt keinen
> unterstützten Weg, einen nativen Custom-Node in Python oder PowerShell zu
> schreiben – anders als die übrigen Clients in [`scripts/`](../../scripts/)
> ist dieser deshalb in TypeScript implementiert, mit Jest als Test-Runner.

Die vollständige Installations-, Bedienungs- und Fehlerbehandlungs-Referenz
(inkl. `setup.sh`-Optionen, Ressourcen/Operationen-Tabelle,
Beispiel-Workflows und Troubleshooting) steht im README des Pakets:

**→ [`scripts/n8n/README.md`](../../scripts/n8n/README.md)**

Dieses Dokument fasst nur die wichtigsten Punkte zusammen und ordnet den Node
in die übrige Dokumentation ein.

## Voraussetzungen

- Node.js ≥ 18 und npm
- Eine selbst gehostete n8n-Instanz, deren Dateisystem/Umgebung zugänglich
  ist (Docker-Container oder lokale Installation)
- Ein erreichbares Bondrucker-Backend und dessen `API_KEY` (siehe
  [`.env.example`](../../.env.example) bzw. [`security.md`](../security.md))

## Installation

```bash
cd scripts/n8n
./setup.sh --container <container-name> --ssh <user@server>   # Docker-Deployment
./setup.sh --local                                             # lokale n8n-Instanz
```

Das Skript installiert Abhängigkeiten, baut das Paket (`npm run build`),
führt die Jest-Tests aus und installiert den Node anschließend in die
n8n-Custom-Extensions (`N8N_CUSTOM_EXTENSIONS`). Details, Flags und die
manuelle Installation ohne `setup.sh` stehen im
[Paket-README](../../scripts/n8n/README.md#1-install-build-test-and-install-the-node).

## Credentials

In n8n unter **Credentials → New → Bondrucker API**:

| Feld    | Wert                                                                 |
|---------|-----------------------------------------------------------------------|
| Host    | Basis-URL des Backends, z. B. `https://backend-bondrucker.bondrucker-app.de` (ohne trailing slash) |
| API Key | Wert aus dem Backend-Setting `API_KEY` (derselbe, den der Server im Header `X-API-Key` erwartet) |

Der **Test**-Button ruft `GET /api/templates` auf und prüft damit Host und
API-Key.

## Ressourcen und Operationen

| Ressource | Operationen                          |
|-----------|----------------------------------------|
| Job       | Create, Get, Get Many, Cancel          |
| Preset    | Get Many, Print                        |
| Printer   | Get Status, Get Power, Toggle Power    |
| Template  | Get Many                               |
| Icon      | Get Many                               |
| Preview   | Create (rendert PNG, ohne Auftrag anzulegen) |
| Health    | Check                                  |

Die vollständige Feld-Referenz je Operation (inkl. der `Additional Fields`
für Icon/Print Timestamp/Image/QR-Code sowie Beispiel-Workflows) steht im
[Paket-README](../../scripts/n8n/README.md#3-using-the-bondrucker-node).

## Tests

```bash
cd scripts/n8n
npm test
```

Die Suite mockt den n8n-Ausführungskontext (`getNodeParameter`,
`getCredentials`, `helpers.httpRequestWithAuthentication`,
`helpers.prepareBinaryData`) und deckt alle Ressourcen/Operationen sowie die
Fehlerbehandlung (401, `continueOnFail`) ab.
