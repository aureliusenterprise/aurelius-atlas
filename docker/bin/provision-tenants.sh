#!/usr/bin/env bash
# Provision the demo tenants in the running standalone stack (SPC-07, DD-697).
#
# Usage: docker/bin/provision-tenants.sh
#
# The always-on stack starts no provisioning: `tenants` sits behind the compose profile `tenancy`,
# so nothing is provisioned unless a person asks for it. This script asks Compose to run that one
# shot once, which keeps the service's own wiring — its network namespace, its certificates, its
# sample folder and its waits for Keycloak and the store — in the compose pieces and copies none of
# it here. The script names no secret: the stack's env files supply them, the same three every start
# command names (DD-669).
#
# The stack must already be up (docker/README.md, Start). The one shot provisions the tenant `demo`
# with the sample `TENANT_SAMPLE` (sample_data.zip by default) and the tenant `meyn` without one,
# their organizations and role groups included, and gives the platform an `operator` user in the
# store. A tenant already provisioned is left as it is, so a repeat run changes nothing.
#
# Tenancy is a server setting, so the running server has to serve it too. To turn it on:
#
#   ATLAS_TENANCY_ENABLED=true docker compose -f docker/docker-compose.yaml \
#       --env-file apps/aurelius-atlas-server/.env --env-file infra/keycloak/.env \
#       --env-file infra/elasticsearch/.env up -d
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"

cd "$root"

COMPOSE_PROFILES=tenancy ATLAS_TENANCY_ENABLED=true exec docker compose \
    -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env \
    --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env \
    run --rm tenants
