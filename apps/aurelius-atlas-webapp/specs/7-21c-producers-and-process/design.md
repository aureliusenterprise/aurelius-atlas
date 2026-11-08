# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-382. Producers and Consumers are forward seeds, not reverse lookups

- **Status:** Proposed
- **Increment:** 7.21c
- **Date:** 2026-11-07

**Decision.** The dataset page's Producers and Consumers sections seed from the
opened dataset's own `relationshipAttributes` — the `outputFromProcesses` and
`inputToProcesses` ends — like every other section of DET-16's table (DET-32).
No inverse-edge read, no new endpoint, no new store. 7.21a's deferral table
lists the two boxes as "reverse lookups across other entities' edges" that the
browser cannot answer. That row was a misreading of the legacy source, and this
record replaces it: the legacy components select the dataset's own ends and
hand their guids to App Search only to fetch the cards
(`details/dataset/producers-cards/`, `consumers-cards/` — each subscribes to
`relationshipAttributes.outputFromProcesses` / `.inputToProcesses` and queries
`guid: [<those guids>]`). DD-365's forward path answers them with zero new
machinery.

**Reason.** The Atlas base model makes the lineage pair SET-on-both-sides:
`process_dataset_outputs` joins `Process.outputs` to
`DataSet.outputFromProcesses`, and `dataset_process_inputs` joins
`Process.inputs` to `DataSet.inputToProcesses`
(`libs/python/aurelius-atlas-core/aurelius_atlas_core/models/0000-Area0/0010-base_model.json`).
A relationship is one edge with two ends, so the retriever fills both sides on
every read (ERD-06) — a fact the 7.7c editor scenarios already pin: they seed
an edge and read it back ACTIVE at both ends through the API. The demo import
bundle carries the shape: of its 22 `m4i_dataset` entities, 34 dataset-to-
process edges sit on exactly these two keys. The remaining deferred row of the
dataset page — Data Entities — is a true reverse lookup (the 7.21b crossing
read from the other side), and stays deferred with it. Only the two process
boxes were mislabeled.

**Alternatives.** (a) Keep the deferral and port the relationship-search
endpoint first (refused: DD-365 already refuses that port for the forward
sections, and there is nothing here for it to answer — the seed is local).
(b) Query entity search filtered on the relationship ends (stays refused,
DD-368: search indexes own attributes only). (c) Re-read the whole graph
server-side and hand the screen a composed sections payload (stays refused,
DD-365's alternative (c): a second contract duplicating two live reads).

**Consequences.** The legacy's App Search step also filtered
`supertypenames: ['m4i_generic_process']`, which no seed can repeat client-
side; the shipped model names `Process` on both far ends of both relations, so
on modelled data the filter selects everything the seed can hold (recorded as
a deviation). The dataset's two new counts ride DET-17's count-before-cards
rule, which the deferral had cost the page.

### DD-383. The process page is the eighth config row; its deferred boxes leave the bars

- **Status:** Proposed
- **Increment:** 7.21c
- **Date:** 2026-11-07

**Decision.** `m4i_generic_process` enters DET-16's table as the eighth layout
(DET-33): no People box, three sections (Systems · `system`, Inputs ·
`inputs`, Outputs · `outputs`), stats Systems/Inputs/Outputs/Properties,
navigation Description/Systems/Inputs/Outputs/Properties. The legacy page's
lineage-model box and governance-quality box, and their stats and navigation
entries, stay out — with the same reasons that keep them out of the other
seven (the diagram awaits the ADR 055 chain's data path, 5.1; the quality
rules await 7.8's engine). The bars list the rendered box set only, the rule
DD-369 already enforces on every layout.

**Reason.** The legacy dispatch names all nine pages, and the process page is
pure section machinery: its three boxes seed from the process's own forward
ends — `m4i_system_process_assignment` (SET both sides) and the two lineage
relations DD-382 names — so DD-366's "the eighth type is a row" holds without
touching the renderer. The two boxes it cannot answer today (the lineage
diagram, the quality rules) are the same two every other layout already omits.
7.21a deferred the page "out of the user-set seven"; the deferral's reason was
that its sections "are governance/lineage sets the API cannot answer", which
DD-382's reading of the source disproves for the three boxes it ships with.
Adding the row also gives DET-32's Producers cards somewhere to route to: a
process opened from a dataset answers its own layout, which is how the demo
reads (click a producer, see its inputs and outputs).

**Alternatives.** (a) Keep the process on the default layout until the lineage
diagram slice (refused: the three sections need nothing that slice adds, and
the dataset page's new cards route to a screen that cannot show where the
process's data comes from). (b) Show the lineage-model stat as a static
"Unavailable" (refused: the legacy shows the availability string, but DD-369's
rule — no link to a box that is not rendered — retires the entry, and a stat
that can never change teaches the reader to ignore the bar). (c) A People box
from `processOwner` (refused: the legacy page has no box — the same case as
`m4i_field`'s steward end, DET-23's note).

**Consequences.** `layoutForTypeName` answers a direct hit for the eighth
name; every other type still walks to the default (the DET-15 rules the specs
pin are untouched). The table's unit spec, which pins "exactly the seven",
gains the eighth name — the same test that caught 7.21a's row drift now guards
this one. The lineage-model box, when its slice lands, adds one section plus
its stat and nav entry to this row and to the dataset's, in the legacy
positions.
