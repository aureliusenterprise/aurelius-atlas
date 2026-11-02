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
