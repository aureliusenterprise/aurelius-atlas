#!/bin/bash
set -euo pipefail

# Bakes the Playwright browser binaries into the image at PLAYWRIGHT_BROWSERS_PATH
# so neither the dev container nor the CI runner downloads them at runtime.
# The browser set is fixed (chromium, firefox, webkit) to match the test matrix;
# the system packages the browsers need come from the playwright-deps feature.

VERSION="${VERSION:-1.64.0}"
BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/opt/playwright-browsers}"

export PLAYWRIGHT_BROWSERS_PATH="$BROWSERS_PATH"

mkdir -p "$BROWSERS_PATH"

# The Playwright CLI ships with the Python package; install it temporarily -
# the image's runtime Playwright comes from the workspace venv (uv.lock).
python3 -m pip install --quiet --root-user-action=ignore "playwright==${VERSION}"
python3 -m playwright install chromium firefox webkit
python3 -m pip uninstall --yes --quiet playwright

# Record the baked version so the CI image build can assert it matches uv.lock.
echo "$VERSION" >"$BROWSERS_PATH/.playwright-version"

# World-readable: browsers are baked as root, consumed by the remote user.
chmod -R a+rX "$BROWSERS_PATH"

# Clean up
python3 -m pip cache purge || true
apt-get clean
rm -rf /var/lib/apt/lists/*
