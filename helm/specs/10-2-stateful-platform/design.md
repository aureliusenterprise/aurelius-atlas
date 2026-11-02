# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is never
edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-253. The chart-contract suite lives at the workspace root and renders with the helm CLI

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** The chart-contract pytest suite lives at the workspace root
(`tests/`, owned by the root `aurelius-atlas` project through an explicit
`test` target in the root `project.json`). It renders each chart with the
`helm template` CLI in a subprocess and asserts the rendered manifests —
settings keys, Secret references and shapes, certificate SANs, probe shapes,
pg_hba lines, the realm byte-equality — instead of unit-testing template
helpers. The suite skips when `helm` is absent (it ships in the devcontainer
and the CI runner, so in CI it never skips).

**Reason.** A chart is a YAML generator and its contract is the rendered
manifest; testing the manifests is testing the contract (CHT-06's gate only
proves the render _succeeds_ — 10.2 makes the first time real containers
appear in the output, so the output's _content_ needs guarding). No `dev/*`
chart owner is a Python package and none may become one (their `project.json`
files are chart-owner stubs), and the contract spans the umbrella plus the
component charts at once — the root is the only project above that seam. The
`helm` CLI is the only faithful renderer; a Python re-implementation of
Helm's template engine does not exist and a `helm`-library shim would drift.
Rendering in a session-scoped fixture keeps the suite at ~2 s.

**Alternatives.** (a) Colocate under each chart's `tests/` as pytest files —
rejected: the chart owners have no `test` target (they are not Python
projects) and the umbrella↔component joins (Secret names a component consumes,
the issuer reference) have no single chart to live in. (b) Rely on the
`helm-template` render gate plus review — rejected: DD-294's trial showed
renders that pass lint while producing crash-looping pods; the invariants need
assertions. (c) Make the root project a uv member — rejected: `.` already is
the workspace itself; adding the tests as a package would churn
`uv sync`/release for a suite with no import surface. The root `project.json`
is what enables a target here, and with it the python plugin also infers a
root `typecheck` (`uv run pyright .`) — harmless (nothing in CI targets it;
every package is type-checked at home) and left in place.

**Consequences.** Chart edits key the target's cache through
`inputs: helm/**, dev/*/helm/**`, so any chart change re-runs the suite in CI
(the root project is affected via the umbrella's implicitDependencies anyway).
The suite is the pattern 10.3 extends when the app charts land; the
`covers`-marker rule ids (CHT-10..19) give `aurelius-atlas-trace check` the
spec-to-test map. Next free DD: 254.

### DD-254. Deploy-time credential generation lands in 10.2 with publish and rotation in 10.4

- **Status:** Accepted
- **Increment:** 10.2 (re-sliced from 10.4's share of DD-287)
- **Date:** 2026-10-28

**Decision.** The umbrella's deploy-time credential generation (DD-287's
mechanism: `randAlphaNum 32` for every empty value, `lookup`-preserve across
upgrades, values-supplied wins, one Secret per consumer, none committed)
ships in 10.2 — but only the five Secrets its workloads consume:
`<release>-elasticsearch` (elastic-password), `-keycloak-admin` (user/password),
`-keycloak-database` (user/password, shared by Keycloak and the bundled
Postgres), `-keycloak-users` (writer-password/reader-password), and
`-otel-clients` (OTEL_INGEST_CLIENT_SECRET). Each renders only while its
consumer chart is enabled. 10.4 keeps the rest of DD-287's promise: the
remaining secrets (the collector legacy token and the observability slice's
credentials, the webapp's edge token), the chart OCI-publish polish, and the
operator runbook around retrieval and rotation.

**Reason.** 10.2's acceptance is "the stateful pods reach Ready on a cluster"
— every one of them reads a generated Secret at boot (CHT-13/16), so the
generation is not separable from the workloads that consume it: without it,
the increment's own hand check would need out-of-band Secrets, exactly the
trial-fixup shape DD-294 called out as the thing acceptance must not need.
The five are also the complete set no other increment needs earlier. The
10.4-only parts stay in 10.4 because their consumers (collector, webapp edge)
land there.

**Alternatives.** (a) Ship all of DD-287's secrets now — rejected: a Secret
with no consumer is dead config that 10.3/10.4 would re-shape anyway; (b)
keep generation in 10.4 and hand-generate for the hand check — rejected: the
`lookup`-preserve pattern is subtle and untested-by-CI until real upgrades
run (10.5); deferring it also defers its first real exercise past its own
increment.

**Consequences.** The umbrella's `secrets.*` values block is the operator's
supply surface; the component charts consume strictly by `<release>-<purpose>`
names (their `*SecretName` values bring your own, which skips generation —
the chart renders the consumer regardless, pointing wherever told). The
collector legacy Secret gains a composed `otel-header` key (the
`"Authorization=Bearer <token>"` pair) when 10.3/10.4 wires its consumers —
env values cannot concat from a `secretKeyRef`, so the composition belongs in
the Secret, not the chart. Next free DD: 255.

### DD-255. The coredump agent ships as its own image project

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** The Elasticsearch coredump-agent jar (the no-op javaagent that
absorbs the fatal `java_lang` dump attempt on GKE, dev/elasticsearch's
workaround) ships as a real image — `aurelius-atlas-elasticsearch-agent`
(`tools/es-coredump-agent/`, a `dhi.io/busybox` base plus the committed jar) —
and the store's StatefulSet mounts it as an init container copying the jar to
an emptyDir the JVM's `-javaagent` flag reads. The jar itself stays committed
(`coredump-noop.jar`, 1.9 KB, byte-stable; `build.sh` regenerates it) and a
chart-contract test pins the image reference and the flag.

**Reason.** The alternative shape — embedding the jar's bytes in a chart
ConfigMap — hides a shipped binary artifact from every supply-chain control
this workspace already runs for images: the SBOM (CycloneDX), the vulnerability
scan (`docker-vuln-scan`), the cosign sign/attest/verify chain
(publish.yaml), and the registry ACL. An image flows all of them for free the
moment it exists as a project (the docker plugin infers the eight targets from
the `Dockerfile` alone; publish.yaml's `run-many -t docker-publish` picks it up
with no wiring). It also keeps the chart honest: a ConfigMap jar makes every
install carry the bytes; an image reference makes the store chart depend on a
versioned, signed artifact like every other workload.

**Alternatives.** (a) ConfigMap-embedded base64 jar — rejected above (supply
chain), plus a 1.9 KB binary blob in chart values-review. (b) Bake the jar
into a custom ES image — rejected: forks the hardened `dhi.io` store image and
re-creates the maintenance the hardened image exists to avoid. (c) Drop the
agent in-cluster (hope GKE's `vm.max_map_count` story differs) — rejected: the
procfs write is the same node behaviour DD-008's CI lessons recorded; the agent
is what makes ES 9.x boot there.

**Consequences.** The image builds in CI (`affected -t docker-build`), is
published and signed with every release like any other, and takes
`global.image`'s registry/namespace so a mirror deployment redirects it. The
busybox base pins `1.37` (no `latest` tag exists on the hardened image). The
chart's `agent.image.tag` defaults to the appVersion chain like the store's
own image. Next free DD: 256.

### DD-256. The realm is a byte-copy chart asset and its placeholders resolve in Keycloak

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** The Aurelius realm (`master.json`, the 2 580-line identity
configuration) is a chart _asset_: `dev/keycloak/helm/files/master.json`, a
byte-copy of the dev import `dev/keycloak/import/master.json`, rendered into
the realm ConfigMap verbatim (`.Files.Get`). Helm performs no substitution in
it. Its `${DEV_USER_WRITER_PASSWORD}` / `${DEV_USER_READER_PASSWORD}` /
`${OTEL_INGEST_CLIENT_SECRET}` placeholders resolve at import time inside
Keycloak itself — the JVM's own
`-Dkeycloak.migration.replace-placeholders=true` flag (already the dev
compose's mechanism, DD-196) fed from the container's environment, which the
chart fills from the generated Secrets. A chart-contract test byte-compares
the asset against the dev import every run (the drift guard).

**Reason.** The dev import file is the single authored source (every dev/e2e
realm edit lands there first); Helm-substituting the placeholders would fork
that source per environment. More than drift, the decisive fact is
reproducibility: a Helm-rendered `randAlphaNum` secret appears twice in one
render (the realm ConfigMap and the Secret), and `lookup` cannot protect the
ConfigMap side — a pod rescheduled later gets a realm baked with yesterday's
rendered value while the Secret holds today's, a boot-order-dependent
credential mismatch. Keeping the file byte-identical to what dev already
imports proves the chart path and the dev path carry the same realm, and
Keycloak's placeholder resolution — the mechanism the dev stack runs today —
is the same one that resolves from the Secret-fed env.

**Alternatives.** (a) `tpl`/substitution over the file in-chart — rejected:
the double-`randAlphaNum` race above, plus the file's 2.5 KB of `${env:...}`-
adjacent JSON full of braces Helm would have to be told to ignore. (b)
Generate the realm from chart values — rejected: forks the source and loses
every realm edit; the file is the API. (c) A CI check comparing the copy
instead of a test — rejected: the chart-contract suite is the established
place for render-time invariants (DD-253); a byte-compare there runs on the
same gate.

**Consequences.** Editing the dev import requires re-running the byte-copy
(`cp dev/keycloak/import/master.json dev/keycloak/helm/files/master.json`) and
the test fails until it is done — deliberate: the two files may only differ in
the same commit. The browser-facing redirect URIs in the realm stay
localhost-only for now; per-environment redirects are 10.3's webapp work and
will extend the asset (or a values-driven patch) then, not by Helm-substituting
secrets. Next free DD: 257.

### DD-257. Stateful workloads run as their image's declared uid, with fsGroup for volumes

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** Every stateful workload of the platform charts pins its
container to the uid the image itself declares — Elasticsearch 1000,
Keycloak 65532, Postgres 70 — with `runAsNonRoot: true`, matching
`runAsGroup`, and `fsGroup` set to the same uid for the mounted volumes.
The chart sets no `runAsUser: 0` anywhere and relies on no privilege drop
in the image. `fsGroup` is the in-cluster equivalent of the compose
stacks' one-shot `volume-init` chown: the kubelet group-owns the
provisioned volume at the fsGroup gid, so the dynamic-provisioner path
needs no init-container root.

**Reason.** Found in the 10.2 minikube hand check, not on the drawing
board. The first install crashlooped both stateful pods: Elasticsearch
exited with `can not run elasticsearch as root` (its JVM refuses uid 0 in
`initializeNatives`), and Keycloak's re-augmentation failed with
`AccessDeniedException` on `/opt/keycloak/lib/quarkus/transformed-bytecode.
jar` because the pod ran uid 1000 while the image owns that tree at 65532.
The charts had inherited a belief from the dev compose comments — that the
store image boots as root and drops privilege via `gosu` before exec'ing
the JVM, so the pod should run as root. That is upstream Elastic's image;
the hardened `dhi.io` images have no root stage at all: the ES entrypoint
is `umask 0002` then exec, its `Config.User` is `1000`, and Keycloak's is
`65532` (Postgres 70). The image's declared user is the only correct
`runAsUser`, and the hand check is the level (of the three in `AGENTS.md`)
that catches a wrong one.

**Alternatives.** (a) `runAsUser: 0` + hope for a gosu drop — rejected:
crashes the store outright, and giving root to pods that never need it
violates the hardening posture the images exist for. (b) Omit
`podSecurityContext` and inherit the image user — rejected:
`runAsNonRoot` must be explicit for the posture to be checkable, and
`fsGroup` must be set explicitly or dynamically-provisioned volumes mount
root-owned against the wrong gid. (c) An init container that chowns as uid
0 (the compose's `volume-init` shape, kept) — rejected in-cluster:
`fsGroup` does the same job without granting any container root.

**Consequences.** The chart-contract suite pins each workload's uid
against the image's declared user (`test__runs_as_image_uid_with_fs_group`
in both stateful suites), so a base-image uid change fails the gate with a
pointer to this entry. Compose comments claiming a root-entrypoint boot
describe upstream images, not `dhi.io` ones — they are corrected where
10.2 touched them, and any future chart copies the uid from
`docker inspect`, never from prose. Next free DD: 258.

### DD-258. A bundled database dates its consumer with a wait-init and its own probe SANs

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** Two facts the compose siblings state outright and the first
chart port lost, both caught by the 10.2 minikube hand check. (1) The
Keycloak pod waits for the bundled database: a `wait-for-postgres` init
container (bundled flavor only) retries a TCP dial of the database's
headless Service until it answers — the Kubernetes port of the compose's
`depends_on: postgres-keycloak: condition: service_healthy`, which has no
direct equivalent because Kubernetes never gates one pod's start on another
pod's readiness. (2) The database's Certificate carries `127.0.0.1` as an
IP SAN next to the service-name DNS SANs: the `verify-full` `pg_isready`
probes dial `127.0.0.1` (the compose healthcheck's own target, and the dev
`tls.json` lists the address for exactly this), and `verify-full` compares
the dialled host against the SANs — without the loopback entry the probes
can never pass, the pod never turns Ready, and the headless Service never
publishes an endpoint for Keycloak's JDBC URL to resolve.

**Reason.** The first install deadlocked the pair exactly along those two
missing facts: Keycloak logged `UnknownHostException: atlas-keycloak-postgres`
(it started before the database was reachable and prod mode exits on the
JDBC failure), while Postgres sat Ready-in-name-but-0/1 because its startup
probe failed hostname verification against a certificate that could not
amever validate the address it was probed at. The init's wait is
transitive on TLS correctness — the headless Service publishes the pod only
after the pod's own verify-full probe passes, so a successful dial already
proves the database serving verified TLS. bash's `/dev/tcp` is the shape
the compose's Keycloak healthcheck uses and needs no client tool added to
the hardened image.

**Alternatives.** (a) A `startupProbe` failure-threshold budget on Keycloak
instead of the init — rejected: prod-mode `kc.sh` exits on the first JDBC
failure, so probes cannot ride out the race; the restart loop only
re-rolls the dice, which is what made the deadlock look random. (b) Have
the probes dial the service name instead of loopback — rejected: during a
pod's own NotReady phase its endpoint is unpublished, so a readiness probe
addressed through the Service could fail on its own not-ready status —
loopback is the only address that answers the instant Postgres itself is
up, which is why the compose (and every Postgres guide) probes `127.0.0.1`.
(c) `publishNotReadyAddresses` on the database Service — rejected: that
would hand consumers a dial target before the database accepts connections,
replacing the deadlock with a worse silent race.

**Consequences.** The chart-contract suite pins both: the init container
present under bundled and absent under external, and the Certificate's
`ipAddresses: [127.0.0.1]`. A future cluster-ca path that issues per-SAN
certificates must keep the loopback entry as long as the probes dial
loopback. Next free DD: 259.

### DD-259. The chart-managed trust root is a namespaced self-signed issuer chain

- **Status:** Accepted
- **Supersedes:** the issuer shape in DD-286
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** `global.trust.createIssuer=true` (the default posture) builds
the cluster trust root as a three-resource chain in the app namespace: a
self-signed bootstrap `Issuer` signs exactly one `isCA: true` `Certificate`
whose Secret is the trust root (its name is `global.trust.caSecretName`,
defaulting to `<issuerRef.name>-ca`); a `ca`-type `Issuer` of that Secret —
the object every `Certificate` names in `issuerRef` — then signs every leaf.
Because every leaf descends from the one CA, the `ca.crt` cert-manager
places in each leaf Secret is the same root everywhere, and the file each
consumer pins verifies every peer's certificate. The chain is namespaced
(`Issuer`), so the umbrella's default `issuerRef.kind` becomes `Issuer`
(the component charts' standalone defaults follow); a `ClusterIssuer` stays
valid only for bring-your-own issuers (`createIssuer=false`, gke.yaml),
whose CA is off-cluster and installed via `caBundle` as before. DD-286's
decision stands in full except this issuer-shape clause.

**Reason.** The 10.2 hand check: a fresh minikube install reached Ready for
the store and the database but Keycloak refused its JDBC TLS with `PKIX
path validation failed`. The leaf Secrets told the story — the Keycloak
and database certificates were signed by two different CAs, which is what
a bare `selfSigned` issuer means: cert-manager generates a fresh private
key for every Certificate it self-signs, so "the issuer's CA" is a
per-certificate secret that cannot exist. DD-286's prose always assumed a
shared root ("a private root is the default, so the cluster's trust set is
closed and enumerable") — the implementation shipped in 10.1 contradicted
its own consequence. The namespacing is cert-manager's own constraint,
verified on the cluster before the charts changed: a `ClusterIssuer` reads
its CA Secret from cert-manager's namespace (`ErrGetKeyPair` otherwise),
while a `Certificate` can only write its Secret to its own namespace — the
chart can therefore never hand a `ClusterIssuer` a CA it created.

**Alternatives.** (a) Keep the self-signed `ClusterIssuer` and have each
consumer trust the issuer per leaf (mount every peer's `ca.crt`) —
rejected: N² trust material, renewed on every certificate rotation, and
it still cannot express "verify the name I dial" across independently
minted roots. (b) Make the chain a `ClusterIssuer` pair and copy the CA
Secret into cert-manager's namespace — rejected: the chart would write
into another system's namespace and race its garbage collection. (c)
Generate the CA key in the chart (a Helm-rendered private key in a
Secret) — rejected: the key lands in the release history and every
`helm get`, the exact posture DD-287 exists to avoid; cert-manager's
bootstrap chain keeps the key in its own secret with rotation built in.

**Consequences.** Three objects instead of one for the default posture;
the chart-contract suite renders and pins the whole chain (bootstrap spec,
root `isCA` + bootstrap issuerRef, CA Issuer spec, leaf refs `kind:
Issuer`), and the leaf certificates in the minikube hand check now share
one CA fingerprint. A CA rotation is cert-manager-renewal-driven and hits
the boot-time CA readers (store, Keycloak) — DD-286's restart-hook
consequence, still owed by 10.3. GKE overlays with `createIssuer=false`
are unaffected. Next free DD: 260.

### DD-260. Keycloak's management interface is TLS in prod mode, probes included

- **Status:** Accepted
- **Increment:** 10.2
- **Date:** 2026-10-28

**Decision.** Keycloak's three probes address the management port over
**HTTPS** (`httpGet.scheme: HTTPS`), and the startup budget is 30×10s
(300s). Prod mode puts TLS on the management interface as well as the
browser one — the same keypair serves both — so there is no plaintext
listener anywhere in the chart's posture (`KC_HTTP_ENABLED=false` is a
chart-contract assertion), and a plaintext probe can only ever fail. The
budget covers what the cluster measures: `kc.sh start` re-augments the
Quarkus runtime into the container's image filesystem on every new
container (the PVC holds the realm and cache, not the augmented
runtime-layer), which on minikube's CPU took ~165s end to end.

**Reason.** The last hand-check failure, and the subtlest: the trust fixes
worked (realm import ran over JDBC TLS, bootstrap completed in ~2.5s after
a 165s boot) yet the pod restarted eleven times. kubelet logged
`Get "http://…:9000/health/ready": EOF` — the dev healthcheck's plaintext
`/dev/tcp/localhost/9000` probe shape was copied from the compose, where it
works only because dev runs the plaintext listener as ADR 039's named
relaxation. The chart renders prod posture, and an HTTP probe against a TLS
port gets an EOF — the pod's container then died on a
startup-probe-threshold kill seconds after finishing its work. The widened
budget is the same measurement: the earlier 180s (the compose's
`start_period`) left 15 seconds of margin against a cold start, and a
kill-then-reaugment loop (each restart pays the augmentation again) looked
exactly like a broken chart.

**Alternatives.** (a) `KC_HTTP_ENABLED=true` and a plaintext management
listener in-cluster — rejected: the compose's relaxation is named and
scoped to dev (ADR 039); a chart posture that exists to be the hardened
shape does not open a second plaintext port. (b) TCP probes instead of
HTTP — rejected: they'd pass on a listening socket whose health checks are
failing (the compose's HTTP-shape probe exists for the checks); TLS HTTP
probes cost kubelet nothing extra. (c) Pinning the probes' certificate
verification to the cluster CA — not an option kubelet offers (HTTPS
probes ignore certificate validation), and the right one: a liveness
channel is an escape hatch, not a trust surface.

**Consequences.** The probe scheme is a values knob
(`probes.scheme`, default HTTPS) rather than a template literal. The
augmentation cost is per-container, so a rollout or reschedule always
pays it: the readiness gate plus the 300s budget absorb it; a future
image that ships the augmented runtime (a custom build) can shrink the
budget. The chart-contract test pins the HTTPS scheme and a startup
budget of at least 300s. Next free DD: 261.
