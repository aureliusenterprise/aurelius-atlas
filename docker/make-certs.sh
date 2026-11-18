#!/usr/bin/env bash
# Create the TLS material the standalone stack mounts (SPS-09, DD-681).
#
# Usage: docker/make-certs.sh [host]
#
#   host  the browser host of the stack — the value STANDALONE_HOST will carry (default: localhost).
#         The edge leaf names it beside localhost and 127.0.0.1 (SPS-02); the other leaves never
#         name it (SPS-03) and re-running with a new host re-issues only the edge leaf.
#
# What it makes, in each certificates directory named by certs.txt: <service>.pem and
# <service>-key.pem (leaf and key, serverAuth and clientAuth, as tools/tls/certgen.sh issues them),
# a copy of ca.pem, and — for the identity provider's directory only — truststore.p12, the PKCS12
# the stack's Keycloak JVM dials Postgres and its OTLP exporter with (TLS_TRUSTSTORE_PASSWORD).
# The CA itself lives in docker/certs/ (ca.pem, ca-key.pem — both git-ignored there, like every
# certs/ directory), outside the mount trees so no container ever reads its key.
#
# openssl only, and no system change: unlike `nx certgen` (mkcert), this script never installs the
# CA into a trust store (SPS-09) — the stack trusts it by mount alone, and the browser warns once
# for a private CA, which is expected (SPS-10). Bring your own certificates instead by placing a
# CA and leaves at the same paths and not running this script (DD-681).
#
# Password: the stack's Keycloak opens the truststore with TLS_TRUSTSTORE_PASSWORD, which compose
# interpolates from the stack's env-files (README.md). The script writes the PKCS12 with the same
# value, so the two never disagree: the shell value wins, else the first env-file that defines it.
# A dev checkout defines it in infra/keycloak/.env; an install that ships the stack alone defines it
# in docker/.env, which compose reads on its own. tools/tls/certgen.sh reads the file the same way.
# When nothing defines it, the script makes one and records it in docker/.env (DD-691), so a person
# who follows the bundle README (certificates first, then fill the secrets) starts with one password
# and never types this one.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/.." && pwd)"
host="${1:-localhost}"
ca_dir="$here/certs"

command -v openssl >/dev/null || { echo "error: openssl not found" >&2; exit 1; }

