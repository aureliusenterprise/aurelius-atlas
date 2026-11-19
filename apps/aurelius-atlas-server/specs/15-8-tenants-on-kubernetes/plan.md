# 15.8 Plan

The steps, in order, each with the rules it delivers, its tests and what it waits for. The spec is
[`spec.md`](./spec.md). The three parts are three pull requests; 15.8b and 15.8c can be reviewed while 15.8a's
cluster check waits.

## 15.8a The chart's realm

1. **The client scopes** (TKS-01): copy into `infra/keycloak/helm/files/aurelius-atlas.json` the definitions
   of every scope its clients and defaults name, from `infra/keycloak/import/master.json`, without their ids.
2. **The account set** (TKS-02): the `account` and `account-console` clients, the `account` roles, the
   default role and its composites, as `docker/keycloak/aurelius-atlas.json` carries them since DD-700's
   increment, with the realm's paths.
3. **The `roles` scope** (TKS-03): add the audience-resolve and realm-role mappers; keep DD-661's mapper and
   its claim, which Grafana's role mapping reads.
4. **Tests**: extend `tests/test__charts_keycloak.py` with the guards
   `tests/test__standalone_demo_realm.py` has for the stack's realm (every named scope defined, the account
   set, the `roles` mappers), and keep the drift guard between the two realms.
5. **Waits for a cluster** (TKS-04): a fresh install on minikube with tenancy on, a tenant provisioned by the
   chart's hook, a member made in the console, their sign-in and account page.

## 15.8b The command and the image

1. **`--passwords-from`** (TKS-05, TKS-06): in `provisioning.py`, read the JSON file before anything is done,
   refuse a user to be made that it doesn't name, and pass the password to `ensure_person` as temporary; the
   summary prints no password when the option is given. `ensure_person` takes a temporary given password.
2. **Tests**: `test__aurelius_atlas_server_tenant_people.py`: a given password set as temporary with
   `UPDATE_PASSWORD`, a missing name refused before the tenant is provisioned, no password in any line written.
3. **The samples in the image** (TKS-07): the server's `Dockerfile` copies `data/atlas-sample/*.zip` into
   `/application/samples` and sets `AURELIUS_ATLAS_SERVER_SAMPLE_DIR`; the build's Nx inputs name the folder,
   so a new sample rebuilds the image. A test reads the `Dockerfile`; by hand, `docker run` of the image with
   the command `samples` lists the three.
4. **No wait**: buildable and testable locally.

## 15.8c The script and the guide

1. **`helm/bin/tenant.sh`** (TKS-08 to TKS-13), beside the chart:
    - parse `-n`, `-r` (default `atlas`) and `--context`; print the usage and exit 2 without arguments;
    - find the CronJob with `kubectl get cronjob -l app.kubernetes.io/name=atlas-server,app.kubernetes.io/instance=<release>`
      and the name ending `-operators`; refuse without one;
    - for `add` and `user add`, work out the users the command may make (`<tenant>_atlas`, with `--users all`
      the steward and the scientist; or the named user), generate their passwords with `openssl`, and make a
      Secret of them, named after the Job and labelled for cleanup;
    - make the Job from the CronJob with `kubectl create job --from=… --dry-run=client -o json`, replace the
      container's command, add the Secret's volume and mount for `add` and `user add`, and apply it;
    - wait for the Job to complete or fail, print its logs, read the summary's `made` lines, print those users'
      passwords, and exit with the command's code;
    - delete the Job and the Secret in a `trap` on exit, interruption included.
2. **Tests**: `tests/test__helm_tenant_script.py`, the script run against a stand-in `kubectl` on the `PATH`
   that records its calls and answers as the cluster would (TKS-08 to TKS-13).
3. **The guide**: `docs/user-guide/kubernetes-tenants.md`, the counterpart of `standalone-tenants.md`: the
   command's options, the rights the script needs (TKS-14), the passwords on the terminal alone, and bringing
   an older Keycloak's realm in step (DD-731). `docs/user-guide/deployment.md`'s "Turn on tenancy" links it, and
   `mkdocs.yaml` lists it.
4. **Waits for a cluster**: the spec's acceptance by hand, after 15.8a and 15.8b are deployed.

## Dependencies

- 15.8c's script runs the command of 15.8b: its cluster check needs an image with `--passwords-from`.
- Every cluster check needs a running cluster with the release installed and tenancy on, the step the
  colleague's work unblocks. Until then each part is done to its local tests.
