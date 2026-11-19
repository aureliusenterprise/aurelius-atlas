# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the Design Log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-701. A person the command makes gets a temporary password, printed once

- **Status:** Proposed
- **Increment:** 15.7
- **Date:** 2026-11-19

**Decision.** A user `add` or `user add` makes gets a password the command generates to meet the realm's
password policy, stored in Keycloak as temporary, with the required action `UPDATE_PASSWORD`. The command
prints it once, in its summary, to whoever ran it, and writes it nowhere else. A user the realm already has
keeps its password, and none is printed.

**Reason.** A tenant's people should be added without editing files, and their passwords known to no one but
them. A temporary password hands the account over: the person sets their own at the first sign-in, and the one
printed stops working then. The runbook already makes administrators this way. Generating it in the command
keeps the realm's policy, 12 characters with an upper- and a lower-case letter, a digit and a special
character, from refusing it.

**Alternatives.**

- Passwords from variables, as the seeded demo and meyn have (DD-700): every tenant edits `infra/keycloak/.env`
  and the compose file, which is what this increment removes.
- The command writes the passwords to a file: a secret on disk that someone has to delete.
- No password, an invitation by email instead: the stack sends no email.

**Consequences.** Whoever runs the command passes each printed password on, once; a lost one is reset in the
console. The seeded demo and meyn keep their permanent passwords from the env file (DD-700), since a demo
stack is signed in to again and again with the same ones.

### DD-702. The standalone stack's tenant command runs in its one shot `tenants`

- **Status:** Proposed
- **Increment:** 15.7
- **Date:** 2026-11-19

**Decision.** `docker/tenant` is a shell script that runs `docker compose run --rm --no-deps` of the stack's one
shot `tenants`, with the stack's three env files and the profile `tenancy`, its entrypoint replaced by the
command and the script's arguments passed through. It answers the command's output and exit code.

**Reason.** The one shot `tenants` is the stack's place where the server's image runs with tenancy on, the
provisioning client's secret and the sample folder mounted. Running the command there gives it everything
`add --sample` needs, with no second service definition to keep alike. A script hides the compose line, its
env files and its profile.

**Alternatives.**

- A service of its own for the command: the same settings and mounts stated twice.
- `docker compose exec` into the running server: its container has no sample folder and no provisioning
  client's secret.
- An Nx target: Nx is a development tool, and the stack runs without it.

**Consequences.** The script needs the stack's Keycloak and store running, as the command does. A Kubernetes
deployment needs its own way to run the same command, later.
