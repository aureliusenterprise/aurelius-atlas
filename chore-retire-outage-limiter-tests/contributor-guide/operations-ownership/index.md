# Operations Ownership

Two records name an owner and a written path where the system had none: the handling of operational secrets ([ADR 028](<https://aureliusenterprise.github.io/chore-retire-outage-limiter-tests/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>)) and the response to a failure of the running system ([ADR 041](<https://aureliusenterprise.github.io/chore-retire-outage-limiter-tests/architecture/adr/041-a-failure-of-the-running-system-has-an-owner-and-a-rehearsed-path/index.md>)). The owner named by both is the same role, because this is one team.

## The owner

**The maintainers team** — the role whose two signatures carry every change ([ADR 044](<https://aureliusenterprise.github.io/chore-retire-outage-limiter-tests/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)) — answers for:

- rotation, loss, and break-glass for real secrets and age keys (ADR 028 R1);
- the response to a failure of the running system, from noticing to closing (ADR 041 R1).

The owner is a role, not a person: when a person leaves, the duties move with the pull request that removes their key from `.sops.yaml`. This page is the written path both records require (ADR 028 R2–R4, ADR 041 R2); the first rehearsals are scheduled at the bottom.

## Secret handling

Storage is decided by [ADR 008](<https://aureliusenterprise.github.io/chore-retire-outage-limiter-tests/architecture/adr/008-secrets-never-in-plaintext/index.md>): `.env.enc` per project, encrypted with SOPS to the recipient set in `.sops.yaml`; per-person age keys at `secrets/keys.txt`, never committed.

- **Adding a person — the rehearsed case, and the easy direction.** The person generates a key on first devcontainer start.
- A reviewed change adds it to `.sops.yaml`.
- The key tooling (`update-keys`, the `rotate-keys` workflow) re-encrypts every `.env.enc` for the new set.
- **Urgent rotation — suspected leak, forced expiry.** Any one maintainer acts without waiting: rotate the value at its origin, update the project's `.env`, run `nx encrypt <project>`, ship under the normal gate with expedited review, and note the old value's exposure window in the commit message.
- **Key loss — the declared answer (ADR 028 R3).** Data encrypted to a lost key alone is unrecoverable; there is no personal-key escrow, by design. The person regenerates a key and membership repairs through re-encryption signed by every remaining recipient. The consequence is owned by the team, written here, not discovered in an incident.
- **Break-glass — temporary access (ADR 028 R4).** Any maintainer may decrypt and share one value, for a stated reason, to a named recipient. The grant is logged in the project's issue log with the value name, reason, and expiry; the team reviews grants at the dependency-review cadence.

## Incident response

The path from first signal to all-clear (ADR 041 R2); the owner is the maintainers team.

1. **Noticing** — a symptom appears, or (from increment 6.4) an alert fires ([ADR 040](<https://aureliusenterprise.github.io/chore-retire-outage-limiter-tests/architecture/adr/040-the-system-raises-its-hand-when-it-is-broken/index.md>)). The first person to notice is the recorder, not the decider.
2. **Triage** — any maintainer is the decider: confirm impact, choose investigate / mitigate / accept. Mitigation on dev systems needs no permission; a mitigation that touches real data needs a second maintainer.
3. **Act** — the decider acts or delegates. The evidence is inside the system (ADR 016): the observability stack (Grafana, Prometheus, Loki, Tempo), the server's logs, the store's health endpoint — reachable without provisioning anything external (ADR 041 R4).
4. **Escalate** — possible data loss pulls in the dataset's owner (below); suspected secret exposure switches to the rotation path above.
5. **All-clear and record** — the decider declares the end and writes the one-page record: symptoms, actions, cause, follow-ups (ADR 041 R5). Follow-ups that should become triggers become alert rules at 6.4 (ADR 041 R6).

## Dataset Ownership

[ADR 042](<https://aureliusenterprise.github.io/chore-retire-outage-limiter-tests/architecture/adr/042-every-dataset-has-an-owner-who-answers-for-it/index.md>) R1/R5/R6: the owner is the workspace project that writes the dataset, named beside it; a new dataset arrives with its owner named in the change that creates it — one line, not a ceremony.

| Dataset | Owner |
| --- | --- |
| Elasticsearch: `aurelius-atlas-typedefs` (entity indices from 2.2, audit from 3.5) | `aurelius-atlas-server` |
| Keycloak realm and its Postgres database | `dev/keycloak` |
| Example Postgres database (template slice) | `aurelius-atlas-fastapi-example`, removed with it (DD-019) |
| Operational signals (metrics, logs, traces) | `dev/observability`, custodian of a shared store (ADR 042 R2) |

The catalogue's store has one writer — the server — so shape arbitration has no live subject in the spine; it applies from the first dataset with a second reader-writer.

## Rehearsals (scheduled)

- **First rehearsal of the secret paths** (rotation, loss, break-glass) on dev secrets in a dev environment — before the first deployment that keeps real data (ADR 028 R2).
- **First game-day of the incident path** on the dev stack — same gate, and yearly after (ADR 041 R3); each rehearsal updates this page.
