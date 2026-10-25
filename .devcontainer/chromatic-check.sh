#!/usr/bin/env bash
# Chromatic-job command for CI, run INSIDE the dev container (see ci.yaml).
#
# Chromatic only publishes aurelius-atlas-ui's Storybook, so skip the build
# when the UI (or its dependencies) are not affected, and report the result
# via the job's step output ($GITHUB_OUTPUT is mounted into the container by
# devcontainers/ci). The build output lands in dist/, in the mounted
# checkout, where the host-side Chromatic step uploads it.
set -euo pipefail

if npx nx affected -t build-storybook --graph=stdout |
    jq -e '.tasks.tasks | has("aurelius-atlas-ui:build-storybook")' >/dev/null; then
    npx nx build-storybook aurelius-atlas-ui
    echo "ui-affected=true" >>"$GITHUB_OUTPUT"
else
    echo "ui-affected=false" >>"$GITHUB_OUTPUT"
fi
