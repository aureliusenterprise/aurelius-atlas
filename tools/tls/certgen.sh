#!/usr/bin/env bash
set -euo pipefail

# Generate one project's local development TLS material. The shared local root
# CA is mkcert's own root CA, which lives in mkcert's store (its CAROOT) and
# is installed into the system trust stores; every project's material lands in
# its own certs/ directory: leaf certificates it presents, optional PKCS12
# keystores and truststore, and a copy of the CA bundle so the project mounts
# everything from its own directory (removable as a whole slice, ADR 002). Leaves are
# issued with `openssl` against the mkcert root (see issue_leaf) so they carry
# both serverAuth and clientAuth extended key usages.
# Passwords for PKCS12 material come from the project's decrypted .env
# (TLS_TRUSTSTORE_PASSWORD — a SOPS-encrypted per-project dev default).
# Configuration (services and SANs) lives in the project's tls.json.
# Invoked by the `certgen` target inferred by tools/plugins/tls.ts: the
# target runs it with its project root.

# The root CA has no workspace home: mkcert owns it in its CAROOT
# (~/.local/share/mkcert by default), outside the repo and gitignored by
# definition. Projects consume a copy of rootCA.pem in their own certs/.
ca_root="$(mkcert -CAROOT)"

# Install the local root CA into the system and NSS trust stores (idempotent)
# and copy it into the consuming project's certs/. Containers do not trust it
# automatically; they mount ca.pem instead.
# mkcert is not safe to run concurrently (its CAROOT generation and system
# trust-store import race), and Nx runs certgen for every project in
# parallel, so the CA bootstrap is guarded by an exclusive lock in CAROOT.
# Every project run bootstraps under the same lock, so runs are
# self-sufficient and order-independent, and it is a cheap no-op once the CA
# exists.
bootstrap_ca() {
    mkdir -p "$ca_root"
    exec 9>"$ca_root/.certgen.lock"
    flock 9
    mkcert -install
    # Copies to consuming projects happen under the same lock: mkcert -install
    # (re)writes rootCA.pem, and a concurrent copy would otherwise read it
    # truncated.
    local dest
    for dest in "$@"; do
        cmp -s "$ca_root/rootCA.pem" "$dest" || cp "$ca_root/rootCA.pem" "$dest"
    done
    flock -u 9
}

project_root="${1:?usage: certgen.sh <project-root>}"
config="$project_root/tls.json"
certs_dir="$project_root/certs"

if [[ ! -f "$config" ]]; then
    echo "error: $config not found — run from the workspace root" >&2
    exit 1
fi

mkdir -p "$certs_dir"
bootstrap_ca "$certs_dir/ca.pem"

