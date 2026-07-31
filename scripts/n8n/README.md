# n8n-nodes-bondrucker

An **n8n community node** for the Bondrucker REST API (see
[`../../docs/openapi.yaml`](../../docs/openapi.yaml)) — the same API the
[PowerShell module](../powershell/), [Python client](../python/), and
[Home Assistant integration](../homeassistant/) in this repo talk to. It
covers the same "client-parity" surface as those: creating/listing/cancelling
print jobs, printing presets, checking/toggling the printer, listing
templates/icons, rendering a preview, and the health check.

> **Note on "TypeScript"**: n8n custom nodes must be written in TypeScript/
> JavaScript — n8n itself is a Node.js application and every node has to
> implement the `INodeType` interface from `n8n-workflow`. There is no
> supported way to write a native custom node in Python or PowerShell. Its
> automated test suite uses **Jest** (the standard for n8n node packages).

## Contents

```
scripts/n8n/
├── credentials/
│   └── BondruckerApi.credentials.ts # Host + API key, sent as the "X-API-Key" header
├── nodes/Bondrucker/
│   ├── Bondrucker.node.ts           # Node UI + execute() logic (all resources/operations)
│   ├── GenericFunctions.ts          # HTTP client + error handling (401 etc.) + loadOptions dropdowns
│   ├── Bondrucker.node.json         # n8n codex metadata
│   └── bondrucker.png               # Node icon (../../icon.png)
├── test/
│   ├── GenericFunctions.test.ts     # Unit tests for the HTTP client, error handling, loadOptions
│   └── Bondrucker.node.test.ts      # Unit tests for every resource/operation
├── setup.sh                         # Install, build, test, and link into a local/Docker n8n instance
├── package.json / tsconfig.json / jest.config.js / gulpfile.js / .eslintrc.js
└── README.md
```

## Requirements

- Node.js >= 18 and npm
- A running n8n instance (self-hosted) you control the filesystem/env of
- A reachable Bondrucker backend and its `API_KEY` (see
  [`../../.env.example`](../../.env.example) and
  [`../../docs/security.md`](../../docs/security.md))

## 1. Install, build, test, and install the node

From this directory (`scripts/n8n`):

```bash
./setup.sh --container <container-name-or-id> --ssh <user@server>
```

This will:

1. Verify Node.js/npm are available (Node >= 18 required)
2. Run `npm install`
3. Compile TypeScript and copy the node icon (`npm run build`)
4. Run the Jest test suite (`npm test`) — pass `--no-tests` to skip
5. `npm pack` the built package and `docker cp` the tarball into the
   container
6. `npm install` the tarball inside the container's custom-extensions
   folder (default `/home/node/.n8n/custom`, override with `--custom-dir`)
7. Restart the container so n8n picks up the new node (skip with
   `--no-restart`)

If you're running the script directly on the Docker host (no SSH hop
needed), omit `--ssh`:

```bash
./setup.sh --container <container-name-or-id>
```

The script checks whether the container's `N8N_CUSTOM_EXTENSIONS` env var
already includes the custom-extensions folder. If it doesn't, `docker exec`
can't fix that — the container's env is fixed at creation time. In that
case, add `N8N_CUSTOM_EXTENSIONS=/home/node/.n8n/custom` to the container's
`docker run -e` args or `docker-compose.yml`, then recreate it
(`docker compose up -d` / `docker rm` + `docker run`), not just restart it.

Then, in the n8n editor UI, add a node and search for **"Bondrucker"**.

### Installing into a local n8n instance instead

If you want to test against a local n8n install (not the Docker
deployment), use `--local` instead of `--container`:

```bash
./setup.sh --local              # links into ~/.n8n/custom
./setup.sh --local --n8n-dir /path/to/n8n/home
```

This links the package (like `npm link`) instead of copying a tarball, so
rebuilding picks up changes without re-running `setup.sh`. At the end it
prints the exact steps to point n8n at the linked package:

```bash
export N8N_CUSTOM_EXTENSIONS="$HOME/.n8n/custom"
n8n start
```

### Manual install (without setup.sh)

```bash
npm install
npm run build
npm test
npm pack                                    # -> n8n-nodes-bondrucker-<version>.tgz
docker cp n8n-nodes-bondrucker-*.tgz <container>:/tmp/
docker exec <container> sh -c '
  mkdir -p /home/node/.n8n/custom && cd /home/node/.n8n/custom
  [ -f package.json ] || npm init -y
  npm install /tmp/n8n-nodes-bondrucker-*.tgz
'
docker restart <container>
```

For a remote Docker host, prefix the `docker`/`docker cp` commands with
`DOCKER_HOST=ssh://user@server` instead of `docker cp`+`scp`ing manually —
the Docker CLI streams the file over the SSH connection.

## 2. Configure credentials in n8n

1. In n8n, go to **Credentials → New → Bondrucker API**.
2. Fill in:
   - **Host**: the backend base URL, e.g.
     `https://backend-bondrucker.bondrucker-app.de` (no trailing slash)
   - **API Key**: the backend's `API_KEY` setting — the same value clients
     send in the `X-API-Key` header (see
     [`../../.env.example`](../../.env.example))
3. Click **Test** — this calls `GET /api/templates` and confirms the host and
   API key are valid.

## 3. Using the "Bondrucker" node

The node exposes seven resources:

