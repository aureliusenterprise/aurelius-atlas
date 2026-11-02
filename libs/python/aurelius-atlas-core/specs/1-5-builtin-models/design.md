# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-031. The patch records live in the typedef document

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** The `typedefs` document of DD-028 holds, next to `typesDef`, a list `patches` of
`AtlasPatch` records: one per typedef patch id, with its description, type, action, status and times.
A patch's record is written in the same document write as the type change it makes.

**Reason.** Atlas keeps patch records as graph vertices and commits them after the type change, so a
crash between the two applies a patch twice, which the `typeVersion` check mostly hides. One document
makes the change and its record atomic, and gives both the single version of DD-029: a process that
loses a race reloads the records with the types, and sees the patch as already applied (MDL-15).

**Alternatives.** A second document, or an index of patch records: queryable by `admin/patches`, but two
writes per patch, and a race between processes needs its own conditional write.

**Consequences.** `admin/patches` (2.2) reads the records from the document. The Java patches of 2.2,
which change entities rather than types, may keep their records elsewhere; 2.2 decides.

### DD-032. The built-in models are vendored unchanged and read from a directory

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** `addons/models` of Apache Atlas `release-2.4.0` is copied byte for byte into the package
`aurelius_atlas_core.models`, and kept out of the formatting hooks. The server loads models from
`AURELIUS_ATLAS_SERVER_MODELS_DIR`, which defaults to that package directory.

**Reason.** Atlas reads its models from `$ATLAS_HOME/models`, so operators add their own model files and
patches there;
a directory setting keeps that. Unchanged copies let a reviewer prove them unchanged with a diff against
the tag, as for the dashboards (DD-017), and ship in the wheel without a build step. The line endings are
kept too: one patch file has CRLF, so the directory is `-text` in `.gitattributes`.

**Alternatives.** Converting the models to Python data: no diff against Atlas, and no way to add models
without a release. Reading them from a checkout of Atlas at build time: the build would depend on a
second repository.

**Consequences.** A newer Atlas version's models are a new copy and a check of the new patches against
the nine actions.

### DD-033. Start-up loading is one change per model file and per patch

- **Status:** Proposed
- **Increment:** 1.5
- **Date:** 2026-10-18

**Decision.** Each model file and each patch is one change of the typedef store (DD-029): what to create,
update or patch is decided inside the change, on the definitions and patch records just read, and decided
again when a conditional write loses to another process.

**Reason.** Atlas loads models only on its one active server. Here every process starts the same way,
possibly at the same moment; deciding inside the change makes a second process see the first one's types
and records, so it creates, updates and patches nothing twice. One change per file and per patch keeps
Atlas's isolation: a failing file or patch leaves the others applied (MDL-04, MDL-06).

**Alternatives.** All files and patches in one change: one write, but a failure would need the transient
registry to roll back part of a change. A lock document held while loading: needs expiry when its
holder dies (as in DD-029).

**Consequences.** The first start against an empty store writes the document once per model file and
patch, a few hundred writes of the whole document; later starts write nothing unless a model or patch is
new. Two processes starting together may each retry once per change.
