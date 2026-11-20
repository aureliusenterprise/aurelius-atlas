# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the Design Log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-728. On a cluster, passwords reach the Job in a short-lived Secret and leave through the terminal

- **Status:** Proposed
- **Increment:** 15.8
- **Date:** 2026-11-20

**Decision.** For `add` and `user add` on a cluster, `helm/bin/tenant.sh` generates the temporary passwords on
the machine it runs on, puts them in a Secret it makes for the one Job, mounts it read-only, and passes
`--passwords-from`. The command sets them as temporary and prints none (TKS-06). The script prints each made
user's password on its own terminal after the Job, then deletes the Job and the Secret.

**Reason.** In the standalone stack the summary prints each password to whoever ran the command (DD-701). On a
cluster a pod's output is kept: by the kubelet as the Job's log, and by the chart's collector in Loki, where it
outlives the first sign-in. Generating the passwords outside the cluster and handing them in through a Secret
keeps them out of every log, and the Secret exists only while the Job runs.

**Alternatives.**

- The command prints the passwords, and the script deletes the Job at once: Loki has already collected them.
- The command writes them into a Secret through the Kubernetes API: the Job's service account needs rights to
  write Secrets, and someone has to read and delete it afterwards.
- No initial password, a realm administrator sets one in the console: every new person costs a manual step.

**Consequences.** `add` and `user add` gain `--passwords-from`, which the standalone script doesn't use. The
person running the script needs the rights to create and delete Secrets in the namespace (TKS-14). A password
the script generated for a user the command found, not made, is discarded unprinted.

### DD-729. The server's image ships the repository's samples

- **Status:** Proposed
- **Increment:** 15.8
- **Date:** 2026-11-20

**Decision.** The server's image copies the export ZIPs of `data/atlas-sample/` into `/application/samples`
and sets `AURELIUS_ATLAS_SERVER_SAMPLE_DIR` to it.

**Reason.** A pod has no sample folder of its own, and `sample_data.zip` is too large for a ConfigMap once
encoded. The three samples are about 1 MB together, small beside the image. In the image, `samples` and
`add --sample` behave the same in every pod of it, the Job the script runs included.

**Alternatives.**

- An image of samples, copied into an empty volume by an init container: one more image to build, sign and
  publish for 1 MB.
- A volume the operator fills: a sample becomes a deployment task.
- The samples left out on a cluster, imported through `admin/import` afterwards: `add --sample` works on one
  deployment shape only.

**Consequences.** A new sample in `data/atlas-sample/` reaches a cluster with the next image. The standalone
stack keeps mounting its own folder over the setting, so its samples need no rebuild.

### DD-730. The script runs the command as a Job made from the operators CronJob

- **Status:** Proposed
- **Increment:** 15.8
- **Date:** 2026-11-20

**Decision.** `helm/bin/tenant.sh` finds the release's operators CronJob by its labels and makes a Job of it
with `kubectl create job --from=cronjob/…`, its container's command replaced by the command and the script's
arguments, and for `add` and `user add` the passwords' Secret mounted. It waits for the Job, prints its output,
and deletes the Job and the Secret on every way out, interruption included.

**Reason.** The operators CronJob already carries all the command needs: the server's image, its settings, the
provisioning client's secret, and the labels the store's network policy admits. A Job made from it inherits
them, so the script states none of the chart's wiring itself, as `docker/bin/tenant.sh` runs in the stack's
existing one shot (DD-702).

**Alternatives.**

- `kubectl exec` into a server pod: the server's container has no provisioning client's secret.
- A Job template of its own in the chart, rendered by the script: the same environment stated twice.
- `kubectl run` with the environment rebuilt from the Secrets: the script would repeat the chart's joins.

**Consequences.** The script works only while tenancy is on, since the CronJob exists only then (TKS-09). A
change to the CronJob's environment reaches the script with no change to it.

### DD-731. The chart's realm carries the standalone realm's fixes

- **Status:** Proposed
- **Increment:** 15.8
- **Date:** 2026-11-20
- **Supersedes:** DD-661's trim of the `roles` scope to its one client-role mapper; the rest of DD-661 stands

**Decision.** The chart's realm defines every client scope it names, carries the account clients, their roles
and the default role, and its `roles` scope gains the audience-resolve and realm-role mappers beside DD-661's
mapper: the fixes DD-700's increment gave the standalone realm.

**Reason.** The chart's realm has the standalone realm's gaps. A file that lists client scopes gets none of
Keycloak's built-in ones, so with tenancy on the webapp's sign-in asks for the undefined `organization` and
fails with `invalid_scope`. Keycloak makes its account clients before it imports a file's scopes, so the account
page answers 403. The trimmed `roles` scope gives no token the `account` audience. Tenants on a cluster need all
three, and the two realms stay alike.

**Alternatives.**

- Leave the chart's realm, and document tenancy on a cluster as unsupported: ADR 063's deployment shape fails.
- Fix the realm through a post-install Job and the admin API: a second way to define the realm, beside the
  file.

**Consequences.** A cluster whose Keycloak has imported the realm already keeps the old one, since the import
runs into an empty database only. The guide names the admin-API steps that bring such a realm in step, or a
fresh Keycloak database.