# Issue one leaf certificate signed by the local root CA, usable for BOTH
# server and client authentication. mkcert's own leaves carry serverAuth only,
# so a TLS peer that checks extended key usage rejects them as client
# certificates (Kafka's ssl.client.auth=required fails with "Extended key
# usage does not permit use for TLS client authentication"). Issuing here keeps
# the same mkcert root — already installed into the system trust store — while
# setting both usages. Fresh key and serial per call, like mkcert.
issue_leaf() {
    local cert="$1" key="$2"
    shift 2
    local cn
    cn=$(basename "$cert" .pem)
    local sans=() san
    for san in "$@"; do
        if [[ "$san" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
            sans+=("IP:$san")
        elif [[ "$san" == *:* ]]; then
            sans+=("$san") # explicit type prefix (DNS:, IP:, email:)
        else
            sans+=("DNS:$san")
        fi
    done
    local ext
    ext=$(mktemp)
    {
        printf '[leaf]\n'
        printf 'basicConstraints = critical, CA:FALSE\n'
        printf 'keyUsage = critical, digitalSignature, keyEncipherment\n'
        printf 'extendedKeyUsage = serverAuth, clientAuth\n'
        printf 'subjectAltName = %s\n' "$(IFS=,; printf '%s' "${sans[*]}")"
    } >"$ext"
    openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:prime256v1 -out "$key"
    openssl req -new -key "$key" -subj "/CN=$cn" -out "$key.csr"
    openssl x509 -req -in "$key.csr" \
        -CA "$ca_root/rootCA.pem" -CAkey "$ca_root/rootCA-key.pem" \
        -set_serial "0x$(openssl rand -hex 8)" -days 825 \
        -extfile "$ext" -extensions leaf -out "$cert" 2>/dev/null
    rm -f "$key.csr" "$ext"
}

read_password() {
    local env_file="$project_root/.env"
    if [[ ! -f "$env_file" ]]; then
        echo "error: $env_file not found — run 'nx decrypt $project_root' first" >&2
        exit 1
    fi
    local password
    # `|| true` on the grep: under `set -euo pipefail` a no-match (exit 1) in a
    # command substitution would abort the script via pipefail before the
    # explicit missing-password diagnostic below can run.
    password=$({ grep -m1 '^TLS_TRUSTSTORE_PASSWORD=' "$env_file" || true; } | cut -d= -f2- |
        sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'\$//")
    if [[ -z "$password" ]]; then
        echo "error: TLS_TRUSTSTORE_PASSWORD missing from $env_file" >&2
        exit 1
    fi
    printf '%s' "$password"
}

need_keystore=$(jq -r '.keystore // false' "$config")
need_truststore=$(jq -r '.truststore // false' "$config")

password=""
if [[ "$need_keystore" == "true" || "$need_truststore" == "true" ]]; then
    password=$(read_password)
fi

# Idempotency: mkcert issues a fresh leaf on every invocation (new key, new
# notBefore), so re-running unconditionally would rewrite material that
# running services have bind-mounted — their in-memory leaves then no longer
# match what clients verify against, and their TLS healthchecks fail. A
# fingerprint of everything the material is derived from (root CA, manifest,
# PKCS12 password, and this script itself, so changing how material is issued
# regenerates every project) is recorded in certs/.stamp after each generation;
# when it still matches and the material is present, chains to the current CA,
# and is not near expiry, there is nothing to do. Deleting the material (or
# certclean) fails the checks and regenerates it.
stamp_file="$certs_dir/.stamp"
fingerprint=$(cat "$ca_root/rootCA.pem" "$config" "$0" | sha256sum | cut -d' ' -f1)
fingerprint+=$(printf '%s' "$password" | sha256sum | cut -d' ' -f1)

material_current() {
    [[ -f "$stamp_file" && "$(<"$stamp_file")" == "$fingerprint" ]] || return 1
    local service
    while read -r service; do
        [[ -z "$service" ]] && continue
        [[ -f "$certs_dir/$service.pem" && -f "$certs_dir/$service-key.pem" ]] || return 1
        if [[ "$need_keystore" == "true" && ! -f "$certs_dir/$service.p12" ]]; then
            return 1
        fi
    done < <(jq -r '.services | keys[]' "$config")
    if [[ "$need_truststore" == "true" && ! -f "$certs_dir/truststore.p12" ]]; then
        return 1
    fi
    while read -r service; do
        [[ -z "$service" ]] && continue
        openssl x509 -in "$certs_dir/$service.pem" -noout -checkend 86400 >/dev/null 2>&1 || return 1
        openssl verify -CAfile "$certs_dir/ca.pem" "$certs_dir/$service.pem" >/dev/null 2>&1 || return 1
    done < <(jq -r '.services | keys[]' "$config")
    return 0
}

if material_current; then
    echo "TLS material for $project_root already current in $certs_dir"
    exit 0
fi

# Per-service material: PEM leaf + key for non-JVM consumers, PKCS12 keystore
# (leaf + key + CA chain) for JVM consumers when keystore is requested.
# Keys are group/world readable so non-root service containers (whose users
# differ per image) can mount them; they protect only local development
# traffic, per ADR 006. NEVER ship this directory anywhere the material
# outlives the machine: it is dev identity (mTLS client certs since PR #130), so never
# tar/archive `certs/` into artifacts, reports, or support bundles, and never
# COPY it into an image (the root .dockerignore enforces this). Everything under
# it is git-ignored (certs/.gitignore). Services that enforce stricter
# permissions (e.g. Postgres) copy them and tighten the mode at startup.
while read -r service; do
    [[ -z "$service" ]] && continue
    mapfile -t sans < <(jq -r --arg s "$service" ".services[\$s][]" "$config")
    issue_leaf "$certs_dir/$service.pem" "$certs_dir/$service-key.pem" "${sans[@]}"
    chmod 644 "$certs_dir/$service-key.pem"
    if [[ "$need_keystore" == "true" ]]; then
        openssl pkcs12 -export -name "$service" \
            -in "$certs_dir/$service.pem" -inkey "$certs_dir/$service-key.pem" \
            -certfile "$certs_dir/ca.pem" \
            -out "$certs_dir/$service.p12" -passout "pass:$password"
        chmod 644 "$certs_dir/$service.p12"
    fi
done < <(jq -r '.services | keys[]' "$config")

# JVM truststore holding only the root CA, for clients (Kafka clients, JDBC
# drivers, Schema Registry clients, Keycloak's OTLP sender) that verify servers.
if [[ "$need_truststore" == "true" ]]; then
    rm -f "$certs_dir/truststore.p12"
    keytool -importcert -alias aurelius-dev-ca -file "$certs_dir/ca.pem" \
        -keystore "$certs_dir/truststore.p12" -storetype PKCS12 \
        -storepass "$password" -noprompt
    chmod 644 "$certs_dir/truststore.p12"
fi

printf '%s' "$fingerprint" >"$stamp_file"
echo "TLS material for $project_root written to $certs_dir"
