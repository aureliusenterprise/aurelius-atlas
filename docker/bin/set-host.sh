#!/usr/bin/env bash
# Move the standalone stack to a browser host of your own (SPC-03, DD-694).
#
# Usage: docker/bin/set-host.sh <host>
#
#   host  the address a browser types, such as atlas.example or 192.168.1.20.
#
# The stack serves localhost with no host value of its own (SPC-02): the host sits written into
# three files, and this script writes a new one into the same three places and re-issues the edge
# leaf for it (the only leaf that names the browser host, SPS-02). It changes nothing else — every
# internal hop stays a service name or a loopback name.
#
#   docker/gateway/nginx.conf                    the proxy's server_name
#   apps/aurelius-atlas-webapp/docker/config.json the browser's Keycloak URL
#   docker/keycloak/aurelius-atlas.json           the realm's redirect and post-logout URIs
#
# A host change is not a restart: a store that already holds the realm keeps the old host in it,
# because Keycloak imports a realm only into an empty database (SPS-07's path retires with the host
# machinery, DD-694). So after this script, clear the demo:
#
#   docker compose -f docker/docker-compose.yaml down -v
#
# and start the stack again. Point the browser machine's hosts entry or DNS at the machine that
# holds the Docker daemon, and trust docker/certs/ca.pem to quiet the browser warning (SPS-10).
#
# The same thing by hand: edit the three files above and run docker/bin/make-certs.sh with the host.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"

[[ $# -eq 1 && -n "$1" ]] || { echo "usage: ${0##*/} <host>" >&2; exit 2; }
host="$1"

gateway="$root/docker/gateway/nginx.conf"
webapp_config="$root/apps/aurelius-atlas-webapp/docker/config.json"
realm="$root/docker/keycloak/aurelius-atlas.json"

# The host the files carry now, read from the proxy's server_name — the one line that states it.
current="$(sed -n 's/^[[:space:]]*server_name[[:space:]]\{1,\}\([^;]*\);.*/\1/p' "$gateway")"
if [[ -z "$current" ]]; then
    echo "error: $gateway holds no server_name, so the current host cannot be read" >&2
    exit 1
fi
if [[ "$current" == "$host" ]]; then
    echo "the stack already serves $host"
    exit 0
fi

# Every browser-facing host in the three files is the same URL prefix, so one substitution reaches
# all of them and cannot touch an internal hop (those name a service or a loopback port).
prefix="https://${current}:9000"
for file in "$gateway" "$webapp_config" "$realm"; do
    [[ -f "$file" ]] || { echo "error: $file is missing" >&2; exit 1; }
    sed -i.bak "s|${prefix}|https://${host}:9000|g" "$file" && rm -f "$file.bak"
done
# The proxy's own server_name is the line the prefix rule above never matches.
sed -i.bak "s|^\([[:space:]]*\)server_name[[:space:]]\{1,\}${current};|\1server_name ${host};|" "$gateway" &&
    rm -f "$gateway.bak"

echo "wrote $host into:"
for file in "$gateway" "$webapp_config" "$realm"; do
    echo "  ${file#"$root"/}"
done

"$here/make-certs.sh" "$host"

cat <<EOF

The stack now serves https://${host}:9000.
If the stack already ran, the realm in its store still names ${current}: run
  docker compose -f ${root}/docker/docker-compose.yaml down -v
and start the stack again (SPC-03).
EOF
