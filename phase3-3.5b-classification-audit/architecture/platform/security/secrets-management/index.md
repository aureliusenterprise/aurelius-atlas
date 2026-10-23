# Secrets Management

The architecture view of secrets in Aurelius Atlas. The practitioner's walkthrough — generating your key, registering it, re-encrypting — is the [Contributor Guide's Secrets Management](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/contributor-guide/secrets-management/index.md>).

## Production

The running system receives secrets the way it receives every setting: through the environment the deployment supplies at start-up ([configuration management](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/architecture/platform/delivery/configuration-management/index.md>)) — the store password is a secret type and never appears in logs. Where those values live (an orchestrator secret store, a KMS) is the deployment arrangement's choice; the system asks for values, not for a vault ([ADR 018](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)).

- **Ownership**: operational secret handling — rotation, loss, break-glass — has a named owner and a rehearsed path ([ADR 028](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/architecture/adr/028-operational-secret-handling-has-a-named-owner/index.md>)).
- **Pipeline boundaries**: CI token and secret handling follows the pipeline's declared scoping; artifacts carry inventories so a leaked dependency is a lookup ([ADR 033](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/architecture/adr/033-shipped-artifacts-carry-a-contents-inventory/index.md>)).
- **TLS material**: a deployment serves its own certificates; the repository's material is development-only ([TLS Certificates](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/contributor-guide/tls-certificates/index.md>)).

## Development and CI

Three rules keep developer secrets honest; the commands for each are the [contributor guide's](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/contributor-guide/secrets-management/index.md>).

- **Ciphertext travels with the code** ([ADR 008](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/architecture/adr/008-secrets-never-in-plaintext/index.md>)): each project's real settings are committed encrypted to a recipient list; plaintext files carry dev defaults only. Ciphertext is the source of truth — an edit that is not re-encrypted is undone by the next CI run.
- **Keys are per person, not shared**: each developer holds their own key, and the recipient set is declared in version control. Adding a person is a key-list change; removing one is rotation.

> [!NOTE]
>
> **Why keys per person, not one team key?**
>
> A shared key has to be replaced whenever anyone leaves — and every encrypted file re-encrypted under the fear of who still has the old copy. With per-person recipients, offboarding is removing one name from the recipient list and rotating: the departure *is* the rotation, with no secret to hunt down.

- **Decryption is a task dependency**: every run that reads configuration first decrypts, so a run either has its configuration before it starts or fails naming the key it needed — the loud failure ADR 018 requires.

> [!WARNING]
>
> **A fresh clone fails tests until your key is registered**
>
> Almost every `serve`, `test`, and `e2e` target first runs a decrypt step. Decryption only succeeds once your public key is on the recipient list. Until then, commands fail with a decryption error — this is expected, not a broken setup; the contributor guide walks through [registering your key](<https://aureliusenterprise.github.io/phase3-3.5b-classification-audit/contributor-guide/secrets-management/index.md>).
