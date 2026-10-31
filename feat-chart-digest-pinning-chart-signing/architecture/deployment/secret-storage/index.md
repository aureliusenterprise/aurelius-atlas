# Secret storage — alternatives and tradeoffs

Status: **analysis, decision pending** (pre-pentest review, 2026-10-29). This page analyses where the system's runtime credentials should live. It changes nothing: today's behaviour is DD-244's (the umbrella generates every empty credential with `randAlphaNum`, preserves it across upgrades with `lookup`, and writes one Secret per consumer). The pentest review flagged that Helm release storage ends up being the system's secret store, and an auditor will ask "how do you rotate this?" — this is the decision space.

## The current shape and what it costs

The generated values (`secrets.*` in `helm/values.yaml`) render into the release Secret and into every `helm get values` output, in plaintext:

- The chart-contract posture is deliberate: a stock install needs **no external secret system**, which is what makes `helm upgrade --install atlas   helm -f environments/minikube.yaml` work at all (CHT/ADR 057).
- The cost: every credential is readable by anyone with `get secrets` on `<release>-*` or on Helm's release Secret (`sh.helm.release.v1.*`), a rotation means editing values and re-rendering, and `--set secrets.x=…` puts a real credential into shell history and CI logs.
- A real gap found while writing this: a consumer supplying a bring-your-own Secret name (`credentialSecrets.*`, `*SecretName` values) does **not** suppress the umbrella's generation of `<release>-<purpose>` — the block gate is the consumer chart's `enabled` flag alone. With an external store wired in, the chart would still mint a parallel set nobody uses. Fix: gate generation on "no bring-your-own name given" alongside the segmentation work.

## What a production deployment needs

1. A source of truth outside the Helm release (rotation without re-render).
2. Least-privilege read access per consumer (already Secret-per-consumer — RBAC can now name them).
3. A rotation story an auditor can watch: change the store, the workload converges.
4. No real credential in git, in shell history, or in CI logs.

## Alternatives

| Option | How it joins this chart | Pros | Cons |
| --- | --- | --- | --- |
| A. Status quo + RBAC hardening | Document that `sh.helm.release.v1.*` read access is admin-level; namespace-scoped Roles per consumer for the `<release>-*` Secrets | Zero new moving parts; honest about being the dev/stock posture | No rotation path (a values edit + re-render; pods need restarts); release Secret still holds everything; auditors keep asking the question |
| B. External Secrets Operator (ESO) | An `ExternalSecret` per `<release>-<purpose>` syncs from the org store (GCP SM / AWS SM / Vault / Azure KV) into the same Secret names the charts already consume; prod values set the `*SecretName`/`credentialSecrets.*` bring-your-own fields and the chart's generation stops (gap above) | The chart contract **already fits** — consumers join by Secret name, never by generation; per-store rotation policies; ESO refreshes without redeploy; no secret ever enters git or values | New cluster operator; the org store becomes a deployment prerequisite (runbook grows); drift care needed so ESO owns the Secret and Helm doesn't adopt it (the `lookup` pattern must see it as existing — it does, `lookup` reads live Secrets) |
| C. Sealed Secrets | A controller re-encrypts with the cluster's keypair; the plaintext never leaves the cluster | Git-safe artifacts; offline creation | Generated-value bootstrapping is manual (create → seal → commit round-trip per credential); key rotation is a ceremony; controller is a decrypt-or-relock SPOF; least-suitable for generated credentials |
| D. SOPS + git-decrypt (age) | The workspace already uses SOPS for `.env.enc` (devcontainer age keys); secrets-as-files decrypted at deploy time by the CI operator | Familiar tooling; small step from today | Designed for env files, not k8s Secrets: every consumer here reads a `secretKeyRef`, so it needs a gitops reconciler (Sealed-Secrets-like or `sops-template-controller`) bolted on; age-key sprawl mirrors the devcontainer key problem at prod scope; same "rotate = git push" ceremony |
| E. Vault (agent/CSI injector) | Mount Vault paths as files, or CSI-inject the Secret payloads | Strongest rotation/dynamic-credential story; audit logging in the store | Highest ops burden of all options; the chart's consumers are Secret-key based (env `valueFrom`), so a Secret-sync step (Vault External Operator) is wanted anyway — at which point it is option B with a different store |

## Decision drivers

- **Who runs the prod cluster.** If the platform team already runs ESO or Vault, B/E is nearly free; greenfield pushes toward B's smaller surface.
- **Rotation is the audit question.** Only B and E answer "change it in one place, workloads converge" without re-rendering the release.
- **Fit with the existing contract.** The chart's whole credential surface is Secret *names* (DD-244's `*SecretName` values exist exactly for this); B needs no chart redesign — it needs the generation gate fixed and a runbook section.
- **Git-hygiene.** C and D keep ciphertext in git; B/E keep nothing in git.

## Recommendation (pending)

Split by audience, keep both first-class:

1. **Stock/dev installs keep DD-244 generation** (zero-dependency install is a feature, not an accident).
2. **Production takes option B**: ESO (or Vault External Operator over the org's store) owns the `<release>-<purpose>` Secret objects; the umbrella's generation is suppressed when the consumer names its own Secret (fix the gate), and `secrets.*` values stay a dev-only path. Rotation = edit the org store; ESO refreshes; consumers restart on their own schedule (note: the components read these as env vars at boot, so rotation still needs a rollout — a documented `kubectl rollout restart` step, or checksum annotations later).
3. Keep option A's RBAC note in the runbook either way — least-privilege on the generated Secrets is good hygiene at every tier.

Option A alone leaves the rotation question unanswered; C and D fight the generated-credential shape; E is B plus cost. B is the smallest system change that answers the audit question.

## References

- DD-244 (deploy-time credentials, generation + lookup-preserve), CHT-19, DD-254/DD-256 (secret-per-consumer joins, realm placeholder import).
- `helm/AGENTS.md` — the values contract for `credentialSecrets.*` / `*SecretName` bring-your-own fields.
