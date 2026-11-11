# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-455. The score is a first-class Atlas entity, typed in the m4i models

- **Status:** Proposed
- **Increment:** 12.2
- **Date:** 2026-11-10

**Decision.** The scanner writes each score as an `m4i_dq_score` entity. The type
enters the catalogue as a new m4i model file,
`libs/python/aurelius-atlas-core/aurelius_atlas_core/m4i_models/0011-m4i_dq_score_model.json`,
which the boot loader reads after the data dictionary (DD-362). Its attributes
are the fields of the engine's score document (12.1's `result_documents`), plus
`verdict` (`PASS`/`FAIL`/`ERROR`), `errorMessage`, and a unique `scoreKey`.

**Reason.** 12.1's `result_documents` renders plain dictionaries, and 12.1's
spec leaves "writing scores to the store" to this increment (its not-delivered
table). A score has to live where its readers already are. The webapp's score
box (7.25) resolves entities by guid and reads entity attributes; the rules box
(7.24, DET-35) already resolves `m4i_data_quality` entities through the same
bulk-read machinery. A score stored anywhere else — a side index, a separate
keyspace, a field on the rule — is a second read path the server and the
webapp would each have to grow, against ADR 054's retirement of the App Search
`data_quality` index the legacy used for exactly this (DD-369). A typed
entity also makes the score visible to the rest of the product for free: search,
lineage, audits, and export see it like any other entity.

**Alternatives.** Store the score as attributes on the rule entity. It loses
on scale: one rule spans many datasets (DQS-03), and a SET of per-dataset
scores on a rule turns every rule read into a large entity — and the 7.24 box
shows the rule, not the score, so the pair would still need splitting. A new
`dqscore_*` index like the legacy Flink job's: ADR 054 retired that index
surface, and a second store is one more backup and authorization surface.
A JSON blob attribute: no typing, no search, and the webapp would parse the
store's internals (against 8.x's client boundary).

**Consequences.** The m4i models gain one file and one boot-time patch (DD-457).
The boot loader's model count changes, so the type count in any test that
counts types rises by one. The scanner depends on the type existing, which the
model file guarantees in every environment that loads the built-in models
(`m4i_models_enabled`, DV-139): a deployment that turns the m4i models off has
no rules either, so it has nothing to scan.

### DD-456. Latest-per-rule-dataset, updated in place by a unique key

- **Status:** Proposed
- **Increment:** 12.2
- **Date:** 2026-11-10

**Decision.** Each score entity carries a unique `scoreKey`:
`{datasetGuid}/{ruleGuid}`, or `{datasetGuid}/overall` for the summary. The
scanner writes through `create_or_update_bulk` naming no guid, so the store
matches by the unique key and updates the one entity it finds (EWR-06). The
store holds one row per rule per dataset: the newest scan.

**Reason.** Every reader asks the same question: what is this rule's score on
this dataset now. The score box (7.25) resolves a rule's scores for one
dataset, and a card shows one number. A history of runs makes every read a
max-over-runs query the store cannot answer, and a growing pile of stale rows
the catalogue never ages out. Update in place also keeps DQ-08's contract
intact: a run that scores a rule writes its row, and a rule that scores nothing
writes nothing (DD-453), so an old row is never mistaken for a fresh zero.

**Alternatives.** Insert a new entity per run, newest wins. It is real history,
but it needs a retention rule, a newest-per-key read path, and a way to
retire the losers; none of the three is in scope, and inventing the retention
policy silently (keep 30 runs?) is a product decision (DV-style, its own
record later). Reuse the rule guid as the key: one rule spans many datasets
(DQS-03), so the guid alone collides across datasets. A composite qualified
name only: qualified names are unique only within a type and the key must also
be a lookup handle, so `scoreKey` is the unique attribute and `qualifiedName`
follows it.

**Consequences.** A rescan of unchanged data rewrites the same entity and
bumps its audit history — Atlas's own update semantics, and an operator reading
an entity's audits sees the scan cadence for free. History stays open as a
later record; nothing in this design blocks adding rows beside the key row.

### DD-457. Rule binding rides the existing association ends; the vocabulary rides a patch

