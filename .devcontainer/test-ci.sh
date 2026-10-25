#!/usr/bin/env bash
# Test-job command for CI, run INSIDE the dev container (see ci.yaml).
#
# Diagnostics must be collected here, not as a host step: the e2e containers
# run on the dev container's own Docker daemon (the docker-in-docker feature),
# which is torn down when the step ends - the host daemon never sees them.
# Writing to reports/ works because the container mounts the checkout.
set -uo pipefail

if npx nx affected -t test e2e -c ci; then
    exit 0
fi

mkdir -p reports/failure-diagnostics
docker ps --all --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" \
    >reports/failure-diagnostics/container-status.txt 2>&1 || true
for project in $(docker compose ls --all -q); do
    echo "Collecting logs for project: $project"
    docker compose --project-name "$project" logs --no-color \
        >"reports/failure-diagnostics/${project}-logs.txt" 2>&1 || true
done
exit 1
