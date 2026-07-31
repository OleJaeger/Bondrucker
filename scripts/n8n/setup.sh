#!/usr/bin/env bash
#
# Builds the n8n-nodes-bondrucker package and installs it into a running
# n8n Docker container so the "Bondrucker" node shows up in the n8n node panel.
#
# The container can be local or on a remote Docker host reachable via SSH
# (the Docker CLI's ssh:// transport is used, so no manual scp is needed).
#
# Usage:
#   ./setup.sh --container <name> [options]     # install into a Docker container (default deployment)
#   ./setup.sh --local [options]                # install into a local n8n user folder instead
#
# Container mode options:
#   --container <name>   Name or ID of the running n8n container (required)
#   --ssh <user@host>     SSH target of the Docker host, if not local (sets DOCKER_HOST=ssh://user@host)
#   --custom-dir <path>   Custom-extensions folder inside the container (default: /home/node/.n8n/custom)
#   --restart             Restart the container after installing, without asking
#   --no-restart          Don't restart the container after installing, without asking
#                         (if neither is given, the script asks interactively)
#
# Local mode options:
#   --n8n-dir <dir>       n8n user folder to link into (default: ~/.n8n)
#
# Common options:
#   --no-tests            Skip the Jest test run
#   -h, --help            Show this help
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE=""
RUN_TESTS=1
N8N_DIR="${HOME}/.n8n"
CONTAINER=""
SSH_HOST=""
CUSTOM_DIR_IN_CONTAINER="/home/node/.n8n/custom"
RESTART_CONTAINER=1
RESTART_CONTAINER_SET=0

while [[ $# -gt 0 ]]; do
	case "$1" in
		--local)
			MODE="local"
			shift
			;;
		--container)
			MODE="container"
			CONTAINER="$2"
			shift 2
			;;
		--ssh)
			SSH_HOST="$2"
			shift 2
			;;
		--custom-dir)
			CUSTOM_DIR_IN_CONTAINER="$2"
			shift 2
			;;
		--restart)
			RESTART_CONTAINER=1
			RESTART_CONTAINER_SET=1
			shift
			;;
		--no-restart)
			RESTART_CONTAINER=0
			RESTART_CONTAINER_SET=1
			shift
			;;
		--n8n-dir)
			N8N_DIR="$2"
			shift 2
			;;
		--no-tests)
			RUN_TESTS=0
			shift
			;;
		-h|--help)
			grep '^#' "$0" | sed 's/^#//'
			exit 0
			;;
		*)
			echo "Unknown argument: $1" >&2
			exit 1
			;;
	esac
done

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }
fail() { printf '\033[1;31mError:\033[0m %s\n' "$1" >&2; exit 1; }

if [[ -z "$MODE" ]]; then
	fail "Specify a mode: --container <name> (install into the running n8n Docker container) or --local (link into a local n8n user folder). See --help."
fi

command -v node >/dev/null 2>&1 || fail "Node.js is required but was not found in PATH."
command -v npm  >/dev/null 2>&1 || fail "npm is required but was not found in PATH."

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [[ "$NODE_MAJOR" -lt 18 ]]; then
	fail "Node.js >= 18 is required (found $(node -v)). n8n and this package target Node 18+."
fi

cd "$SCRIPT_DIR"

log "Installing dependencies"
npm install

log "Building TypeScript sources"
npm run build

if [[ "$RUN_TESTS" -eq 1 ]]; then
	log "Running the Jest test suite"
	npm test
else
	log "Skipping tests (--no-tests was passed)"
fi

if [[ "$MODE" == "local" ]]; then
	CUSTOM_DIR="${N8N_DIR}/custom"
	mkdir -p "$CUSTOM_DIR"

	log "Linking package into ${CUSTOM_DIR}"
	if [[ ! -f "${CUSTOM_DIR}/package.json" ]]; then
		(cd "$CUSTOM_DIR" && npm init -y >/dev/null)
	fi

	# `npm install <local-path>` creates a real symlink (like `npm link`) so
	# rebuilding this package picks up changes without re-running setup.sh.
	(cd "$CUSTOM_DIR" && npm install "$SCRIPT_DIR" >/dev/null)

	log "Done"
	cat <<EOF

