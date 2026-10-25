#!/bin/bash
set -euo pipefail

# kubelogin - the exec credential plugin AKS puts in every kubeconfig for
# Entra ID auth (docs/architecture/self-hosted-ci.md). Plain static binary;
# no official devcontainer feature exists (azure-cli/kubectl/helm use the
# official ones).

VERSION="${VERSION:-0.2.22}"

case "$(uname -m)" in
    x86_64) ARCH=amd64 ;;
    aarch64 | arm64) ARCH=arm64 ;;
    *)
        echo "kubelogin: unsupported architecture $(uname -m)" >&2
        exit 1
        ;;
esac

if [ "$VERSION" = "latest" ]; then
    VERSION="$(curl -fsSL https://api.github.com/repos/Azure/kubelogin/releases/latest |
        grep -oE '"tag_name": *"[^"]+"' | head -1 | cut -d'"' -f4 | tr -d v)"
fi

# Releases ship zips with the binary under bin/linux_<arch>/.
curl -fsSL "https://github.com/Azure/kubelogin/releases/download/v${VERSION}/kubelogin-linux-${ARCH}.zip" -o /tmp/kubelogin.zip
unzip -o -q /tmp/kubelogin.zip -d /tmp/kubelogin-pkg
install -m 0755 "/tmp/kubelogin-pkg/bin/linux_${ARCH}/kubelogin" /usr/local/bin/kubelogin
rm -rf /tmp/kubelogin.zip /tmp/kubelogin-pkg