| Resource | Operations                          | Backend endpoint(s)                                   |
|----------|--------------------------------------|---------------------------------------------------------|
| Job      | Create, Get, Get Many, Cancel        | `POST/GET /api/jobs`, `GET/DELETE /api/jobs/{id}`      |
| Preset   | Get Many, Print                      | `GET /api/presets`, `POST /api/presets/{key}/print`    |
| Printer  | Get Status, Get Power, Toggle Power  | `GET /api/printer/status`, `GET/POST /api/printer/power(/toggle)` |
| Template | Get Many                             | `GET /api/templates`                                    |
| Icon     | Get Many                             | `GET /api/icons`                                         |
| Preview  | Create (renders a PNG, no job created)| `POST /api/preview`                                     |
| Health   | Check                                | `GET /health` (no API key required)                      |

**Job: Create** and **Preview: Create** share the same fields, since they
send the same payload (`docs/openapi.yaml`'s `PrintJobCreate`): **Template**
(dropdown, populated via `GET /api/templates`), **Title**, **Markdown**, and
an **Additional Fields** collection with **Icon** (dropdown, populated via
`GET /api/icons`), **Print Timestamp**, **Image (Base64)**, and **QR Code**
(the latter two are mutually exclusive — the backend rejects a request
setting both). **Preview: Create** additionally asks for an **Output Binary
Field** name (default `data`) that the rendered PNG is attached to, ready to
feed into e.g. a **Send Email** or **Write Binary File** node.

**Job: Get Many** supports **Status** (`Queued`/`Printing`/`Failed`/
`Completed`/`Cancelled`/`All`) and either **Return All** or a **Limit** — the
status filter is applied server-side via the `status` query parameter; the
limit is applied client-side after fetching (the API has no page size
parameter).

**Preset: Print** and **Job: Get**/**Cancel** take a **Preset**/**Job ID**
field; Preset is a dropdown populated via `GET /api/presets`, Job ID is a
plain string field (job IDs are UUIDs, not sequential numbers).

### Example workflow

`Manual Trigger → Bondrucker (Preset: Print "wlan-qrcode") → Bondrucker (Job: Get)`

1. **Preset: Print**: Preset `wlan-qrcode`
2. **Job: Get**: Job ID `={{$json.id}}` (from the Print step's output)

Or, to render a preview before printing:

`Manual Trigger → Bondrucker (Preview: Create) → Bondrucker (Job: Create)`

## Error handling

`GenericFunctions.bondruckerApiRequest` normalizes failures into n8n's error
types so they surface clearly in the editor and in `continueOnFail` mode:

- **HTTP 401** → `NodeApiError` with a message pointing at the credentials
  (API key mismatch with the backend's `API_KEY` setting).
- Any other HTTP/transport failure (400 validation errors, 404 unknown
  job/preset, 409 invalid job state, 503 printer/Home Assistant
  unreachable, ...) → generic `NodeApiError` carrying the backend's error
  detail.

With **"Continue on Fail"** enabled on the node, failed items are emitted as
`{ error: "<message>" }` instead of stopping the workflow.

## Running the tests

```bash
npm test              # run once
npm run test:watch    # watch mode
npm run test:coverage # with coverage report
```

The suite (`test/GenericFunctions.test.ts`, `test/Bondrucker.node.test.ts`)
mocks n8n's `IExecuteFunctions` context (`getNodeParameter`, `getCredentials`,
`helpers.httpRequestWithAuthentication`, `helpers.prepareBinaryData`,
`continueOnFail`) and covers:

- Correct HTTP method/URL/body/query-string for every resource and operation
- The `X-API-Key` header being applied via the credential's declarative
  `authenticate`
- `Job: Create`/`Preview: Create` payload building, including omitting empty
  optional fields
- `Job: Get Many` status filtering and limit truncation
- `Preview: Create` requesting a binary (`arraybuffer`) response and
  attaching it via `prepareBinaryData`
- 401 / generic error handling
- `continueOnFail` behavior (errors captured as item JSON vs. thrown)
- Multiple input items processed independently
- The `loadOptions` dropdown helpers (Template/Preset/Icon)

## Linting & formatting

```bash
npm run lint     # eslint-plugin-n8n-nodes-base community node rules
npm run format   # prettier
```

## Troubleshooting

- **Node doesn't show up in n8n**: confirm the container's
  `N8N_CUSTOM_EXTENSIONS` env var points at the folder `setup.sh` installed
  into (`docker exec <container> printenv N8N_CUSTOM_EXTENSIONS`), and that
  `npm run build` ran after any code change (n8n loads from `dist/`, not
  from the TypeScript sources) — re-run `./setup.sh --container ...` to
  rebuild and reinstall.
- **`setup.sh` says the container's `N8N_CUSTOM_EXTENSIONS` doesn't include
  the custom dir**: env vars can't be added to a running container via
  `docker exec`; add it to the container's `docker run -e` args or
  `docker-compose.yml` and recreate the container (not just restart it).
- **`docker cp`/`docker exec` fails with a connection error over `--ssh`**:
  confirm you can `ssh <user@server>` manually and that user is in the
  `docker` group (or is root) on that host.
- **401 Unauthorized**: double-check the **API Key** field matches the
  backend's `API_KEY` setting exactly (see `.env` on the backend host).
- **404/503 on printer operations**: `PrinterPower`/`PrinterPowerToggle`
  require `HOMEASSISTANT_URL`/`HOMEASSISTANT_TOKEN` to be configured on the
  backend (see [`../../docs/configuration.md`](../../docs/configuration.md));
  without them the backend returns `503`.
