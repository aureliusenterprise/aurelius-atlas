#!/usr/bin/env bash
# Cluster validation installer (10.5, CHT-50/51/52).
#
# The runbook (docs/architecture/deployment/runbook.md) §0-2 as code: minikube
# lifecycle, cert-manager, Envoy Gateway (+ the GatewayClass EG ships none of),
# the DD-265 split-horizon CoreDNS patch, the image build-and-load pass (no
# pull secrets on minikube), and the umbrella install with the DD-252
# stuck-release recovery scripted. Every subcommand is idempotent: re-running
# `up` against a live cluster converges and is a no-op when already green.
#
# Subcommands:
#   up        cluster + prereqs + images + install + readiness (all of it)
#   images    build the Aurelius images and load them + the infra pins
#   status    release state, pod table, Gateway address
#   hosts     refresh the fenced /etc/hosts block from the live Gateway IP (CHT-106)
#   down      helm uninstall (+ --cluster to also minikube delete)
#
# Flags (env-overridable): --domain, --realm, --cpus, --memory, --skip-build.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

RELEASE="${ATLAS_CLUSTER_RELEASE:-atlas}"
NS="${ATLAS_CLUSTER_NS:-atlas}"
DOMAIN="${ATLAS_CLUSTER_DOMAIN:-atlas.test}"
REALM="${ATLAS_CLUSTER_REALM:-master}" # smoke users are seeded on master (CHT-78)
CPUS="${ATLAS_CLUSTER_CPUS:-4}"
MEMORY="${ATLAS_CLUSTER_MEMORY:-8192}"
EG_VERSION="${ATLAS_CLUSTER_EG_VERSION:-1.9.3}"
HELM_TIMEOUT="${ATLAS_CLUSTER_HELM_TIMEOUT:-15m}"
GATEWAY_CLASS="${ATLAS_CLUSTER_GATEWAY_CLASS:-envoy-gateway}"
TMP="${ATLAS_CLUSTER_TMP:-$ROOT/tmp/cluster}"
SKIP_BUILD="${ATLAS_CLUSTER_SKIP_BUILD:-0}"
# The repo venv carries PyYAML (chart_tags); the bare python3 may not.
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3

log() { printf '\033[1;36m[cluster]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[cluster]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[cluster] %s\033[0m\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        up | images | status | hosts | down) ACTION="$1"; shift ;;
        --domain) DOMAIN="$2"; shift 2 ;;
        --realm) REALM="$2"; shift 2 ;;
        --cpus) CPUS="$2"; shift 2 ;;
        --memory) MEMORY="$2"; shift 2 ;;
        --skip-build) SKIP_BUILD=1; shift ;;
        --cluster) PURGE_CLUSTER=1; shift ;;
        *) die "unknown argument: $1" ;;
    esac
done
ACTION="${ACTION:-up}"
mkdir -p "$TMP"

KC_SVC_DNS="atlas-keycloak.${NS}.svc.cluster.local"
REWRITE="rewrite stop name keycloak.${DOMAIN} ${KC_SVC_DNS}"

# --- cluster lifecycle ------------------------------------------------------

ensure_minikube() {
    command -v minikube >/dev/null || die "minikube not on PATH (devcontainer feature; CHT-59)"
    if ! minikube status -f '{{.Host}}' 2>/dev/null | grep -q Running; then
        log "minikube start (cpus=$CPUS memory=${MEMORY}Mi)"
        minikube start --cpus="$CPUS" --memory="$MEMORY" >/dev/null
    fi
}

ensure_tunnel() {
    # The Gateway needs an external address (minikube tunnel). Background it
    # with a pidfile; re-running is a no-op while the pid lives.
    if [[ -f "$TMP/tunnel.pid" ]] && kill -0 "$(cat "$TMP/tunnel.pid")" 2>/dev/null; then
        return
    fi
    log "minikube tunnel (background, pidfile $TMP/tunnel.pid)"
    nohup minikube tunnel >/dev/null 2>&1 &
    echo $! >"$TMP/tunnel.pid"
}

