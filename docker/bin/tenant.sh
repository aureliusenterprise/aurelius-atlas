#!/usr/bin/env bash
# Add a tenant with its people, or manage them, in the running standalone stack (TAD-12, DD-702).
#
# Usage: docker/bin/tenant.sh <command> [arguments]
#
#   add <tenant> [--sample <name>] [--users atlas|all]
#                  make the tenant and <tenant>_atlas, its administrator; --users all adds <tenant>_steward and
#                  <tenant>_scientist; --sample loads that sample into a new tenant
#   user <tenant> add <username> [--role atlas|steward|scientist] [--email <address>]
#   user <tenant> remove <username>
#   samples        the samples you can name with --sample
#   list           the tenants, their state, trust and sample
#   remove <tenant>
#
# Each person the command makes gets a temporary password, printed once below: they set their own at the
# first sign-in (DD-701). Pass it on and keep no copy.
#
# The script runs the server's command `python -m aurelius_atlas_server.provisioning` in the stack's one
# shot `tenants`, which already holds what the command needs — the server's image and settings with tenancy
# on, the provisioning client's secret, the network namespace, the certificates and the sample folder — so it
# copies none of that here. It names no secret: the stack's env files supply them, the same three every start
# command names (DD-669). It edits no file: a tenant and its people live in the store and in Keycloak, which
# the stack keeps until `down -v`.
#
# The stack must already be up, with tenancy on (docker/README.md, Tenants).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"

if [ "$#" -eq 0 ]; then
    sed -n '3,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 2
fi

cd "$root"

COMPOSE_PROFILES=tenancy ATLAS_TENANCY_ENABLED=true exec docker compose \
    -f docker/docker-compose.yaml \
    --env-file apps/aurelius-atlas-server/.env \
    --env-file infra/keycloak/.env \
    --env-file infra/elasticsearch/.env \
    run --rm --no-deps --entrypoint python tenants -m aurelius_atlas_server.provisioning "$@"
