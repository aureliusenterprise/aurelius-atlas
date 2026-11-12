# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-508. The scanner charts stay out of the umbrella

- **Status:** Proposed
- **Increment:** 12.3
- **Date:** 2026-11-12

**Decision.** The three batch scanner charts are standalone charts at
`apps/<app>/helm/` with the full `global.*` contract declared locally (CHT-114).
They are never `dependencies:` rows of the `helm/` umbrella, and the umbrella's
values tree carries no scanner toggle. The "Adding a chart" recipe in
`helm/AGENTS.md` step 3 (register in the umbrella) is explicitly not followed
for these three, and the recipe gains a pointer to this entry.

**Reason.** The scanners read the customer's own systems — their databases,
their brokers, their file extracts — on schedules the customer owns. A catalogue
install that silently starts scanning customer data is a deployment the operator
did not choose, and a schedule is a data-access policy, not infrastructure.
Keeping the charts outside keeps that policy an explicit second install. The
customer half of the fleet may not even run the umbrella (the catalogue can
already run against a customer-hosted store and issuer), so an umbrella-only
distribution would also fail the deployments that need the scanners most.

**Alternatives.** Ship them as umbrella dependencies with `enabled: false`:
the row still implies the topology table's claim that the system "includes" the
scanner, and an operator flipping it on inherits the umbrella's namespace,
issuer, and secret roster whether that fits the scanner's data network or not.
Ship one combined "scanners" chart: one chart cannot match three owners'
release cadences, and DD-293 keys release wiring at the owning project.

**Consequences.** Each chart must render standalone, so each declares the full
`global.*` shape with empty defaults like every other chart (the existing rule
carries no cost here). The identity join cannot name a co-installed server
Service by convention, which is CHT-116's `catalogue.serverUrl` value instead
of a derivation. `helm/AGENTS.md`, `helm/README.md`, and each scanner's
`AGENTS.md`/`README.md` state the non-membership, so the next contributor does
not "fix" the missing umbrella row.

### DD-509. Scanner identities are registered and credentialled by the deployment, never by these charts

- **Status:** Proposed
- **Increment:** 12.3
- **Date:** 2026-11-12

