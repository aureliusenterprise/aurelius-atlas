#!/usr/bin/env bash
# Import the sample into the running standalone stack (SPC-06, DD-697).
#
# Usage: docker/bin/import-sample.sh [zip]
#
#   zip  the export ZIP in the stack's sample folder, sample_data.zip by default.
#
# The always-on stack starts no import: `sample-import` sits behind the compose profile `demo`, so
# nothing imports unless a person asks for it. This script asks Compose to run that one shot once,
# which keeps the service's own wiring — its network namespace, its certificates, its sample folder
# and the wait for the server — in the compose pieces and copies none of it here. The script names
# no secret: the stack's env files supply them, the same three every start command names (DD-669).
#
# The stack must already be up (docker/README.md, Start). The import signs in as the client
# `aurelius-atlas-admin` and posts the ZIP to `admin/import` through the proxy; it logs the import's
# status and its counts by type, and a failed import exits non-zero. An import updates the entities
# it finds by GUID, so running it again is safe.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"

cd "$root"
# COMPOSE_PROFILES opens the service's profile for this run, and SAMPLE_ZIP names the ZIP the one
# shot reads from its sample folder (the service's own variable, apps/aurelius-atlas-server/docker/
# compose.yaml).
COMPOSE_PROFILES=demo SAMPLE_ZIP="${1:-sample_data.zip}" exec docker compose \
    -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env \
    --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env \
    run --rm sample-import