- **Status:** Proposed
- **Increment:** 12.2
- **Date:** 2026-11-10

**Decision.** The scanner finds a rule's datasets through ends the m4i model
already has: the rule's `fields` end (the `m4i_data_quality_field_assignment`
association) to each `m4i_field`, and each field's `datasets` end to its
`m4i_dataset` (DQS-03). No new relationship enters. The new vocabulary
attributes a rule needs to be stored (`dqcheckkind`, `dqcolumn`, and the
`dq`-prefixed parameters, DQ-07's names) enter as one `ADD_ATTRIBUTE` typedef
patch on `m4i_data_quality`, in
`libs/python/aurelius-atlas-core/aurelius_atlas_core/m4i_models/patches/`.

**Reason.** The binding already exists in the shipped catalogue and the UI
already reads it: the 7.24 rules box seeds from the field's own
`dataQuality` end (DET-35, DD-444), and the 7.21 walk goes dataset → fields
(DT-28..31). Walking rule → fields → datasets is the same edges in the other
direction, so a scanner rule set and a shown rule set are the same set by
construction. A parallel binding — a `datasets` end added to the rule, or a
dataset attribute on the rule — would be a second truth that drifts the first
time a rule is edited. The vocabulary attributes cannot ride the existing
model file, because a model file only creates types; the loader applies
patches after files (MDL-01), so `ADD_ATTRIBUTE` is the shipped mechanism for
"this type gains attributes", already used for 25 attributes of the Cloud
models.

**Alternatives.** Bind rules to datasets directly with a new relationship: it
loses the second truth argument, and it costs a new relationship def, its
inverse attribute, and a legacy-migration patch of every stored rule. Read
only the field end and require rules to name their dataset in a parameter:
that inverts the model (a rule's params name columns, not entities, DQ-01) and
makes the column-name binding the scanner's invention rather than the
catalogue's fact.

**Consequences.** One patch file and one model file land in `aurelius-atlas-core`
beside the scanner. A stored legacy rule with only the pair (no `dqcheckkind`)
keeps working through `rule_from_atlas_attributes`' legacy map (DQ-07), so no
re-authoring pass is needed: only rules the map cannot read go ERROR (DD-454).
The patch's attributes are optional, so every stored rule stays valid.

### DD-458. The scanner is its own Keycloak service client

- **Status:** Proposed
- **Increment:** 12.2
- **Date:** 2026-11-10

**Decision.** The job authenticates with client credentials of a new
confidential service-account client, `aurelius-atlas-quality-scanner`, in the
dev realm import (`dev/keycloak/import/master.json`) and in the production
realm when its chart lands (12.3). Its secret resolves from
`QUALITY_SCANNER_CLIENT_SECRET`, the placeholder pattern the realm import
already uses for every other per-service client. The server accepts the token
by its `azp`: the client id joins the server's `auth_audiences` in dev `.env`.

**Reason.** The audit trail is the reason the catalogue traffic goes through
the REST client at all (DQS-10), and an audit event is only as good as the
principal in it. A job that signs in as a human dev user (the
`import_sample.py` password-grant pattern) writes Atlas audits attributed to a
person who did not run them, and it needs that person's password at job time.
A token minted as the server's own client id is worse: it claims to be the
server reading itself. The 10.9 per-producer-credentials decision already set
the pattern for background identities — one confidential service-account
client per service, one secret per service — and every ingest identity in the
dev realm follows it. Reusing another service's client (for instance an
`otel-*` ingest client) fails on its own terms too: those tokens carry the
collector's audience and the catalogue refuses them (AUT-02).

**Alternatives.** Reuse the `aurelius-atlas-server` confidential client: its
audience is already accepted, but `serviceAccountsEnabled` is false on it, and
enabling it would let any holder of the server's secret mint Atlas-admin
tokens, which is a wider door than the scanner needs. The password grant of a
dev user, as the sample importer does: it puts a human credential in a
customer's scheduler and a human name in every audit row. Mutual TLS
(`client.authenticatorType=x509`): real for some customer estates, and the
realm, the compose files, and the dev CA wiring it needs is a deployment
decision for the chart's increment (12.3), not the app's.

**Consequences.** Three files outside the app change: the dev realm import
(one client block with `serviceAccountsEnabled: true` and the `profile`
default scope, plus its service-account user), the dev keycloak compose (the
secret guard alongside the others), and the scanner's and server's `.env`
keys. The prod realm join waits for 12.3 with the rest of the deployment
surface, the same split 10.7 used for the production identity realm.

The service account holds the server client's `atlas-read` and `atlas-write`
roles (AUZ-02). Acceptance of the token's audience only opens the door
(AUT-02); every read and write past it rides the store's authorizer, which
grants privileges from the roles under `aurelius-atlas-server` — a role-less
service account would get scrubbed searches and refused writes. `atlas-types`
and `atlas-admin` stay out of reach: the job changes no types and no admin
surface. The client carries `fullScopeAllowed: true`, the same setting the
server client itself carries: Keycloak emits another client's roles only for
clients inside the token's audience, and the audience mapper keeps other
clients out of a restricted client's audience — a restricted scanner mints a
token that names the grant but carries no roles. The `profile` scope is in the
client's default scopes so the token carries `preferred_username` — without it
the audit rows would name the service account's `sub` UUID, because the
client's explicit scope list replaces the realm's defaults. The write-role gate
stays off in dev (`write_role` unset); when a deployment turns it on, this
client's roles are a values line in the chart — recorded here so the gap is
named, not discovered.

### DD-459. The first reader is a file reader; a source is configured, never guessed

- **Status:** Proposed
- **Increment:** 12.2
- **Date:** 2026-11-10

**Decision.** The reader seam is `read(qualified_name, guid) -> pl.DataFrame`.
The first cut ships one reader: a file reader over the `sources` map from
dataset qualified name to a path, with the format read from the extension
(parquet, CSV, NDJSON, JSON). A dataset with no entry in the map is skipped
with a count (DQS-04). No path is derived from the dataset's attributes, and
no directory is searched.

**Reason.** Every reader is a trust decision, a credential decision, and a
test-infra decision, and those three differ per customer source: a JDBC
extract needs a host, a port, and a password; an object-store extract needs a
bucket role. Guessing an extract location from catalogue attributes
(`qualifiedName` → path) would read any file the catalogue's text mentions —
a name an editor controls becomes a path the scanner opens, which is a path
traversal written into the product. A configured map is also the smallest
thing the e2e can drive: fixtures write a parquet file, the map names it, and
the scan's proof is real reads and real score rows (DD-223's shared-service
rule intact, since no new service is needed). polars reads all four formats
natively, which keeps DD-450's dependency posture: the scanner's frame layer
is polars alone.

