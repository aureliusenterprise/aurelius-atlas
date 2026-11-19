# 15.8 Adding a tenant on Kubernetes

- **Status:** planned
- **Pull request:** three, one per part (15.8a, 15.8b, 15.8c)
- **Records:** ADR 063 (Proposed); DD-728 to DD-731 (here); relies on 15.7 (TAD-01 to TAD-13, DD-701,
  DD-702), 15.5b (TRM-05, DD-601), 17.1 (IRT-06, DD-700) and 10.15 (DD-661)

15.7 gave the standalone stack one command that adds a tenant with its people, `docker/bin/tenant.sh`. A
Kubernetes deployment has the same command in the server's image, but no way to run it: no `docker compose
run`, and a pod's output is collected into its log and Loki, where a printed temporary password would stay.
This increment adds `helm/bin/tenant.sh`, which runs the command on the cluster with the same arguments, keeps
every password out of the cluster's logs, and ships the samples with the server's image. It also gives the
chart's realm the fixes the standalone realm got, without which a sign-in to a tenant fails.

The chart's declarative `tenancy.tenants` and its provisioning hook stay as they are: they provision a tenant
with no people. The script is how a tenant's people, and tenants with a sample, are added.

## Scope

The increment is three parts, each a pull request of its own, in this order:

| Part  | Delivers                                                                                | Projects                                  |
| ----- | --------------------------------------------------------------------------------------- | ----------------------------------------- |
| 15.8a | The chart's realm: the client scopes it names, the account clients, the `roles` mappers | `infra/keycloak` (the chart's realm file) |
| 15.8b | The command's `--passwords-from`; the samples in the server's image                     | `aurelius-atlas-server`                   |
| 15.8c | `helm/bin/tenant.sh`, and the guide adding a tenant on Kubernetes                       | `helm`, `docs`                            |

Not delivered, with the increment that will:

| Not delivered                                                                                  | Lands with  |
| ---------------------------------------------------------------------------------------------- | ----------- |
| The declarative path: `tenancy.tenants` entries with a sample and users, passwords in a Secret | not planned |
| Samples beyond the repository's, from a volume or a registry                                   | not planned |

## Semantics

"The command" is `python -m aurelius_atlas_server.provisioning` (15.3, 15.7). "The chart's realm" is
`infra/keycloak/helm/files/aurelius-atlas.json`, imported into an empty Keycloak at its first boot. "The
operators CronJob" is the server chart's `<fullname>-operators` (TRM-05), which carries the server's image,
settings and the provisioning client's secret. "The script" is `helm/bin/tenant.sh`.

### 15.8a The chart's realm

| Id     | Rule                                                                                                                                                                                                                                                                                                                                      |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TKS-01 | Every client scope a client of the chart's realm names, by default or optionally, and every scope of the realm's own defaults, is defined in the file, as the dev realm defines it (DD-731)                                                                                                                                               |
| TKS-02 | The file names the `account` and `account-console` clients with their default scopes and their mappings to the `account` client's roles, those roles, and the default role `default-roles-aurelius-atlas` with `offline_access`, `uma_authorization`, `view-profile` and `manage-account`, so Keycloak makes none of them itself (DD-731) |
| TKS-03 | The realm's `roles` scope carries DD-661's client-role mapper, the audience-resolve mapper and the realm-role mapper (DD-731)                                                                                                                                                                                                             |
| TKS-04 | The chart's realm imports into an empty Keycloak without error, and with tenancy on a member of a tenant signs in to the webapp in it and opens their account page                                                                                                                                                                        |

### 15.8b The command and the image

| Id     | Rule                                                                                                                                                                                                                                                                                                                                       |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TKS-05 | `add` and `user add` take `--passwords-from <file>`: a JSON object of usernames and passwords. A user the command makes and the file names gets that password, temporary, with the required action to change it at the first sign-in (DD-701). A user the command would make that the file doesn't name is refused before anything is done |
| TKS-06 | With `--passwords-from`, the command writes no password: its summary says `made` for a user it made and `existed` for one it found (TAD-08), and nothing else names a password                                                                                                                                                             |
| TKS-07 | The server's image holds the samples of `data/atlas-sample/` in `/application/samples`, and names that folder in `AURELIUS_ATLAS_SERVER_SAMPLE_DIR`, so `samples` and `add --sample` work in any pod of it. The standalone one shot `tenants` keeps its own sample folder (TAD-12, DD-729)                                                 |

### 15.8c The script

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                              |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TKS-08 | `helm/bin/tenant.sh [-n <namespace>] [-r <release>] [--context <context>] <arguments>` takes the arguments of `docker/bin/tenant.sh` (TAD-12) and runs the command with them on the cluster. It needs `kubectl` and `openssl` alone. With no argument it prints its usage and exits 2                                                                             |
| TKS-09 | The script finds the operators CronJob of the release by its labels, the server chart's name and the release's instance, and the suffix `-operators`. Without one, as with tenancy off, it says so and exits non-zero, having made nothing                                                                                                                        |
| TKS-10 | The script runs the command once as a Job made from the operators CronJob, its command replaced, and waits for it to end. It prints the Job's output and exits with the command's exit code. It deletes the Job and every Secret it made, whether the command succeeded, failed or the script was interrupted (DD-730)                                            |
| TKS-11 | For `add` and `user add`, the script generates on the machine it runs on a password meeting the realm's policy for each user the command may make, puts them in a Secret mounted read-only into the Job, and passes `--passwords-from`. After the Job, it prints the password of each user the command's summary says it made, on its own terminal alone (DD-728) |
| TKS-12 | No password the script generates enters the Job's output, the cluster's logs or Loki; the Secret holding them lives only while the Job runs (DD-728)                                                                                                                                                                                                              |
| TKS-13 | Every other command, `samples`, `list`, `admin`, `trust`, `user remove` and `remove`, is passed through as it is, with no Secret                                                                                                                                                                                                                                  |
| TKS-14 | The script needs, in the namespace, the rights to read CronJobs, to create, read and delete Jobs and Secrets, and to read pods and their logs; the guide names them                                                                                                                                                                                               |

## Java origin

None: Apache Atlas has no tenants and no Kubernetes deployment.

## Deviations

None against Apache Atlas.

## Acceptance

- 15.8a: `tests/test__charts_keycloak.py` and `tests/test__realm_organizations.py` extended to the chart's
  realm, as `tests/test__standalone_demo_realm.py` pins the stack's (TKS-01 to TKS-03); by hand on a cluster
  (minikube, `helm/environments/minikube.yaml`), a fresh install with tenancy on, a tenant member's sign-in and
  account page (TKS-04).
- 15.8b: `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_tenant_people.py` (TKS-05, TKS-06); a
  test of the server image's Dockerfile and a `docker run` of the built image listing the samples (TKS-07).
- 15.8c: `tests/test__helm_tenant_script.py` runs the script against a stand-in `kubectl` on the `PATH` that
  records each call and answers as the cluster would: the CronJob found, the Job and the Secret made with the
  right shape, both deleted on success, failure and interruption, the passwords printed after the Job and in no
  call to `kubectl` but the Secret's (TKS-08 to TKS-13).
- By hand on the cluster: `helm/bin/tenant.sh -n atlas add acme --users all --sample small`, then a sign-in as
  `acme_atlas` with its printed temporary password; `kubectl -n atlas get jobs,secrets` lists nothing the script
  made; Loki holds no line with the password.
