#!/usr/bin/env bash
# CI pipeline for Aurelius Atlas, run INSIDE the dev container (see ci.yaml).
#
# Fail-fast phases, cheapest first, external services last, so a change that
# fails a local phase never reaches Chromatic or SonarQube:
#
#   0/5 hygiene   prune the warm daemon's containers/volumes (Shape A
#                 parity with the hosted runners' fresh daemons)
#   1/5 validate  pre-commit over the whole tree
#   2/5 test      unit + e2e tests for affected projects
#   3/5 scan      build images for affected projects, then vulnerability-scan
#   4/5 storybook build Storybook when the UI is affected (the host-side
#                 Chromatic step uploads it after this script)
#   5/5 sonar     SonarQube analysis for affected projects
#
# Everything runs in ONE container on ONE Docker daemon: e2e containers, built
# images, and reports all live on the mounted checkout / shared daemon, so
# later phases see what earlier phases produced. $GITHUB_OUTPUT is mounted in
# by devcontainers/ci; the ui-affected line tells the host Chromatic step
# whether to run.
set -euo pipefail

echo "::group::0/5 Daemon hygiene (prune stale containers)"
# Shape A keeps the dockerd IMAGE store warm on a PVC (base layers survive
# the per-pod wipe - that is the point), which also keeps the previous
# run's CONTAINERS: `compose up` reuses a stopped container verbatim, so
# its baked command is the previous commit's. Run 40231127680 proved it -
# postgres died on the pre-fix cert command, and keycloak's container was
# 2 hours old. The ephemeral checkout (ci.yaml) sanitizes the tree, not
# the daemon. Containers/volumes go, images stay: GitHub-hosted parity
# for state the tests own, warm store for state they don't.
docker container prune -f
docker volume prune -af
echo "::endgroup::"

echo "::group::1/5 Validate (pre-commit)"
uv run pre-commit run --all-files
echo "::endgroup::"

echo "::group::2/5 Test affected projects"
# Diagnostics are collected here, not as a host step: the e2e containers run
# on the dev container's own Docker daemon (the docker-in-docker feature),
# which the host daemon never sees. reports/ works because the container
# mounts the checkout.
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
echo "::endgroup::"

echo "::group::3/5 Build and scan docker images"
# Layer cache is registry-backed (GHCR buildcache tags,
# tools/plugins/docker.ts); the scan reads the images from the daemon that
# built them, minutes earlier, in this same container.
npx nx affected -t docker-build -c ci
npx nx affected -t docker-vuln-scan -c sarif
echo "::endgroup::"

echo "::group::4/5 Storybook (for Chromatic)"
# Chromatic only publishes aurelius-atlas-ui's Storybook, so skip the build
# when the UI (or its dependencies) are not affected. dist/ lands in the
# mounted checkout, where the host-side Chromatic step uploads it.
if npx nx affected -t build-storybook --graph=stdout |
    jq -e '.tasks.tasks | has("aurelius-atlas-ui:build-storybook")' >/dev/null; then
    npx nx build-storybook aurelius-atlas-ui
    echo "ui-affected=true" >>"$GITHUB_OUTPUT"
else
    echo "ui-affected=false" >>"$GITHUB_OUTPUT"
fi
echo "::endgroup::"

echo "::group::5/5 SonarQube analysis"
# Decrypt every project, not just the affected ones: with task-based
# affected, decrypt only counts as affected when .env.enc changes, and a
# .env that the sonar run decrypts itself is written after Nx has loaded the
# task env, so sonar-scanner would run without SONAR_TOKEN ("Not authorized").
npx nx run-many -t decrypt
npx nx affected -t sonar
echo "::endgroup::"
