#!/bin/sh
# Fills the webapp image's nginx template (/etc/nginx/conf.d/default.conf) for the standalone stack into
# /out/default.conf, as the chart's init container does (DD-262), and fails on a placeholder left. The stack's
# proxy sends /api/ to the server itself; the webapp's own /api/ points at the server too, through the proxy's
# network, for a call that reaches the webapp directly.
set -eu
src=/etc/nginx/conf.d/default.conf
out=/out/default.conf
sed \
    -e 's|${AURELIUS_ATLAS_WEBAPP_API_UPSTREAM}|https://proxy:21000|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_API_UPSTREAM_NAME}|aurelius-atlas-server|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_DNS_RESOLVER}|127.0.0.11|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_KEYCLOAK_ORIGINS}||g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_OTEL_UPSTREAM}|https://otel-collector:4318|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_OTEL_UPSTREAM_NAME}|otel-collector|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_OTLP_ENDPOINT}|127.0.0.1:4317|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_REALIP_BLOCK}||g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_TLS_CA_FILE}|/certs/ca.pem|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_TLS_CERT_FILE}|/certs/aurelius-atlas-webapp.pem|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_TLS_KEY_FILE}|/certs/aurelius-atlas-webapp-key.pem|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_OTEL_INGEST_TOKEN}|none|g' \
    -e 's|${AURELIUS_ATLAS_WEBAPP_HSTS_HEADER}||g' \
    "$src" > "$out"
if grep -Eq '\$\{AURELIUS_ATLAS_WEBAPP_[A-Z_]+\}' "$out"; then
    echo "unresolved placeholder in $out:" >&2
    grep -E '\$\{AURELIUS_ATLAS_WEBAPP_[A-Z_]+\}' "$out" >&2
    exit 1
fi
