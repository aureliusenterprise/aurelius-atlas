#!/usr/bin/env bash
# Provision the GKE side of self-hosted CI (docs/architecture/self-hosted-ci.md,
# infra/arc/README.md).
#
# Usage: ./install.sh <cluster|controller|nodepool|scale-set-shapea|cache-server|status>
# Env:   GCP_PROJECT, GKE_CLUSTER, GKE_LOCATION (region), GKE_NODEPOOL (default: cipool),
#        CI_SHAPEA_IMAGE_TAG (scale-set-shapea image tag, default: main)
set -euo pipefail

PROJECT="${GCP_PROJECT:?set GCP_PROJECT}"
CLUSTER="${GKE_CLUSTER:?set GKE_CLUSTER}"
LOCATION="${GKE_LOCATION:?set GKE_LOCATION (region)}"
POOL="${GKE_NODEPOOL:-cipool}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-status}" in
    cluster)
        # Standard-mode (Autopilot forbids privileged pods - the dind sidecar
        # needs Standard). Zonal; system pool = 1-2 small nodes for the ARC
        # controller; CI pods land on `nodepool` (spot, tainted) only.
        gcloud container clusters create "$CLUSTER" \
            --project "$PROJECT" --location "$LOCATION" \
            --release-channel regular \
            --machine-type e2-small --num-nodes 1 \
            --enable-autoscaling --min-nodes 1 --max-nodes 2 \
            --disk-type pd-balanced --disk-size 50 \
            --workload-metadata=DISABLED
        ;;
    controller)
        # Cluster-scoped; one per cluster.
        helm install arc \
            oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
            --namespace arc-systems --create-namespace
        ;;
    nodepool)
        # Scale-to-zero: GKE regional pools start at 1 node per zone; spot +
        # min 0 keeps the idle cost to the controller's needs only.
        gcloud container node-pools create "$POOL" \
            --project "$PROJECT" --cluster "$CLUSTER" --location "$LOCATION" \
            --machine-type n2-standard-8 --spot \
            --enable-autoscaling --min-nodes 0 --max-nodes 3 \
            --disk-type pd-ssd --disk-size 200 \
            --node-taints "ci=true:NoSchedule" \
            --workload-metadata=DISABLED
        ;;
    scale-set-shapea)
        # The production scale set (arc-shapea-values.yaml): the job
        # container IS the dev container image - ci.yaml runs on it
        # directly. Needs atlas-arc-auth + atlas-ghcr-pull (the GHCR pull
        # secret, see README). CI_SHAPEA_IMAGE_TAG selects the image tag
        # (default main; the build workflow publishes sha-<full-sha> for
        # branch builds).
        # NOTE: helm upgrade EVICTS in-flight runner pods (jobs die, queued
        # jobs requeue) - deploy between runs.
        TAG="${CI_SHAPEA_IMAGE_TAG:-main}"
        helm upgrade --install atlas-ci-shapea \
            oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
            --namespace arc-runners -f "$HERE/arc-shapea-values.yaml" \
            --set "template.spec.containers[0].image=ghcr.io/aureliusenterprise/atlas-ci-runner:${TAG}"
        ;;
    cache-server)
        # The actions/cache backend for self-hosted runners
        # (cache-server-values.yaml, README "Cache server"). Safe to
        # deploy any time (its own release, evicts nothing). One-time.
        helm upgrade --install gha-cache-server \
            oci://ghcr.io/falcondev-oss/charts/github-actions-cache-server \
            --namespace arc-runners -f "$HERE/cache-server-values.yaml"
        ;;
    status)
        kubectl -n arc-runners get autoscalingrunnerset,secrets,pvc,pods,deploy,svc -o wide
        ;;
    *)
        echo "usage: $0 <cluster|controller|nodepool|scale-set|status>" >&2
        exit 2
        ;;
esac