**Alternatives.** Derive the path from `qualifiedName`: rejected above for the
name-is-a-path hole. Scan a source directory and match by filename: it guesses
and it silently reads a newly dropped file the operator never named. JDBC now:
the e2e would need a database service and credentials for every CI run of
every change, and the seam gains nothing from having two readers before a real
customer source is picked. One flat `extracts.parquet` with a dataset column:
it is a format choice disguised as a design, and a single wide file cannot
carry two datasets with different schemas.

**Consequences.** The seam is the contract a later source reader implements,
and the map is one settings key: a deployment adds a reader, not a redesign.
The row budget (DQS-05) lives in the file reader, where the read actually
happens; a future streaming reader enforces its own cut. Skipping with a count
means a misconfigured map shows up in the scan's output rather than as a
silent zero score — the DD-369 posture again, at the configuration layer.

### DD-460. The batch boundary is one scan; incremental scans wait for a need

- **Status:** Proposed
- **Increment:** 12.2
- **Date:** 2026-11-10

**Decision.** A scan re-reads every configured extract and re-scores every
ACTIVE rule over it (DQS-01..06). Nothing is remembered between runs except
the scores themselves; the scanner keeps no cursor, watermark, or state file.
The row budget bounds the cost.

**Reason.** Every alternative needs something this increment has no use for.
An incremental scan over growing extracts needs a per-dataset watermark and a
definition of "new rows" — for a parquet file the honest answer is "the file
changed", which is the whole re-scan anyway. An event-driven scan on entity
change needs the entity's change feed, which is 5.x/6.x's task machinery, and
data extracts change without the catalogue noticing (the catalogue holds
metadata, not rows). A watermark in the store (a `lastScannedAt` attribute on
the dataset) is the same state a score row's `runAtMs` already carries per
rule. Bounded re-scan is what the CronJob (12.3) runs, what the e2e proves,
and what the 1,500-line increment carries. The budget is here because the
first real extract can be large; the watermark can wait for the first
extract that is too large.

