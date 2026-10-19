# Configuration Management

Settings arrive at start-up through one channel and fail loudly ([ADR 018](<https://aureliusenterprise.github.io/main/architecture/adr/018-settings-arrive-at-startup-through-one-channel/index.md>)). The contract is the same everywhere; what differs is who supplies the values. Production is first below, and the development and CI arrangements come after.

## Production

The unit that ships is the container image ([release management](<https://aureliusenterprise.github.io/main/architecture/platform/delivery/release-management/index.md>)). Its configuration is the environment, read once at start-up into a frozen settings object — no library reads the environment afterwards, and apps pass settings objects down. Validation failures (missing key, bad scheme, half a TLS pair) stop start-up with a message naming the variable, so a misconfigured deployment never serves traffic.

What a deployment must supply has no defaults — the service does not start without it (SRV-01, SRV-02): the store's endpoints and credentials, and the CA that signs the store's certificate. Where those values come from — an orchestrator secret store, certificate provisioning — is the [deployment](<https://aureliusenterprise.github.io/main/architecture/platform/delivery/deployment/index.md>) page's subject (6.4). The knobs are named, with defaults and validation, in the server's design documentation: [Configuration](<https://aureliusenterprise.github.io/main/api-reference/apps/aurelius-atlas-server/#configuration>).

> [!WARNING]
>
> **A half TLS pair stops the server from starting**
>
> The serving certificate and key are a pair: both set, or both unset — enforced at start-up. A container that mounts only the certificate exits with a message naming the missing variable; this is the design working, not a broken image.

**Naming.** App-owned settings carry a per-project prefix, so two projects in one workspace can never read each other's values. Keys that third-party code (the platform's, the observability exporter's, infrastructure images) reads must stay bare to be read at all — the prefix list lives in the root `AGENTS.md`.

> [!NOTE]
>
> **Why do the variable names carry such long prefixes?**
>
> One project's environment leaks into all of that project's tasks, so a bare `PORT` set by the frontend example would be visible to the server's tests. The prefix is what keeps two projects' settings from shadowing each other; keys the ecosystem's own images read must stay bare to be read at all.

## Development and CI

The same channel, with repository-local plumbing: each project's plaintext `.env` carries dev defaults, and its real settings travel with the code as ciphertext ([ADR 008](<https://aureliusenterprise.github.io/main/architecture/adr/008-secrets-never-in-plaintext/index.md>)). The rules that keep the two in step — decryption as a task dependency, ciphertext as the source of truth, TLS material as configuration — are the secrets guide's, with the commands: [Secrets Management](<https://aureliusenterprise.github.io/main/contributor-guide/secrets-management/index.md>).

> [!WARNING]
>
> **Editing `.env` alone is undone by the next CI run**
>
> Ciphertext is the source of truth and plaintext is generated from it. An `.env` edit that is not re-encrypted disappears the moment CI decrypts — the change works locally and fails in the pipeline, with the plaintext file as the only visible symptom.
