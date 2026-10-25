#!/usr/bin/env bash
# Provision the AKS side of self-hosted CI (docs/architecture/self-hosted-ci.md,
# infra/arc/README.md).
#
# Usage: ./install.sh <controller|nodepool|scale-set|status>
# Env:   AZ_RESOURCE_GROUP, AZ_CLUSTER_NAME, AZ_NODEPOOL (default: cipool)
set -euo pipefail

RG="${AZ_RESOURCE_GROUP:?set AZ_RESOURCE_GROUP}"
CLUSTER="${AZ_CLUSTER_NAME:?set AZ_CLUSTER_NAME}"
POOL="${AZ_NODEPOOL:-cipool}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-status}" in
    controller)
        # Cluster-scoped; one per cluster.
        helm install arc \
            oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller \
            --namespace arc-systems --create-namespace
        ;;
    nodepool)
        # Scale-to-zero (min 0) requires the cluster autoscaler enabled.
        az aks nodepool add \
            --resource-group "$RG" --cluster-name "$CLUSTER" --name "$POOL" \
            --node-vm-size Standard_D8s_v5 \
            --enable-auto-scaling --min-count 0 --max-count 3 \
            --kubelet-disk-type Ephemeral \
            --node-taints "ci=true:NoSchedule" \
            --priority Spot --eviction-policy Delete
        ;;
    scale-set)
        # Needs the atlas-arc-auth secret + the PVC (see README); labels the
        # runners with atlas-ci, which runs-on selects via CI_RUNS_ON.
        helm upgrade --install atlas-ci \
            oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set \
            --namespace arc-runners -f "$HERE/arc-values.yaml"
        ;;
    status)
        kubectl -n arc-runners get autoscalingrunnerset,secrets,pvc,pods -o wide
        ;;
    *)
        echo "usage: $0 <controller|nodepool|scale-set|status>" >&2
        exit 2
        ;;
esac
