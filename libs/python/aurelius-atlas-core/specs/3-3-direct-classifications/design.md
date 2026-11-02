# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-070. Classification instances are documents of their own index, listed by their entity

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** A classification instance is one document of the index behind `aurelius-atlas-classifications`,
keyed by a GUID of its own: type name, the GUID and status of the entity it is attached to, `propagate`,
`removePropagationsOnEntityDelete`, validity periods and attribute values (as DD-049 stores values). The
entity's document lists the GUIDs of its classifications (`classificationGuids`), in the order they were
attached. Reading an entity's classifications is a get of the listed documents, in real time.

**Reason.** Atlas keeps a classification as a vertex the entity reaches by an edge, and a propagated one is
the same vertex reached by many entities. A document per instance keeps that: 3.4 lists a propagated instance
on every entity it reaches, and an update of it changes one document. Listing GUIDs keeps reads to gets by id,
as DD-061 does for relationships.

**Alternatives.** Classifications embedded in the entity document: no second read, but 3.4 would copy a
propagated classification into every entity it reaches and rewrite every copy on each change.

**Consequences.** An entity read with classifications costs one more `mget`. The GUID of an instance is
internal: Atlas's classifications have none in their JSON.

### DD-071. An entity write also writes classification instances, all or nothing

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** `EntityStore.write` also writes, changes and removes classification instances, in the same bulk
request and journal entry as the entities, as DD-062 does for relationships; recovery restores them too.

**Reason.** Attaching a classification changes the entity's list and the instance together; Atlas does both in
one graph transaction.

**Alternatives.** Writing the instance first and the entity after: a failure between leaves an instance no
entity lists.

**Consequences.** The journal entry holds the classifications' states before the write, as it does for
entities and relationships.

### DD-072. The propagation defaults are Atlas's defaults

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** A classification attached without `propagate` gets `true`
(`atlas.classification.propagation.default`), without `removePropagationsOnEntityDelete` gets `false`
(`atlas.classification.propagation.remove.on.entity.delete`); both are Atlas 2.4.0's defaults, fixed in code.

**Reason.** No deployment changes them yet, and both decide 3.4's propagation, which will read the stored
values.

**Alternatives.** Server settings now: two settings with no effect until 3.4.

**Consequences.** 3.4 may turn them into server settings.

### DD-073. 3.3 is split into direct classifications and the bulk associator

- **Status:** Proposed
- **Increment:** 3.3
- **Date:** 2026-10-23

**Decision.** 3.3a ports classifications attached directly: storage, reads, the per-entity and
`bulk/classification` endpoints, classifications of created entities and of deleted ones. 3.3b ports
`bulk/setClassifications` (`ClassificationAssociator`) and `bulk/headers?tagUpdateStartTime`.

**Reason.** Together they are above the size an increment may have (ADR 051); the associator builds on 3.3a's
operations.

**Alternatives.** One increment: one pull request far above the limit.

**Consequences.** Until 3.3b, `bulk/setClassifications` and `bulk/headers` answer `404`.
