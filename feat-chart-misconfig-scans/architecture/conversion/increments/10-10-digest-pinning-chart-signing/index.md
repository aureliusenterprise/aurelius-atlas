# 10.10 Digest-pinned images and signed charts

- **Status:** in progress
- **Pull request:** \#184 (stacked on \#183)
- **Records:** DD-278 (adds), DD-245 (relies on: the `appVersion` chain), DD-247/DD-250 (relies on: plugin-inferred chart targets), CHT-05/07 (relies on: the publish cascade)

## Scope

The pre-pentest triage's **M9** (supply chain: digest pinning + chart signing). Every workload image the charts render is addressed by **mutable tag** — `dhi.io/keycloak:26.7-debian13`, `ghcr.io/aureliusenterprise/ aurelius-atlas-server:v1.2.3` — so a registry compromise, a mirror substitution, or a retagged upstream silently changes what installs; "version v1.2.3" does not pin bytes. Images are keyless-signed at publish (`docker-sign`/`docker-verify`, publish.yaml), but **nothing verifies at install**, and the published OCI **charts themselves are unsigned**, so the artifact set the release ships is only half attested.

This increment delivers both halves of M9:

- **Digest pinning (third-party only).** Every image block in every chart's values gains a `digest` field; the image helpers render `<base>@<digest>` whenever a digest is set and `<base>:<tag>` otherwise. The thirteen chart-pinned third-party image values (nine distinct dhi.io tags; the collector and curl pins repeat across three charts each) gain **committed digests**: a stock install pulls immutable digests. The six Aurelius images stay tag-referenced by design: the risk digest pinning answers is *someone else changing what a tag means*, and our own tags are written only by publish.yaml after signing and verifying — while the published chart artifact is itself immutable (OCI refuses re-pushing a version) and cosign-signed below, so an install of chart version X provably names the release's images without a second pin. Their `digest` fields exist for operators who want to freeze a patch level, empty in the repo.
- **Chart signing.** The helm plugin gains `helm-sign` and `helm-verify` targets (the docker plugin's keyless pair, mirrored: cosign against the pushed OCI chart artifact, verification against the same identity/issuer regexps), and the publish workflow signs and verifies the charts exactly as it already does for images.
- **Digest freshness.** `tools/images/chart_digests.py` extracts every (repository, tag, digest) triple from the chart values and compares each against the registry's current manifest for that tag. A weekly workflow fails on drift and a dispatched run opens a refresh PR, so a tag bump without its digest refresh cannot sit unnoticed.

This increment does **not** deliver: digest pinning of the **Aurelius images** (their tags are release-scoped, written only by the signed publish chain, and the chart signing half of M9 already proves the pairing — DD-278 records the deliberate simplification), admission enforcement (a cluster policy rejecting unsigned/unsigned-by-identity images is an operator posture — runbook note only), chart provenance/attestation beyond the cosign signature, digest pinning of the **dev compose** stacks (loopback shape stays tag-based, CHT-91's reasoning), any change to image signing (already in `docker-sign`/`docker-verify`), or Dependabot coverage of the chart values (its `docker` ecosystem does not parse Helm values; the drift guard is the mechanism here).

## Semantics

| Id | Rule |
| --- | --- |
| CHT-92 | Every chart image value block carries a `digest` (default `""` where unpinned). The image helpers (the Aurelius `<chart>.image` family, the chart-pinned `image`/`pgImage`/`agentImage`, observability's `componentImage`, and new puller/issuer-wait helpers replacing the inline `printf "%s:%s"` joins) render `<base>@<digest>` when `digest` is non-empty, `<base>:<tag>` otherwise — the digest always wins over the tag, whatever produced the tag (appVersion chain, default, `global.image.tag`). The `<base>` (registry/namespace/name or repository) is unchanged by the digest. |
| CHT-93 | The chart-pinned third-party images ship committed digests in values: elasticsearch, keycloak, postgres (bundled DB), the opentelemetry-collector and curl pins in all three charts that carry them, and observability's prometheus/loki/tempo/grafana. A stock render — standalone or umbrella — references every one of them as `<repo>@sha256:<hex>`; no third-party workload image renders by tag. |
| CHT-94 | Aurelius images (server, webapp, data2model, lineage-model, validate-entity, the elasticsearch coredump agent) are **not digest-pinned**: their `digest` fields stay `""` in the repo and in every published chart, and the pipeline bakes nothing — release integrity for own images rides the immutable, cosign-signed chart artifact (CHT-95) plus the signed publish chain. The field remains a live operator override (CHT-92: set it and the render switches to `<base>@<digest>`). |
| CHT-95 | `helm-sign` cosign-keyless-signs the pushed chart artifact (`ghcr.io/aureliusenterprise/charts/<chart>:<version>`); `helm-verify` verifies it with the same `--certificate-identity-regex`/`--certificate-oidc-issuer-regexp` contract as `docker-verify` (defaults `.*`, overridden by the workflow's pinned identity/issuer). publish.yaml runs both after `helm-publish`, same runner, same id-token identity as the image chain. The targets are inferred by the helm plugin (DD-247's mechanism) for every chart owner. |
| CHT-96 | `uv run python tools/images/chart_digests.py --check` exits non-zero when any committed digest differs from the registry's manifest for the same `repository:tag` (or is missing while the tag is pinned); `--fix` rewrites the digest lines in place. A weekly scheduled workflow (plus `workflow_dispatch`, with a mode that opens the refresh PR) runs the check. Pure logic (parse/diff/rewrite) is unit-tested against fixture values trees; registry calls live only in the workflow and manual runs. |
| CHT-97 | A chart-contract guard walks every container and initContainer of the stock umbrella render: each image is either an Aurelius tag reference (`ghcr.io/aureliusenterprise/<name>:<tag>`) or a pinned third-party reference (`<known repo>@sha256:<64 hex>`). An unpinned third-party tag fails the render test — this is the rule CI enforces, complementing the scheduled registry-side check (CHT-96). |

## Java origin

None — this increment ports no Apache Atlas behaviour. The reference is the pre-pentest triage's M9 item ("pin image digests + sign charts like containers"); images already sign, so the delta is the chart side plus the install-time immutability.

## Deviations

None against Atlas. Skipping the Aurelius-side bake that the first design sketch of M9 carried is deliberate (DD-278): a chart digest bake would pin the release to its own images a second time, for a supply-chain risk the signed publish chain already closes, at the cost of a publish-time rewrite of the chart tree. CHT-97 therefore pins the tag shape for Aurelius images in every render, committed or otherwise.

## Acceptance

- `npx nx run-many -t helm-lint helm-template` green (the chart owners).
- `tests/test__charts_umbrella.py` names CHT-97 (the render-side guard over the full stock stack) and CHT-94 (Aurelius images render by tag there — a committed digest on one would fail it).
- Per-chart suites (observability, elasticsearch, keycloak, server, webapp, aux) assert the digest-pinned third-party refs at their own renders and the digest override at the Aurelius joins (`image.digest=<digest>` renders `<base>@<digest>`, CHT-92).
- `tests/test__image_digest_tools.py` names CHT-96: parse → diff → rewrite against a fixture values tree (no registry, no docker).
- `tools/plugins/helm.ts` targets are exercised by `nx run aurelius-atlas-dev-keycloak:helm-sign --dry-run`-style graph checks only (cosign needs a pushed artifact; the real pair runs in publish.yaml — reviewed as code, same pattern as docker-sign).
- Runbook: install-from-OCI pulls digest-pinned third-party images and a signature-verifiable chart; verification one-liner (`cosign verify …charts/<chart>:<version> --certificate-identity-regexp …`); admission enforcement named as the operator-side follow-up.
- Hand check: not run in CI here (needs a release push); proven by render + unit tests + script fixtures.
