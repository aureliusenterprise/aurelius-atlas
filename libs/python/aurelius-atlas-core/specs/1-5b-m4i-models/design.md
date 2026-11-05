# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-362. The m4i types are a second models directory, read from a sample export

- **Status:** Proposed
- **Increment:** 1.5b
- **Date:** 2026-11-05

**Decision.** The m4i data dictionary types ship as an Atlas model file in their own directory,
`aurelius_atlas_core/m4i_models/`. The server loads it after `models_dir`, with the same model loader, when
`m4i_models_enabled` is on. The file was built from the definitions in `sample_data.zip`, without what storing
them added. A test holds it to the sample exports.

**Reason.** The model loader already does what ADR 058 asks: it creates missing types and newer versions,
takes patches, is safe when replicas start together and audits the start's changes in one write. A directory
of its own keeps Atlas's models byte for byte as DD-032 has them. The sample exports carry exactly these
definitions as JSON, the library's own text: `small.zip` and `sample_data.zip` match `m4i_atlas_core` at
`54d9e04`, and only `businessOwner`'s description differs in the older `only_gov_quality.zip`. Reading them
needs no run of the library.

**Alternatives.**

- The file in Atlas's `models` directory: breaks DD-032's vendored copy.
- A job after start-up that posts the types over REST, as `m4i_atlas_core`'s script does: credentials, a
  running server, and the loader's guarantees again.
- Generating the file from the library's Python: the same definitions, at the cost of running a dependency
  outside the repository.

**Consequences.** A change to the m4i types is an edit of the model file with a greater `typeVersion`, or a patch
file in `m4i_models/patches/`, as for Atlas's models. The test against the sample exports then fails for a type
whose definition changed, which is the point to decide whether the samples change too.