**Alternatives.** Watermark by file mtime: it works only for files, so it is
the next increment's per-reader decision anyway. Scan on catalogue change
events: metadata changes do not imply data changed, and data changes do not
touch the catalogue — the two clocks differ, and the pair would scan on the
wrong one. A streaming scan (Kafka): the legacy's shape (Flink over Kafka),
retired with the rule-expression engine (DV-146); the product's contract is a
score that is current as of the last scheduled run.

**Consequences.** A scan's cost is O(Σ extract rows), which the budget caps.
When a customer's extracts outgrow one run, the seam for a fix is per-dataset
concurrency (independent scans, DQS-03's dataset loop is already independent)
and then a per-reader cursor — both changes that leave the scan's contract
(DQS-01..08) unchanged. The e2e therefore proves the batch shape once, on
small fixtures, rather than proving a watermark that does not exist yet.

### DD-461. A stored rule keeps only its own kind's parameters; the store stamps the rest

- **Status:** Proposed
- **Increment:** 12.2
- **Date:** 2026-11-10

**Decision.** When the rule door (`catalogue.rule_attributes`) reads a stored
rule whose `dqcheckkind` names a kind the vocabulary knows, it hands the
bridge only that kind's `dq`-prefixed parameter attributes (DD-457's patch):
the attributes of the other kinds are dropped, whatever their stored value.
A rule with no kind, or one the vocabulary does not know, keeps every
attribute — reading it stays the bridge's error, and the ERROR names the
cause (DD-454). The same fact holds on the score side and the e2e reads it
as such: a stored score's absent primitives read back as the type's defaults
(`score` 0.0, not absent), so the e2e asserts the ERROR entity by its
verdict and cause, and the written entity's "no score" (DQS-08) is the unit
pair's assertion on the fake's record.

**Reason.** The write normalises as Java does (EWR-09): an entity that gives
any attribute gets every primitive of its type mapped, an absent one
materialised to its type's default. So every stored rule carries `dqmin`
0.0, `dqmax` 0.0, `dqmaxAgeHours` 0.0 and `dqminColumns` 0 beside its real
parameters, and the bridge — which validates parameters against the kind and
answers an unknown one with `QualityRuleError` — reads every ACTIVE not-null
rule as ERROR ("has no parameters ['max', …]"), exactly the case the e2e
caught and the fake could not: the fake only answers what a test scripts.
A stored value cannot tell a stamped default from a given zero, so the door
cannot compare values; what it can know is that a kind carries only its own
parameters (DQ-02), so a foreign one is the stamp.

**Alternatives.** Read only the attributes the rule "should" have, per kind,
at the bridge (`aurelius-atlas-quality`): the library is Atlas-blind and its
contract (DQ-02) is to reject unknown parameters — weakening it there would
let a typo'd parameter pass silently. Strip the defaults by value (drop a
double at exactly 0.0): it deletes real parameters too — a
`COLUMN_WITHIN_RANGE` rule with `min` 0.0 is a real range, and a stamped 0
and a written 0 are the same JSON. Have the write omit primitives: it is the
server's shipped Java parity (EWR-09), out of this increment, and other
readers (the UI, 7.24) already read the stamped shape.

**Consequences.** The door filters by `KINDS` from the quality library, so a
future kind needs no door change — its parameters ride the spec. A rule the
vocabulary does not know is untouched, so its ERROR still names the unknown
kind rather than a silently narrowed attribute set. The e2e's seeded rule
sets `active: true` itself, because the same normalisation stamps a rule
created without it as inactive — and the scan would skip it (DQS-02), which
is the store's answer, not the scanner's invention.
