# google-cloud-cli (vendored)

Vendored copy of `ghcr.io/dhoeric/features/google-cloud-cli` (main, fetched
2026-10-25) with two fixes for our base image (`resolute` = Ubuntu 26.04):

1. `apt-key` was removed from Ubuntu 24.10+; the published feature dies with
   `apt-key: command not found`. This copy uses a `signed-by` keyring +
   deb822 source instead.
2. The apt repo renamed the plugin package
   `google-cloud-sdk-gke-gcloud-auth-plugin` → `google-cloud-cli-gke-gcloud-auth-plugin`;
   this copy prefers the current name and falls back to the old one.

Verified by running `install.sh` in `mcr.microsoft.com/devcontainers/base:resolute`
(gcloud 590.0.1 + `gke-gcloud-auth-plugin`, exit 0).

**Upstream switch-back**: when dhoeric/features ships an Ubuntu 24.10+ fix
(track dhoeric/features#issue - the feature is unmaintained since 2023),
delete `./features/google-cloud-cli` and use
`"ghcr.io/dhoeric/features/google-cloud-cli:1"` in devcontainer.json.
