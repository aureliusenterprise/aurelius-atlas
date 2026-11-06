# Deployment

How a released version reaches an environment, and how it is rolled back. The system operates two
environments, development and test, and hands every other environment a complete release ([ADR
024](../../adr/024-a-validated-release-is-promoted-by-a-declared-path.md)): images and charts, signed and
versioned together ([Release Management](release-management.md)). How the charts fit together, and the install
steps, are in the [deployment reference](../../deployment/index.md) and its
[runbook](../../deployment/runbook.md).

## One image per service, one chart per part

Each service ships as its own image: the server, the webapp, the auxiliary APIs, and the store's coredump
agent. Each part has a chart, and the umbrella chart installs them as one release ([ADR
057](../../adr/057-the-system-ships-as-helm-charts-that-a-deployment-installs.md)). An environment differs
from another by its values, never by a changed chart.

In development the same parts run as compose stacks, one per project (`dev/*/docker-compose.yaml`), started by
the targets that need them ([ADR 005](../../adr/005-dev-infra-starts-with-the-app.md)). The compose files and
the charts are siblings: the chart suites hold the settings they share equal, such as the alert rules, the
collector's configuration and the lifetimes.

## Promoting a release

A release is promoted, not rebuilt: an environment receives the release's own images and its signed chart. The
declared path for a deployment that keeps real data:

1. Take a snapshot of the store before the upgrade:
   `kubectl -n atlas exec deploy/atlas-server -- python -m aurelius_atlas_server.snapshots take`.
2. Upgrade the release to the new chart version with the environment's values:
   `helm upgrade atlas <chart> --version <version> -f <values>`.
3. Watch the rollout and the alerts for an hour ([Alerting](../observability/alerting.md)).

## Rolling back

A rollback is the same move with the previous version: `helm rollback atlas`, or `helm upgrade` to it. The
previous server reads the store as the new one left it. When the new version changed the store's layout ([ADR
023](../../adr/023-storage-schema-changes-by-recorded-migration.md)), the previous one may not read it, and
the rollback is a restore of the snapshot taken in step 1 ([Backup &
Restore](../resilience/backup-and-restore.md#restoring)). That restore loses the writes made since the
snapshot, which is why the snapshot is taken right before the upgrade.
