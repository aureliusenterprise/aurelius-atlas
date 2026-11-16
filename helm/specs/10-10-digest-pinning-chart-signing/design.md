# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-278. Third-party digests committed, own images stay tags; charts sign

- **Status:** Accepted
- **Increment:** 10.10
- **Date:** 2026-10-31

**Context.** The pre-pentest triage's M9: every chart image renders by
mutable tag, and published OCI charts are unsigned while their images are
keyless-signed (publish.yaml). A registry compromise, a mirror substitution,
or a retagged upstream silently changes what installs. A first design
sketch pinned _everything_: committed digests for the thirteen third-party
values plus a publish-time bake resolving each Aurelius image's digest into
the chart tree before `helm package`. The bake is what this entry rejects.

**Decision.** Three calls, the second at the user's explicit direction
("uncomplicate our pipeline by only pinning digests for third-party
images"):

1. **Every image block gains a `digest` field; the helpers make it win.**
   `<base>@<digest>` when set, `<base>:<tag>` otherwise — whatever produced
   the tag (appVersion chain, chart default, `global.image.tag`). Puller and
   issuer-wait images move from inline `printf "%s:%s"` joins to named
   helpers so they get the same branch (CHT-92).
2. **Only third-party digests are committed; Aurelius images stay tags.**
   The risk a digest answers is _someone else changing what a tag means_.
   The nine dhi.io pins carry committed digests (CHT-93); a weekly drift
   guard (CHT-96) fails when a tag bump forgets its digest refresh. Our own
   six images are written only by publish.yaml — after signing and
   verifying — and the published chart version that references them is
   itself immutable (OCI refuses re-push) and cosign-signed, so installing
   chart version X provably names this release's images. The bake would
   pin the release to itself a second time, at the cost of a publish-time
   rewrite of the chart tree (a workflow-local mutation invisible to
   review, whose output no CI render ever reproduces). Their `digest`
   fields stay `""` — a live operator override, not decoration (CHT-94).
3. **Charts sign like containers.** `helm-sign`/`helm-verify` join the helm
   plugin's inferred targets (DD-290's mechanism) against
   `ghcr.io/aureliusenterprise/charts/<chart>:<version>`, keyless, with
   `docker-verify`'s identity/issuer regexp contract; publish.yaml runs the
   pair right after `helm-publish` (CHT-95).

**Alternatives.** (a) Full bake (the first sketch) — rejected per 2; with
it went `tools/images/bake_digests.py` and the publish bake step, descoped
mid-increment. (b) Committed Aurelius digests bumped by the release itself
— rejected: every release would dirty the chart tree with a digest of its
own predecessor, and CI renders would trail the registry. (c) Dependabot
for the third-party pins — rejected as mechanism: its `docker` ecosystem
does not parse Helm values; the drift guard's refresh PR is the equivalent
flow. (d) `helm provenance` (.prov packages) instead of cosign — rejected:
cosign is what the image chain already uses, one identity/issuer contract
to audit, and the sign target rides the OCI artifact `helm push` already
uploads.

**Consequences.** A stock install pulls nine immutable third-party images
and a signature-verifiable chart; admission enforcement (policy rejecting
unverified images at the cluster) stays an operator follow-up named in the
runbook. The umbrella guard (CHT-97) classifies every rendered image as
Aurelius-tag or committed-pin, so an unpinned new image fails CI without a
registry call, and a pin that drifts from `conftest.PINNED` fails loudly.
`digest: ""` fields in the six Aurelius blocks look like dead config to a
newcomer; CHT-94 and the values comments carry the why. Next free DD: 279.

### DD-641. The cosign verify targets run serially; chart verify names its flag right

- **Status:** Proposed
- **Increment:** 10.10 (a fix, 2026-11-16)
- **Date:** 2026-11-16
- **Supersedes:** none

**Context.** The first publish run (tag `v0.1.0-rc.1`, 2026-11-16) failed at
"Verify container signatures": `run-many -t docker-verify` fans every project's
verify out in parallel, and the burst of cosign calls raced Sigstore's TUF
repository for its `trusted_root.json`. Two of ten fetches were refused
("failed to persist metadata"), and cosign's v3 bundles make the trusted root
required, so those two verifies failed while the images themselves were signed
and published fine. The same run exposed a second fault that never reached a
report: `helm-verify`'s command names `--certificate-identity-regex`, and
cosign knows only `--certificate-identity-regexp` (with the `p`, the name the
CHT-95 rule in `spec.md` itself misspells). Cosign rejects an unknown flag
before it touches the network, so every chart verify fails; the step had never
run before this tag, and the rerun would have hit it after rebuilding all
images.

**Decision.** Two changes in the plugin targets, and the same two in the spec
wording:

1. **`docker-verify` and `helm-verify` carry `parallelism: false`.** Nx then
   runs each verify alone on the machine, so cosign fetches the trusted root
   once per run instead of ten times in one burst. The publish chain's other
   targets keep their parallel fan-out: only the TUF client is the shared,
   rate-limited resource.
2. **`helm-verify`'s command names `--certificate-identity-regexp`.** The CHT-95
   wording in 10.10's `spec.md` carried the typo; CHT-95's contract is
   `docker-verify`'s identity/issuer regexp, which names the flag with the `p`.
   The merged spec is the reviewed record of the increment and keeps its text;
   this entry is the correction of what the shipped command must name.

**Reason.** A rate-limited fetch is transient, and a retry would usually pass —
but "retry and hope" as a release-gate posture hides the next real failure
inside the noise. Serialising the pair removes the race at its source for a
cost of seconds per release. The flag fix is not optional: the verify step is
what proves the chain (ADR 029), and a verify that always errors on an unknown
flag is a gate that never closes. A latent bug in a target that only the tag
workflow executes, with no unit-test seam for plugin target definitions
(`tools/plugins/*.ts` carry none), stays invisible until the release runs it —
which is how CHT-95's typo survived its own increment.

**Alternatives.**

- Retry with backoff around each verify: answers the symptom, adds a mechanism,
  and the serial run costs no measurable wall time.
- Pre-fetch the trusted root once per job and point cosign at the cached root:
  more moving parts than a fan-out switch; the burst stays a race for any other
  cosign caller in the job.
- Move `publish.yaml` to the devcontainer runner pool while in here: rejected —
  the TUF rate-limit is runner-agnostic (it is the same fetch on any machine),
  so the runner choice is independent of this fix (left as its own open
  question).

**Consequences.** The verify pair now runs serially inside the publish job: the
ten image verifies and the chart verify take seconds apiece instead of
overlapping, and the burst that Sigstore's TUF CDN refuses no longer exists.
The fix lives in the plugin source, so it reaches a workflow run only through a
tag that is cut after it — the `v0.1.0-rc.1` workflow still runs the plugin
code of its own tag, and re-running that tag re-runs the old code. The rc line
moves to `v0.1.0-rc.2` from `main`. The verify commands stay untested by CI's
unit tier (they need a registry and an OIDC identity): their first real gate is
the next publish run, and the serial/flag facts above are what a reviewer
checks.
