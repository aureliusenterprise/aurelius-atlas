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

log() { printf '\033[1;36m[cluster]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[cluster] %s\033[0m\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        up | images | status | down) ACTION="$1"; shift ;;
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

load_images() {
    local refs built=0
    refs="$(image_refs)"
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
        log "minikube image load ${ref##*/}"
        minikube image load "$ref" >/dev/null
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
        bad="$(kubectl -n "$NS" get pods -no json |
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

# --- subcommands ---------------------------------------------------------------

case "$ACTION" in
    up)
        ensure_minikube
        ensure_tunnel
        ensure_prereqs
        load_images
        helm_install
        wait_ready
        kubectl -n "$NS" get gateway \
            -o jsonpath='{range .items[*]}{.metadata.name}{" -> "}{.status.addresses[0].value}{"\n"}{end}' 2>/dev/null || true
        ;;
    images)
        ensure_minikube
        load_images
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
