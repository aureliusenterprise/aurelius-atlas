#!/bin/bash
set -euo pipefail

# Smoke test for the devcontainer CI image.
#
# Runs INSIDE the built dev container (via devcontainers/ci's runCmd) as the
# gate before an image is pushed. It asserts the image is a complete, working
# Aurelius Atlas toolchain: every tool a CI job needs is present, at the
# expected version, and the baked Playwright browsers actually launch.
#
# Keep this script free of repository deps - it runs before any job-specific
# setup, and it must work on a bare checkout.

fail() {
    echo "::error::$*"
    exit 1
}

check_cmd() {
    local name="$1"
    shift
    if command -v "$name" >/dev/null 2>&1; then
        printf '%-16s %s\n' "$name:" "$("$@" 2>&1 | head -1)"
    else
        fail "$name is not on PATH - the image is missing a required tool"
    fi
}

# Like check_cmd but prints the LAST line of the version output (nx prints a
# "Nx Version:" label on the first line, the version is below it).
check_cmd_last() {
    local name="$1"
    shift
    if command -v "$name" >/dev/null 2>&1; then
        printf '%-16s %s\n' "$name:" "$("$@" 2>&1 | tail -1)"
    else
        fail "$name is not on PATH - the image is missing a required tool"
    fi
}

echo "=== Aurelius Atlas devcontainer smoke test ==="

check_cmd node node --version
check_cmd npm npm --version
check_cmd python python3 --version
check_cmd uv uv --version
check_cmd java java -version
check_cmd_last nx nx --version
check_cmd sops sops --version
check_cmd trivy trivy --version
check_cmd cyclonedx cyclonedx --version
check_cmd mkcert mkcert --version
# Azure/Kubernetes CLIs for the self-hosted CI infra (infra/arc).
# az prints "azure-cli 2.x" first; kubelogin prints the git hash last.
check_cmd az az --version
check_cmd kubectl kubectl version --client
check_cmd helm helm version
check_cmd_last kubelogin kubelogin --version
# cosign prints a banner; report the GitVersion line. sonar-scanner logs to
# stderr; report the version token.
command -v cosign >/dev/null 2>&1 || fail "cosign is not on PATH - the image is missing a required tool"
printf '%-16s %s\n' "cosign:" "$(cosign version 2>/dev/null | grep -i gitversion | head -1 | awk '{print $2}')"
command -v sonar-scanner >/dev/null 2>&1 || fail "sonar-scanner is not on PATH - the image is missing a required tool"
printf '%-16s %s\n' "sonar-scanner:" "$(sonar-scanner --version 2>&1 | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)"

# Docker: the devcontainer DinD feature installs engine + CLI. dockerd is
# started by docker-init.sh (the feature entrypoint); the CLI must be usable.
check_cmd docker docker --version
docker compose version | head -1
docker info --format 'docker daemon: {{.ServerVersion}}' ||
    fail "docker daemon is not reachable inside the container"

# Playwright browsers are baked by the playwright-browsers feature. The baked
# version MUST match the version uv.lock pins, or tests fail with a cryptic
# "browser not found" at runtime.
BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:?PLAYWRIGHT_BROWSERS_PATH must be set by the image}"
BAKED="$(cat "$BROWSERS_PATH/.playwright-version" 2>/dev/null || echo "none")"
PINNED="$(sed -n '/^name = "playwright"$/,/^version = /p' uv.lock 2>/dev/null |
    sed -n 's/^version = "\(.*\)"$/\1/p' | head -1)"

if [ -z "$PINNED" ]; then
    echo "::warning::could not read the playwright pin from uv.lock - skipping the version guard"
elif [ "$BAKED" != "$PINNED" ]; then
    fail "baked Playwright browsers are $BAKED but uv.lock pins $PINNED - bump the playwright-browsers feature version in .devcontainer/devcontainer.json"
fi
echo "playwright:      baked=$BAKED uv.lock=$PINNED (match)"

# Prove every browser the test matrix uses really launches (chromium, firefox,
# webkit). This is the expensive check, and the reason baking is worth it.
# uv run resolves the workspace venv (the playwright version CI tests use);
# plain python3 is the fallback for a venv-less checkout.
if command -v uv >/dev/null 2>&1 && [ -d .venv ]; then
    PYRUN=(uv run python)
else
    PYRUN=(python3)
fi
"${PYRUN[@]}" - <<'PY'
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("::error::playwright python package is not importable in the image")

with sync_playwright() as p:
    for name in ("chromium", "firefox", "webkit"):
        browser = getattr(p, name).launch()
        page = browser.new_page()
        page.goto("about:blank")
        print(f"{name:<16} launch OK ({browser.version})")
        browser.close()
PY

echo "=== smoke test passed ==="
