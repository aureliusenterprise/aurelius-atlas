# google-cloud-cli (vendored)

Vendored copy of `ghcr.io/dhoeric/features/google-cloud-cli` (main, fetched
2026-10-25) with three fixes:

1. `apt-key` was removed from Ubuntu 24.10+; the published feature dies with
   `apt-key: command not found`. This copy uses a `signed-by` keyring +
   deb822 source instead.
2. The apt repo renamed the plugin package
   `google-cloud-sdk-gke-gcloud-auth-plugin` → `google-cloud-cli-gke-gcloud-auth-plugin`;
   the name upstream requests has no installation candidate, so its plugin
   install also fails even when triggered. This copy prefers the current name
   and falls back to the old one.
3. The devcontainer CLI exports options as the uppercased option id with no
   underscores (`INSTALLGKEGCLOUDAUTHPLUGIN` - observed in the build log);
   upstream reads `INSTALL_GKEGCLOUDAUTH_PLUGIN`, never exported, so the
   published feature silently skips the plugin install. This copy accepts all
   spellings. (Caught by our `smoke.sh` gate - the image build failed with
   "gke-gcloud-auth-plugin is not on PATH".)

Verified by running `install.sh` in `mcr.microsoft.com/devcontainers/base:resolute`
(gcloud 590.0.1 + `gke-gcloud-auth-plugin`, exit 0).

**Upstream switch-back**: when dhoeric/features ships an Ubuntu 24.10+ fix
(track dhoeric/features#issue - the feature is unmaintained since 2023),
delete `./features/google-cloud-cli` and use
`"ghcr.io/dhoeric/features/google-cloud-cli:1"` in devcontainer.json.
