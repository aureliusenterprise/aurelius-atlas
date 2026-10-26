#!/usr/bin/env bash
# The TEST phase of the Aurelius Atlas CI pipeline, run INSIDE the dev
# container (see ci.yaml). The pipeline itself is spread over named workflow
# steps for readable logs (validate -> test -> teardown -> build ->
# storybook -> scan -> sonar -> chromatic); this script is the test step:
# the unit + e2e suites for the affected projects, container-agnostic.
#
# Diagnostics are collected here, not as a host step: the e2e containers run
# on the dev container's own Docker daemon (the docker-in-docker feature),
# which the host daemon never sees. reports/ works because the container
# mounts the checkout.
#
# Startup sweep: a job whose pod is evicted mid-run (scale-set deploy) never
# reaches the workflow's "Tear down test containers" step, so the next job
# would start on a daemon full of foreign containers - and compose REUSES
# the ones whose config matches (run 40231127680: postgres died on a 2h-old
# pre-fix container). Sweeping at startup closes that gap; on a normal job
# it is a no-op, the previous job's teardown already ran.
set -euo pipefail

docker container prune -f
docker volume prune -af

if ! npx nx affected -t test e2e -c ci; then
    mkdir -p reports/failure-diagnostics
    docker ps --all --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" \
        >reports/failure-diagnostics/container-status.txt 2>&1 || true
    for project in $(docker compose ls --all -q); do
        echo "Collecting logs for project: $project"
        docker compose --project-name "$project" logs --no-color \
            >"reports/failure-diagnostics/${project}-logs.txt" 2>&1 || true
    done
    exit 1
fi