ensure_prereqs() {
    kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create ns "$NS"

    if ! kubectl get ns cert-manager >/dev/null 2>&1; then
        log "cert-manager apply"
        kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml >/dev/null
    fi
    kubectl wait --for=condition=Available deploy/cert-manager-webhook \
        -n cert-manager --timeout=180s >/dev/null

    if ! helm status eg -n envoy-gateway-system >/dev/null 2>&1; then
        log "Envoy Gateway $EG_VERSION"
        helm install eg "oci://docker.io/envoyproxy/gateway-helm" --version "$EG_VERSION" \
            -n envoy-gateway-system --create-namespace >/dev/null
    fi
    # EG ships NO GatewayClass (k8s-edge gotcha): create the one the overlay names.
    kubectl get gatewayclass "$GATEWAY_CLASS" >/dev/null 2>&1 ||
        kubectl apply -f - >/dev/null <<EOF
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
    name: ${GATEWAY_CLASS}
spec:
    controllerName: gateway.envoyproxy.io/gatewayclass-controller
EOF

    ensure_split_horizon
}

ensure_split_horizon() {
    # DD-265: in-cluster producers dial the issuer's public name; CoreDNS must
    # rewrite it to the Keycloak Service. Patch once, roll coredns, done.
    local corefile
    corefile="$(kubectl -n kube-system get configmap coredns -o jsonpath='{.data.Corefile}')"
    if grep -qF "keycloak.${DOMAIN}" <<<"$corefile"; then
        return
    fi
    log "CoreDNS split-horizon rewrite for keycloak.${DOMAIN}"
    local patched
    patched="$(python3 - "$corefile" "$REWRITE" <<'PY'
import sys

corefile, rewrite = sys.argv[1], sys.argv[2]
# Insert the rewrite line after the kubernetes block's closing brace, sharing
# its indentation. Line-based: Corefiles differ between flavours (k3d's flat
# `kubernetes cluster.local {`, minikube's `cluster.local in-addr.arpa
# ip6.arpa {` with 3-space indent), and the block may carry nested stanzas.
lines = corefile.splitlines()
out, i, done = [], 0, False
while i < len(lines):
    line = lines[i]
    out.append(line)
    stripped = line.strip()
    if not done and stripped.startswith("kubernetes") and stripped.endswith("{"):
        indent = line[: len(line) - len(line.lstrip())]
        depth = 1
        i += 1
        while i < len(lines) and depth:
            out.append(lines[i])
            depth += lines[i].count("{") - lines[i].count("}")
            i += 1
        out.append(indent + rewrite)
        done = True
        continue
    i += 1
if not done:
    sys.exit("could not find the kubernetes block in the Corefile")
print("\n".join(out))
PY
)"
    kubectl -n kube-system patch configmap coredns --type merge \
        -p "$(python3 -c 'import json,sys; print(json.dumps({"data":{"Corefile":sys.stdin.read()}}))' <<<"$patched")" >/dev/null
    kubectl -n kube-system rollout restart deployment coredns >/dev/null
    kubectl -n kube-system rollout status deployment coredns --timeout=120s >/dev/null
}

# --- images -------------------------------------------------------------------

image_refs() {
    # Authoritative list: what the stock minikube-overlay render actually names.
    helm dep update helm >/dev/null 2>&1 || die "helm dep update failed"
    helm template "$RELEASE" helm -n "$NS" -f helm/environments/minikube.yaml |
        grep -oE 'image: "[^"]+"' | cut -d'"' -f2 | sort -u
}

chart_tags() {
    # Digest-pinned infra images carry no tag in the render; the charts declare
    # the tag beside the digest (CHT-93). Map digest ref -> tag, one per line.
    "$PY" - <<'PY'
import glob
import yaml

def walk(node):
    if isinstance(node, dict):
        repo, tag, dig = node.get("repository"), node.get("tag"), node.get("digest")
        if isinstance(repo, str) and isinstance(dig, str) and str(dig).startswith("sha256:"):
            print(f"{repo}@{dig}\t{tag}")
        for value in node.values():
            walk(value)
    elif isinstance(node, list):
        for value in node:
            walk(value)

for f in (glob.glob("helm/values.yaml") + glob.glob("apps/*/helm/values.yaml") +
          glob.glob("dev/*/helm/values.yaml")):
    try:
        walk(yaml.safe_load(open(f)))
    except (OSError, yaml.YAMLError):
        pass
PY
}

