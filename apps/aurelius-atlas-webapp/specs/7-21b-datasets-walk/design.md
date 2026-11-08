# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-372. The datasets set is a read-time bounded walk, not an index field

- **Status:** Proposed
- **Increment:** 7.21b
- **Date:** 2026-11-06

**Decision.** The entity page's Datasets section is seeded by a walk the store
takes as data — the path `attributes → fields → datasets` — over the entity's
own `relationshipAttributes` and the bulk reads they resolve into (DET-28).
One round per path key, DET-17's ACTIVE/guid filter at every hop, deduped by
guid keeping first sight, ordered by first reached. The path is a config value
(DET-16's amended row), not a hard-coded three-step: a future walk row names a
different path and the same store runs it. The section's count and cards are
the last round's resolved set, and until that resolve answers the count line
shows the legacy paged-answers string `search.services.appSearchResults.loading`
instead of a number.

**Reason.** The legacy read the crossed field `deriveddataentityguid` off the
dataset's App Search document (the legacy source:
`apps/atlas/src/app/search/details/entity/datasets-cards/datasets-cards.component.ts`).
That field was never a relationship end: the Flink job maintained one-hop
`derived*guid` markings per document (the legacy source:
`libs/m4i-flink-tasks/m4i_flink_tasks/operations/synchronize_app_search/event_handlers/relationship_audit/relationship_audit.py`),
and a post-install script crossed them — for each field document, for each
attribute in its `deriveddataattributeguid`, for each dataset in its
`deriveddatasetguid`: add the pair (the legacy source:
`backend/m4i-atlas-post-install/scripts/connect_datasets_with_entities.py`).
Read at the entity, that crossing is exactly entity → `attributes` → `fields`
→ `datasets` over three ends the shipped model already defines, so the walk
recomputes the identical set. DD-140 refused the App Search index for this
product and DD-365 chose forward walks plus bulk reads as the section data
path; this is that path's one multi-round case. Recomputing also fixes a
correctness bug the legacy lived with: its crossing ran once at install, so a
relationship created after it never appeared in the section until the next
backfill — the walk always reads current edges.

**Alternatives.** (a) A server-side endpoint that composes the walk (the DD-365
refusal stands: a second contract duplicating two live reads for one screen;
the store is the seam, and a DD can add it later without touching this
slice's components). (b) A search query filtering on relationship ends (stays
refused, DD-368: entity search indexes own attributes only). (c) The
relationship-search port (stays deferred, DD-365: one hop per call, so the
walk would run it three times and still need the bulk join). (d) A walk with
transitive closure — "every dataset anywhere below this entity" (refused:
unbounded read cost, the DD-370 class; the legacy's own field was the two-hop
crossing, not a closure).

**Consequences.** A walk section cannot show its count before its cards
resolve — the seed half of DET-17's count-before-caries applies only to
one-hop seeds — so DET-28 trades that number for a loading line, and the
walk's total order (the Relevance sort) is only final at the same moment. The
read cost is bounded and predictable: the attributes chunks (shared with the
Data Attributes section, DD-373), one fields round, one datasets round; a
demo entity with a dozen attributes and a dozen fields costs a hand-full of
chunked bulk calls. Round failures degrade to "what it reached plus one
alert" rather than an empty section, the DET-18 idiom.

### DD-373. One read graph per entity read serves sections and walk hops alike

- **Status:** Proposed
- **Increment:** 7.21b
- **Date:** 2026-11-06

**Decision.** The details screen resolves guids through one read graph scoped
to the entity read that is current (DET-29). Within it, a guid is requested at
most once; the chunk's answer is handed to every consumer that names the guid —
the card body of the section that renders it, and the walk round that passes
through it. The graph is born with the entity read (DET-08's fetch, DET-17's
re-seed trigger) and dies with it: a save re-read (DD-327) starts a new graph,
and a guid change or a superseded answer drops the old one, extending DET-08's
stale-answer guard from the entity to every hop.

**Reason.** Without the graph, the entity page reads the same attribute guids
twice — once as the Data Attributes section's seed (7.21a) and once as the
walk's round 1 (DET-28) — and the duplication grows with the fan-out: fields
reached by two attributes would be requested once per attribute. The legacy
paid this in search queries per box (each cards component owned its App Search
service); this slice's whole data path is bulk reads, so the dedupe belongs in
one place. Scoping the graph to the entity read keeps it honest with DET-08's
guard: an answer that arrives after the route moved on or the editor saved
fills a graph nobody reads, which is exactly the stale-paint bug DET-08 ports
from the legacy `latestEntityId` guard.

**Alternatives.** (a) Let the walk own its own cache (refused: it fixes only
the walk's duplicates and leaves the section/walk overlap — the exact pair the
entity page hits first). (b) Resolve every guid through one global cache
lifetime of the screen (refused: the editor's save mutates entities in place,
DD-327; a cross-read cache would serve bodies that predate the save — and the
existing DET-08/DD-327 re-read idiom already decides "fresh per read"). (c) A
`Map` per chunk call with no graph (refused: dedupe must span chunks and
consumers, and the missing-guid rule — a dropped intermediate never seeds the
next round — needs the set of what resolved, which is the graph's content).

**Consequences.** The walk store and the section stores take the graph as a
dependency, so 7.21a's per-section resolve (DET-18) routes through it too —
one code path for every guid read on the screen, which is what makes DET-29's
"requested at most once" testable with one client spy. Memory is bounded by
the graph's life: one entity's neighbourhood, chunked as it goes. The graph
adds no staleness the screen did not already accept: every consumer shows the
same answer for the same read, which is the consistency the DET-17 re-seed
rule already gives the sections.
