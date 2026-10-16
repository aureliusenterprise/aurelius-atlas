#!/usr/bin/env bash
set -euo pipefail

# Remove one project's generated TLS material. The certs/ directory itself and
# its .gitignore are kept. The root CA is owned by mkcert (its CAROOT and the
# system trust stores) and is left untouched; to drop it entirely, run
# `mkcert -uninstall` manually. Invoked by the `certclean` target inferred by
# tools/plugins/tls.ts.

project_root="${1:?usage: certclean.sh <project-root>}"
certs_dir="$project_root/certs"

rm -f "$certs_dir"/*.pem "$certs_dir"/*.p12
rm -f "$certs_dir"/.stamp

echo "TLS material removed from $certs_dir"