load_images() {
    # CHT-52. minikube cannot load a digest-pinned reference: docker refuses to
    # save one ("manifest for image ... does not exist") and `minikube image
    # load <repo>@sha256:...` is a silent no-op (v1.39). So digest pins travel
    # under the tag their chart declares beside the digest and the exact digest
    # name is re-applied inside the node's containerd. Honesty chain: the local
    # image *is* the verified digest, and `docker tag <digest> <tag>` (never
    # the reverse) is what names it — a :latest drift can't sneak in.
    local tags built=0 ref repo tag
    refs="$(image_refs)"
    tags="$(chart_tags)"
    look() { printf '%s\n' "$tags" | awk -F'\t' -v r="$1" '$1 == r { print $2; exit }'; }
    for ref in $refs; do
        case "$ref" in
            ghcr.io/*)
                if [[ "$SKIP_BUILD" == 1 ]]; then
                    docker image inspect "$ref" >/dev/null 2>&1 ||
                        die "$ref not present and --skip-build was passed"
                else
                    built=1
                fi
                ;;
            *@sha256:*)
                tag="$(look "$ref")"
                [[ -n "$tag" ]] || die "no chart values tag declared for $ref"
                repo="${ref%@*}"
                if ! docker image inspect "$ref" >/dev/null 2>&1; then
                    log "pull ${repo##*/}@${ref##*@}"
                    docker pull "$ref" >/dev/null
                fi
                docker tag "$ref" "$repo:$tag"
                ;;
            *)
                if ! docker image inspect "$ref" >/dev/null 2>&1; then
                    log "pull $ref"
                    docker pull "$ref" >/dev/null
                fi
                ;;
        esac
    done
    if [[ "$built" == 1 ]]; then
        log "building the Aurelius images at :latest"
        npx nx run-many -t docker-build \
            -p aurelius-atlas-server,aurelius-atlas-webapp,aurelius-atlas-data2model,aurelius-atlas-lineage-model,aurelius-atlas-validate-entity,aurelius-atlas-elasticsearch-agent \
            -- --version latest >/dev/null
    fi
    for ref in $refs; do
        if [[ "$ref" == *@sha256:* ]]; then
            repo="${ref%@*}"
            tag="$(look "$ref")"
            log "minikube load ${repo##*/}:$tag (pinned ${ref##*@})"
            minikube image load "$repo:$tag" >/dev/null
            # ctr re-tag is idempotent (re-tagging an existing name exits 0);
            # a different image already under this digest fails loudly here.
            minikube ssh -- "sudo ctr -n k8s.io images tag '$repo:$tag' '$ref'" >/dev/null
        else
            log "minikube image load ${ref##*/}"
            minikube image load "$ref" >/dev/null
        fi
    done
}

# --- umbrella install ---------------------------------------------------------

helm_install() {
    # DD-252 recovery, scripted: a release parked in a pending-* state never
    # resolves itself; uninstall (waited) and reinstall, never upgrade-into.
    local state
    state="$(helm status "$RELEASE" -n "$NS" -o json 2>/dev/null |
        python3 -c 'import json,sys;print(json.load(sys.stdin).get("info",{}).get("status",""))' 2>/dev/null || true)"
    if [[ "$state" == pending-* ]]; then
        log "release stuck at $state — DD-252 uninstall-and-reinstall"
        helm uninstall "$RELEASE" -n "$NS" --wait >/dev/null 2>&1 || true
        state=""
    fi
    local sets=(--set "global.realm=${REALM}")
    if [[ -n "$state" ]]; then
        log "helm upgrade $RELEASE ($state)"
        helm upgrade "$RELEASE" helm -n "$NS" -f helm/environments/minikube.yaml \
            "${sets[@]}" --timeout "$HELM_TIMEOUT" >/dev/null
    else
        log "helm install $RELEASE (realm=$REALM domain=$DOMAIN)"
        helm install "$RELEASE" helm -n "$NS" -f helm/environments/minikube.yaml \
            "${sets[@]}" --timeout "$HELM_TIMEOUT" >/dev/null
    fi
}