**Decision.** A scanner chart consumes an identity Secret by name:
`auth.secretName` (default `<release>-scanner-clients`), key
`auth.secretKey` (default the app's client id). The chart never generates a
credential and never takes one as a plain value (CHT-116) — and no other
shipped chart generates one either: the umbrella carries no scanner Secret and
the hardened realm asset carries no scanner client (CHT-118/119). The
deployment registers the client in its own issuer and places the credential
where the chart's join points — its vault, its Secret manager, or a
hand-placed Secret under the default name.

**Reason.** The scanners deploy to customer environments (DD-508): the
customer runs them against their catalogue, and often against an issuer this
repository's charts never touch. A registration shipped from upstream would
preset a customer's identity topology the way DD-508 refuses to preset their
schedule — the same argument, one layer up. It also keeps the two readers
trivially consistent: the deployment that registers the client is the only
holder of its secret, so there is no roster to synchronise between an umbrella
Secret and a realm import on someone else's cluster. A CronJob cannot verify a
credential at render time (no issuer call from a template), so CHT-02's "the
deployment supplies" is literal: a wrong secret fails the run with a refused
token (DBS-02's exit-1 class), not the pod.

**Alternatives.** The umbrella generating a `<release>-scanner-clients` Secret
and the prod realm asset carrying the three clients when Keycloak is enabled:
every byte of it applies only when the customer installed our umbrella **and**
our Keycloak **and** accepts our client names — the minority of the
installations the scanners exist for — while the shared-realm roster would
then owe a drift guard for clients most deployments delete. The chart
generating its own secret: it cannot, since the issuer that must recognise
the client lives outside the chart.

**Consequences.** Each scanner chart's install story names one prerequisite
it cannot render: a registered client and a credential Secret (the deployment
page spells the shape: confidential, service account, `atlas-read` +
`atlas-write` on the server client). The repo's own dev path is untouched —
`dev/keycloak`'s compose keeps feeding the dev realm's scanner placeholders
from its `.env` (12.2/13.1/13.3), because that realm is the dev stack's, not
a customer contract. The server chart still accepts the scanner audiences by
default (DD-513): acceptance is ours to grant, registration is theirs.

### DD-510. The CronJob shape: Forbid, one deadline, no history beyond the limits, nothing else

- **Status:** Proposed
- **Increment:** 12.3
- **Date:** 2026-11-12

**Decision.** The workload renders one `CronJob` (CHT-115). `concurrencyPolicy`
defaults to `Forbid`: a scan that overlaps itself races its own idempotent
write (DBS-09's in-place update is safe, but the pair doubles the load for no
new fact). `activeDeadlineSeconds` defaults to 3600 so a silent database or
broker (DBS-02's, KSC-01's hang class) ends as a failed job rather than a
stuck pod, while the app's own timeouts still produce the named failure first.
The pod runs `restartPolicy: Never` (a retry is the next cron tick, not a
container restart), keeps the hardened context the service charts use, and
mounts no ServiceAccount token. `schedule` is a required value (CHT-115's
render guard). No `Certificate`, Service, or NetworkPolicy renders: the job has
no listener, and outbound traffic needs no policy in a charts tree that ships
no egress posture (the CHT-60 scope note).

**Reason.** The scheduler contract 12.2, 13.1, and 13.3 wrote for their images
("the scheduler owns when it runs; one run scans, writes, exits") is exactly
`CronJob` + `restartPolicy: Never`. Defaults that differ invite the two failure
modes of scheduled batch work: overlap (a replace policy stacking scans) and
zombie jobs (no deadline). Making `schedule` required follows CHT-02: silence
here is a misinstall, and a default schedule would scan whatever the values
happen to name, on the vendor's clock.

**Alternatives.** Argo CronWorkflow or another CRD: couples the charts tree to
a specific scheduler install (the same reason the charts never render a
GatewayClass). A Deployment with an in-process loop: contradicts the batch
boundary the three apps shipped (DD-460) and hides each run's success in pod
liveness. `allow` concurrency: two scans writing one tree at once is churn the
store tolerates but no one asked for.

**Consequences.** `ttlSecondsAfterFinished` is unset by default, so finished
Job history stays until the cluster's own GC or the operator's value trims it.
Helm's own hook annotations are not used: a scan that runs at `helm install`
time would surprise an upgrade, so the first scheduled tick is the first real
run. A deployment that wants an immediate first scan creates the Job once
(`kubectl create job --from=cronjob/...`), which the 12.3 hand check documents.

### DD-511. Scanner telemetry is a first-class block, optional and off by default

- **Status:** Proposed
- **Increment:** 12.3
- **Date:** 2026-11-12

**Decision.** Each scanner chart carries a `telemetry` block (CHT-125):
`enabled` off by default, `endpoint` required when on, and `auth.enabled` on
by default — auth on renders the app-owned leg's prefixed `OTEL_*` trio with
the ingest client and Secret defaulting to the job's own identity join
(DD-514's reuse rule), auth off renders the bare SDK env leg unauthenticated.
`extraEnv` stays the escape hatch for anything the block does not model.

**Reason.** These charts ship to customer clusters, where a customer's own
collector is a plausible one-line ask — and the CHT-117 passthrough answer
("set the four `OTEL_*` names yourself") makes the operator re-derive the
token-URL derivation and the Secret join the chart already performs. Making
the block reuse the identity the chart already renders means one credential
covers catalogue, broker, and collector unless the deployment opts into a
dedicated ingest client. Off stays the default because a batch job exports a
handful of spans per run: the umbrella's always-on posture (CHT-42, ADR 016)
does not transfer, and no stock install should start chatting to a collector
it never named. No otel client id enters the realm asset: like every scanner
credential, the ingest secret is the deployment's (CHT-119's rule).

**Alternatives.** Passthrough only: honest but manual, and the earlier draft
of this record chose it precisely because no _dev_ install needed it — the
customer-deployment scope reversed that. Telemetry with no off switch: a
CronJob that contacts an endpoint on a customer network without being told
to, which is what the flag prevents.

**Consequences.** The auth-on default assumes the reuse (the job's own client
mints its ingest token); a deployment whose collector demands a dedicated
ingest client sets `telemetry.auth.clientId`/`secretName` and registers that
client itself. TLS to the collector rides the same optional CA mount as every
other leg (CHT-117), and the auth-off leg pins it through the SDK's standard
`OTEL_EXPORTER_OTLP_CERTIFICATE` var rather than `CA_FILE` (DD-210).

### DD-512. The prod realm asset stays out of the scanner story; dev keeps its own path

- **Status:** Proposed
- **Increment:** 12.3
- **Date:** 2026-11-12

**Decision.** The scanner clients ride only the **dev** realm
(`dev/keycloak/import/master.json` and its helm copy, as 12.2/13.1/13.3
landed them, fed by the `dev/keycloak` compose envs). The hardened
`aurelius-atlas.json` asset gains no scanner client and no import env
(DD-509's rule, charted): the asset's minimal surface (CHT-75) and empty
`users` list stay as 10.7 shipped them. A customer deployment registers the
clients in its own issuer with the same shape the dev realm proves
(confidential, service account, `atlas-read`/`atlas-write` on the server
client).

**Reason.** The prod asset is the identity contract for the workloads the
umbrella deploys (10.7); the scanners are deliberately outside the umbrella
(DD-508), so shipping their clients there would register workloads the
umbrella never installs — and against whichever issuer a customer points the
job at, which is often not the one our charts run. The dev path proves the
shape end to end (the e2e suites mint real scanner tokens against the dev
realm), which is the repository's share of the contract; the customer's
registration is their runbook step, documented once on the deployment page.

**Alternatives.** Add the three clients to the prod asset gated on the
keycloak chart (the first cut of this increment): it hardcodes three client
names into the customer's realm for deployments that install our umbrella,
our Keycloak, and our names — and every other deployment deletes them. Ship
a scanner-registration job/hook in the chart: it would dial the issuer with
admin credentials the chart must also be given, inverting DD-509's join.

**Consequences.** The umbrella and keycloak suites pin the absence: no Secret
keyed by a scanner id among the umbrella's generated set, no client named
`*-scanner` in the prod asset, and the import envs unchanged (so a master
install no longer feeds scanner placeholders — it carries no scanner clients
either). The dev compose's `*_SCANNER_CLIENT_SECRET` envs stay exactly where
12.2/13.1/13.3 left them.

### DD-513. The server chart's audience default names the scanner clients

- **Status:** Proposed
- **Increment:** 12.3
- **Date:** 2026-11-12

**Decision.** `atlas-server`'s `auth.audiences` value default grows from
`[aurelius]` to the webapp client plus the three scanner client ids (CHT-120),
so a stock server install accepts a scanner's token. The dev `.env` already
lists exactly this set for `nx serve` and the e2e compose; the chart default now
matches the tested reality instead of re-listing it in three places.

**Reason.** The server's `_audience_matches` check rejects a token whose `aud`
is not on the list (AUT-02), so a chart whose default audience set excludes the
scanners ships a deployment where every scanner fails its first write with a
403 the realm cannot explain. The audiences are not secrets and the operator
override stays one value deep, so the safe default costs nothing. This is the
prod-side join 12.2's AGENTS.md assigned to 12.3 ("the prod-side join lands
with 12.3's chart work").

**Alternatives.** Leave the default at `[aurelius]` and document the join in
the scanner READMEs: three scanner deployments then carry three copy-paste
values, and each one that forgets boots a scanner that cannot write. Put the
scanner ids in the umbrella instead: the server chart must render this default
standalone too (the umbrella's own test pins it), and DD-508 deliberately keeps
the scanners out of the umbrella.

**Consequences.** Two pinned tests update to the new default
(`test__charts_server.py`, `test__charts_umbrella.py`); both keep the
values-override case. A deployment that installs no scanner still accepts the
three names it does not issue tokens for — harmless for a confidential client
that exists, and an operator who deletes the realm clients should trim the
list, which the README notes.