The Bondrucker node is now linked into: ${CUSTOM_DIR}

Next steps:
  1. Set the environment variable so n8n loads community nodes from there:
       export N8N_CUSTOM_EXTENSIONS="${CUSTOM_DIR}"
  2. Start (or restart) n8n:
       n8n start
  3. In the n8n editor, add a node and search for "Bondrucker".
  4. Create "Bondrucker API" credentials:
       - Host:    https://backend-bondrucker.bondrucker-app.de
       - API Key: <the backend's API_KEY setting, see ../../.env.example>

See README.md for details on the credential setup and available operations.
EOF
	exit 0
fi

# --- Container mode ---

command -v docker >/dev/null 2>&1 || fail "docker is required but was not found in PATH."

if [[ -n "$SSH_HOST" ]]; then
	export DOCKER_HOST="ssh://${SSH_HOST}"
	log "Using remote Docker host over SSH: ${SSH_HOST}"
fi

log "Checking container '${CONTAINER}'"
docker version >/dev/null 2>&1 || fail "Cannot reach the Docker daemon${SSH_HOST:+ at ${DOCKER_HOST}}. Check --ssh / Docker access."
RUNNING="$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)"
[[ "$RUNNING" == "true" ]] || fail "Container '${CONTAINER}' was not found or is not running."

log "Packing the built node"
TARBALL="$(npm pack --silent)"
trap 'rm -f "$SCRIPT_DIR/$TARBALL"' EXIT

log "Copying ${TARBALL} into ${CONTAINER}:/tmp/"
docker cp "$TARBALL" "${CONTAINER}:/tmp/${TARBALL}"

log "Installing into ${CUSTOM_DIR_IN_CONTAINER} inside the container"
docker exec "$CONTAINER" sh -c "
	set -e
	mkdir -p '${CUSTOM_DIR_IN_CONTAINER}'
	cd '${CUSTOM_DIR_IN_CONTAINER}'
	[ -f package.json ] || npm init -y >/dev/null
	npm install '/tmp/${TARBALL}'
	rm -f '/tmp/${TARBALL}' 2>/dev/null || true
"

EXISTING_EXT_DIRS="$(docker exec "$CONTAINER" printenv N8N_CUSTOM_EXTENSIONS 2>/dev/null || true)"

if [[ "$RESTART_CONTAINER_SET" -eq 0 ]]; then
	if [[ -t 0 ]]; then
		read -r -p "Restart container '${CONTAINER}' now? [y/N] " REPLY
		case "$REPLY" in
			[yY]|[yY][eE][sS]) RESTART_CONTAINER=1 ;;
			*) RESTART_CONTAINER=0 ;;
		esac
	else
		RESTART_CONTAINER=0
	fi
fi

if [[ "$RESTART_CONTAINER" -eq 1 ]]; then
	log "Restarting ${CONTAINER}"
	docker restart "$CONTAINER" >/dev/null
else
	log "Skipping container restart"
fi

log "Done"
cat <<EOF

The Bondrucker node was installed into ${CONTAINER}:${CUSTOM_DIR_IN_CONTAINER}
EOF

if [[ "$EXISTING_EXT_DIRS" != *"$CUSTOM_DIR_IN_CONTAINER"* ]]; then
	cat <<EOF

WARNING: the container's N8N_CUSTOM_EXTENSIONS is currently:
  "${EXISTING_EXT_DIRS:-<not set>}"
which does not include "${CUSTOM_DIR_IN_CONTAINER}". Docker exec cannot add
environment variables to an already-created container — you need to add
  N8N_CUSTOM_EXTENSIONS=${CUSTOM_DIR_IN_CONTAINER}
to the container's env (docker-compose.yml / docker run -e ...) and recreate
it (docker compose up -d / docker rm + docker run), not just restart it.
EOF
fi

cat <<EOF

Next steps:
  1. In the n8n editor, add a node and search for "Bondrucker".
  2. Create "Bondrucker API" credentials:
       - Host:    https://backend-bondrucker.bondrucker-app.de
       - API Key: <the backend's API_KEY setting, see ../../.env.example>

See README.md for details on the credential setup and available operations.
EOF