read_password() {
    local env_file password
    if [[ -n "${TLS_TRUSTSTORE_PASSWORD:-}" ]]; then
        printf '%s' "$TLS_TRUSTSTORE_PASSWORD"
        return
    fi
    for env_file in "$root/infra/keycloak/.env" "$here/.env"; do
        [[ -f "$env_file" ]] || continue
        # `|| true` on the grep: under `set -euo pipefail` a no-match (exit 1) inside a command
        # substitution aborts the script through pipefail before the next file can be tried.
        password=$({ grep -m1 '^TLS_TRUSTSTORE_PASSWORD=' "$env_file" || true; } | cut -d= -f2- |
            sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'\$//")
        if [[ -n "$password" ]]; then
            printf '%s' "$password"
            return
        fi
    done
    # A checkout that has not decrypted its env still holds infra/keycloak/.env.enc: name the decrypt command,
    # because inventing a password there would disagree with the encrypted one on the stack's start.
    if [[ -f "$root/infra/keycloak/.env.enc" ]]; then
        echo "error: TLS_TRUSTSTORE_PASSWORD found in neither the environment nor" \
            "infra/keycloak/.env — in a checkout, run 'nx decrypt aurelius-atlas-infra-keycloak' first" >&2
        exit 1
    fi
    # A standalone install names the password nowhere, because the bundle ships the roster empty (SBD-04). The
    # truststore password is internal stack material the operator never types — like the CA key, the script
    # makes it on first run and records it in docker/.env, which compose interpolates on the stack's start, so
    # the store and the JVM always agree.
    password="aurelius-atlas-$(openssl rand -hex 16)"
    local docker_env="$here/.env"
    touch "$docker_env"
    if grep -q '^TLS_TRUSTSTORE_PASSWORD=' "$docker_env"; then
        sed -i.bak "s|^TLS_TRUSTSTORE_PASSWORD=.*|TLS_TRUSTSTORE_PASSWORD=$password|" "$docker_env" && rm -f "$docker_env.bak"
    else
        printf 'TLS_TRUSTSTORE_PASSWORD=%s\n' "$password" >>"$docker_env"
    fi
    printf '%s' "$password"
}

password="$(read_password)"

# The CA, created once (idempotent: a re-run re-issues leaves under the CA that exists).
if [[ ! -f "$ca_dir/ca.pem" ]]; then
    mkdir -p "$ca_dir"
    openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:prime256v1 -out "$ca_dir/ca-key.pem"
    openssl req -x509 -new -key "$ca_dir/ca-key.pem" -subj "/CN=Aurelius Atlas standalone stack" \
        -days 3650 -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign" -out "$ca_dir/ca.pem"
fi

# The manifest's SAN tokens in openssl's form: bare IPv4 becomes IP:, a token carrying its own type
# prefix stays, anything else is DNS:. Duplicates drop, because the default host is localhost and the
# edge line names localhost beside its $HOST token — with the host left at the default, the token
# resolves to localhost and the leaf would otherwise name it twice.
format_sans() {
    local out=() san seen
    for san in "$@"; do
        if [[ "$san" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
            san="IP:$san"
        elif [[ "$san" != *:* ]]; then
            san="DNS:$san"
        fi
        for seen in "${out[@]+"${out[@]}"}"; do
            [[ "$seen" == "$san" ]] && san="" && break
        done
        [[ -n "$san" ]] && out+=("$san")
    done
    IFS=,
    printf '%s' "${out[*]}"
}

# A leaf is current when it exists, is not near expiry, chains to this CA alone, and already carries
# exactly the SANs wanted — so a re-run re-issues nothing, and a new host re-issues only the edge
# leaf (the one line of the manifest naming $HOST). -no-CApath -no-CAfile matter: `openssl verify`
# also searches the machine's trust store, and a leaf from another CA (a dev `nx certgen` leaf, whose
# mkcert root is installed here) passes without them while every service rejects it.
leaf_current() {
    local cert="$1" want="$2" have
    [[ -f "$cert" ]] || return 1
    openssl x509 -in "$cert" -noout -checkend 86400 >/dev/null 2>&1 || return 1
    openssl verify -CAfile "$ca_dir/ca.pem" -no-CApath -no-CAfile "$cert" >/dev/null 2>&1 || return 1
    have="$(openssl x509 -in "$cert" -noout -ext subjectAltName 2>/dev/null |
        tail -n +2 | tr -d ' \n' | sed 's/IPAddress:/IP:/g')"
    [[ "$want" == "$have" ]]
}

# One leaf, signed by the stack's CA, serverAuth and clientAuth (the shape tools/tls/certgen.sh
# issues, so a stack leaf behaves like a dev leaf: the server presents its own as a client too).
issue_leaf() {
    local cert="$1" key="$2" cn="$3"
    shift 3
    local sans ext
    sans="$(format_sans "$@")"
    ext="$(mktemp)"
    {
        printf '[leaf]\n'
        printf 'basicConstraints = critical, CA:FALSE\n'
        printf 'keyUsage = critical, digitalSignature, keyEncipherment\n'
        printf 'extendedKeyUsage = serverAuth, clientAuth\n'
        printf 'subjectAltName = %s\n' "$sans"
    } >"$ext"
    mkdir -p "$(dirname "$cert")"
    openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:prime256v1 -out "$key"
    openssl req -new -key "$key" -subj "/CN=$cn" -out "$key.csr"
    openssl x509 -req -in "$key.csr" -CA "$ca_dir/ca.pem" -CAkey "$ca_dir/ca-key.pem" \
        -set_serial "0x$(openssl rand -hex 8)" -days 825 \
        -extfile "$ext" -extensions leaf -out "$cert" 2>/dev/null
    rm -f "$key.csr" "$ext"
    # Group/world readable: the service containers run as different users per image and mount the
    # key read-only; the material protects local stack traffic only, as the dev material does.
    chmod 644 "$key"
}

while read -r dir service sans_rest; do
    [[ -z "$dir" || "$dir" == \#* ]] && continue
    read -r -a sans <<<"$sans_rest"
    sans=("${sans[@]/\$HOST/$host}") # the manifest's $HOST token names the browser host
    mkdir -p "$root/$dir"
    cp "$ca_dir/ca.pem" "$root/$dir/ca.pem"
    if leaf_current "$root/$dir/$service.pem" "$(format_sans "${sans[@]}")"; then
        echo "current $dir/$service.pem"
        continue
    fi
    issue_leaf "$root/$dir/$service.pem" "$root/$dir/$service-key.pem" "$service" "${sans[@]}"
    echo "issued $dir/$service.pem ($service: ${sans[*]})"
done <"$here/certs.txt"

# The JVM truststore the stack's Keycloak reads (docker/keycloak/compose.yaml's JAVA_OPTS): the CA
# alone in PKCS12 — the shape keytool's -importcert leaves, made with openssl alone.
kc_certs="$root/infra/keycloak/certs"
rm -f "$kc_certs/truststore.p12"
openssl pkcs12 -export -name aurelius-atlas-infra-ca -in "$kc_certs/ca.pem" -nokeys \
    -passout "pass:$password" -out "$kc_certs/truststore.p12"
chmod 644 "$kc_certs/truststore.p12"
echo "wrote infra/keycloak/certs/truststore.p12"

cat <<EOF

TLS material is in place. To run on your own host: run this script with it, then start the stack
with STANDALONE_HOST=$host, and point the browser machine's hosts entry or DNS at the machine.
The truststore was written with the stack's TLS_TRUSTSTORE_PASSWORD. Change it in the stack's
env-files and re-run this script, or the stack's Keycloak fails to open the truststore.
EOF