wait_ready() {
    log "waiting for every pod in $NS to be Ready (Jobs exempt)"
    local deadline=$((SECONDS + 900))
    while ((SECONDS < deadline)); do
        local bad
        bad="$(kubectl -n "$NS" get pods -o json |
            python3 -c '
import json, sys
pods = json.load(sys.stdin)["items"]
bad = []
for p in pods:
    name = p["metadata"]["name"]
    phase = p["status"]["phase"]
    if phase in ("Succeeded",):
        continue
    kinds = {o["kind"] for o in p["metadata"].get("ownerReferences", [])}
    ready = any(c["type"] == "Ready" and c["status"] == "True"
                for c in p["status"].get("conditions", []))
    if kinds == {"Job"} and phase == "Running":
        continue
    if not ready:
        bad.append(name)
print(" ".join(bad))
')"
        if [[ -z "$bad" ]] && [[ "$(helm status "$RELEASE" -n "$NS" -o json |
            python3 -c 'import json,sys;print(json.load(sys.stdin)["info"]["status"])')" == "deployed" ]]; then
            log "cluster green"
            return 0
        fi
        sleep 10
    done
    kubectl -n "$NS" get pods -o wide >&2 || true
    die "cluster did not go green within 900s"
}

gateway_address() {
    # The Gateway's external address (minikube tunnel assigns it). Empty when
    # the tunnel is down — the caller decides whether that is fatal.
    kubectl -n "$NS" get gateway "$RELEASE" \
        -o jsonpath='{.status.addresses[0].value}' 2>/dev/null || true
}

ensure_hosts() {
    # CHT-106: the browser leg's DNS. Playwright and page.request resolve
    # outside the Python process, so the resolver shim cannot carry them —
    # a fenced /etc/hosts block maps the edge hostnames to the live Gateway.
    # The block is ours alone: re-runs replace it, nothing outside moves.
    local gateway_ip
    gateway_ip="$(gateway_address)"
    [[ -n "$gateway_ip" ]] ||
        die "the Gateway carries no address — is minikube tunnel running? (install.sh up starts it)"
    HOSTS_FILE="${ATLAS_CLUSTER_HOSTS_FILE:-/etc/hosts}" \
        ATLAS_CLUSTER_GATEWAY_IP="$gateway_ip" \
        ATLAS_CLUSTER_HOSTNAMES="${RELEASE}.${DOMAIN} keycloak.${DOMAIN}" \
        ATLAS_CLUSTER_USER="$(id -un)" \
        PYTHONPATH="$ROOT/libs/python/aurelius-atlas-cluster-lane${PYTHONPATH:+:$PYTHONPATH}" \
        "$PY" - <<'PY'
import os
import sys

from aurelius_atlas_cluster_lane.hosts import hosts_block

path = os.environ["HOSTS_FILE"]
gateway_ip = os.environ["ATLAS_CLUSTER_GATEWAY_IP"]
names = os.environ["ATLAS_CLUSTER_HOSTNAMES"].split()
# Never shadow the machine's own name: on the minikube node that deletes the
# node's own hosts line and breaks DNS for every fall-through lookup.
entries = {n: gateway_ip for n in names}
try:
    with open(path) as handle:
        current = handle.read()
except OSError as error:  # pragma: no cover - operator-run path
    sys.exit(f"cannot read {path}: {error}")
try:
    updated = hosts_block(current, entries)
except ValueError as error:
    sys.exit(f"refusing to write the hosts block: {error}")
if updated == current:
    print(f"{path}: the block is current ({gateway_ip})", file=sys.stderr)
else:
    try:
        with open(path, "w") as handle:
            handle.write(updated)
    except PermissionError:
        user = os.environ.get("ATLAS_CLUSTER_USER", "?")
        sys.exit(f"{path} is not writable by {user}: re-run with sudo (or set ATLAS_CLUSTER_HOSTS_FILE)")
    print(f"{path}: {', '.join(names)} -> {gateway_ip}", file=sys.stderr)
PY
}

# --- subcommands ---------------------------------------------------------------

case "$ACTION" in
    up)
        ensure_minikube
        ensure_tunnel
        ensure_prereqs
        load_images
        helm_install
        wait_ready
        # CHT-106: the block is the browser leg's convenience — a read-only
        # /etc/hosts (devcontainer users are often not root) must not fail an
        # otherwise-green install; the suites ride the resolver shim.
        ensure_hosts || warn "the hosts block was not written — the Python suites do not need it; for Playwright browsers run: sudo bash tools/cluster/install.sh hosts"
        kubectl -n "$NS" get gateway \
            -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.status.addresses[0].value}{"\n"}{end}' 2>/dev/null || true
        ;;
    images)
        ensure_minikube
        load_images
        ;;
    hosts)
        ensure_hosts
        ;;
    status)
        helm status "$RELEASE" -n "$NS" 2>/dev/null | head -6 || log "no release $RELEASE in $NS"
        kubectl -n "$NS" get pods
        kubectl -n "$NS" get gateway -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.status.addresses[0].value}{"\n"}{end}' 2>/dev/null
        ;;
    down)
        helm uninstall "$RELEASE" -n "$NS" --wait >/dev/null 2>&1 || true
        if [[ -f "$TMP/tunnel.pid" ]]; then
            kill "$(cat "$TMP/tunnel.pid")" 2>/dev/null || true
            rm -f "$TMP/tunnel.pid"
        fi
        if [[ "${PURGE_CLUSTER:-0}" == 1 ]]; then
            log "minikube delete"
            minikube delete >/dev/null
        fi
        log "down"
        ;;
esac
