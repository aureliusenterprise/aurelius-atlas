#!/usr/bin/env bash
# Install the GitHub Actions runner binaries into the image (Shape A:
# infra/arc/arc-shapea-values.yaml runs this image as the runner pod's
# job container - no devcontainers/ci, no sibling container).
#
# The binaries are the stock release (run.sh, config.sh, bin/Runner,
# externals/ with node24). ARC configures the runner at start through
# ACTIONS_RUNNER_INPUT_JITCONFIG (the chart's registration wiring), so
# nothing is configured at build time and the install is dev-safe: an
# idle runner that nothing launches.
#
# Version pin: ARC 0.15.1 pairs with the runner release its own image
# ships; keep `version` in sync with ghcr.io/actions/actions-runner
# (NOTES.md).
set -e

VERSION="${VERSION:-latest}"
RUNNER_HOME=/opt/actions-runner

if [ "$VERSION" = "latest" ]; then
    VERSION=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest |
        sed -n 's/.*"tag_name": "v\([^"]*\)".*/\1/p')
fi
[ -n "$VERSION" ] || {
    echo "ci-runner: could not resolve runner version" >&2
    exit 1
}

TARBALL="actions-runner-linux-x64-${VERSION}.tar.gz"
BASE="https://github.com/actions/runner/releases/download/v${VERSION}"

# Verify the published sha256 when the release ships one (best-effort:
# the version is pinned and the download is HTTPS; config.sh --version
# at the end gates a corrupt/foreign tarball).
if curl -fsSL "${BASE}/${TARBALL}.sha256" -o /tmp/runner.sha256; then
    curl -fsSL "${BASE}/${TARBALL}" -o "/tmp/${TARBALL}"
    echo "$(tr -d '[:space:]' </tmp/runner.sha256)  /tmp/${TARBALL}" |
        sha256sum -c -
    rm -f /tmp/runner.sha256
else
    echo "ci-runner: no .sha256 published for ${VERSION}, skipping checksum"
    curl -fsSL "${BASE}/${TARBALL}" -o "/tmp/${TARBALL}"
fi

mkdir -p "$RUNNER_HOME"
tar -xzf "/tmp/${TARBALL}" -C "$RUNNER_HOME"
rm -f "/tmp/${TARBALL}"

# The job container runs as the dev container user (vscode): it must own
# the runner home (run.sh writes .runner* marker files there).
CI_USER="${_REMOTE_USER:-}"
if [ -z "$CI_USER" ] || [ "$CI_USER" = "automatic" ]; then
    CI_USER="vscode"
    id -u "$CI_USER" >/dev/null 2>&1 || CI_USER="root"
fi
chown -R "$CI_USER" "$RUNNER_HOME"

# Shape A's entrypoint chain (arc-shapea-values.yaml): docker-init.sh
# (the docker-in-docker feature) then run.sh. Nothing to do for the
# developer container: the image ships no entrypoint, so the dev
# container keeps the CLI's defaults and the runner sits idle.
"${RUNNER_HOME}/config.sh" --version
