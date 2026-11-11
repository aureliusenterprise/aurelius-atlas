# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-484. The legacy engines' documents are the reference, copied unchanged, beside their catalogue

- **Status:** Proposed
- **Increment:** 14.1
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** The three engines' documents for the sample catalogue are test fixtures of `aurelius-atlas-core`,
copied byte for byte from the legacy repository's post-install data. `atlas-dev` is the reference for values:
the derived documents of the sample catalogue must equal it, field by field, except for the differences DD-485
lists. `atlas-dev-quality` and `atlas-dev-gov-quality` are the reference for shape: their fields, identities and
links, not their values.

**Reason.** ADR 052 rules out running the legacy system; its own output, for a catalogue the repository already
holds, is the next best witness, and the only one for the post-install scripts, which have no tests. Copied
unchanged, a fixture can be checked against its source by anyone. The result engines were written once per
change and never brought up to date, so their values describe a catalogue that no longer exists.

**Alternatives.**

- Expected documents written by hand from the code: a reading of the code checked against itself.
- A trimmed fixture of a few documents: the roll-up and the derived relations need the whole catalogue to be
  checked.

**Consequences.** The fixtures add 3.3 MB to the repository. A rule of the series that the fixtures cannot show
(a change, a delete) is tested against the code's reading only, as LAS-08 to LAS-10 are.

### DD-485. Where the legacy documents differ from the catalogue, the documents follow the catalogue

- **Status:** Proposed
- **Increment:** 14.1
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** The derived documents are computed from the catalogue as it is. The places where the snapshot
differs from that (the spec's table) are not reproduced: a process carries its qualified name, an entity its
definition and its current name, the first parent is the first in the parents' order, and a relation is listed
at both its ends. Every quality rule is scored and every pair of an entity and a governance rule for its type
is judged, where the legacy covered those it happened to see change. What fills a quality result's `name`,
`businessruleid` and `datadomainname`, which no legacy code in the repository produces, is decided by 14.5.

**Reason.** Each difference is a defect or an accident of the legacy pipeline: a fallback for a type whose model
had no qualified name, events lost or applied out of order, the first element of a set. Reproducing them would
take extra code to make the answers worse, and none of them is something a user of the original webapp relies
on.

**Alternatives.**

- Reproduce the snapshot exactly: impossible for the losses, which depend on the order events arrived in.

**Consequences.** Each increment that derives one of these fields records the difference as a deviation, and its
comparison with the fixture tolerates exactly the listed documents.

### DD-486. The rules are stated over the catalogue's state, not over the events that changed it

- **Status:** Proposed
- **Increment:** 14.1
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** Each rule says what a document holds for a given catalogue, not what a handler does to a document
when an event arrives. A change is the catalogue before and after it, and the documents it affects are those
whose rules give another answer after it (LAS-08 to LAS-10).

**Reason.** The legacy handlers patched documents in place: a delete cut a breadcrumb short, a rename replaced
one name, and the result depended on the order events were applied in. Rules over the state give one answer
whatever the order, can be checked against a snapshot, and let 14.3's tasks recompute an affected document
instead of patching it. For a chain where each entity has one parent, the legacy cut and the recomputation give
the same breadcrumb.

**Alternatives.**

- Port the handlers one for one: their order dependence comes with them, and so do the snapshot's losses.

**Consequences.** 14.3 must find, for a change, every document whose breadcrumb, relations or scores pass
through the changed entity.
