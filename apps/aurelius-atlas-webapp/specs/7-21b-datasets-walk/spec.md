# 7.21b Details sections: the datasets walk

- **Status:** proposed
- **Pull request:** —
- **Records:** DD-372, DD-373; amends 7.21a's section table (the
  `m4i_data_entity` row and its stats bar); relies on DET-15..27 (7.21a, the
  section machinery), DD-365..368 (the walk path, the config table, the
  client-side resolve), AEN-04 (`getEntitiesByGuids`, 8.17), ERD-01/02 (the
  bulk read), ERD-06 (relationship attributes of every read), DD-140 (the App
  Search index is not ported), DD-327 (the save re-read)

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

7.21a ships the section machinery and the sections whose set is one hop: the
entity's own relationship attributes seed the store, and one chunked bulk read
resolves the cards (DD-365). Its deferral table hands this slice one section,
the demo's busiest box: the entity page's **Datasets**.

The legacy answered it from one App Search filter — `supertypenames:
['m4i_dataset']` and `deriveddataentityguid: [entityId]` (the legacy source:
`apps/atlas/src/app/search/details/entity/datasets-cards/datasets-cards.component.ts`).
That crossed field is not a relationship end — it is computed offline. The
Flink job keeps one-hop `derived*guid` markings on every document (a dataset
carries `derivedfieldguid`, a field carries `deriveddataattributeguid`, an
attribute carries `deriveddataentityguid` — the legacy source:
`libs/m4i-flink-tasks/m4i_flink_tasks/operations/synchronize_app_search/`),
and a post-install script crosses them into the pair: a dataset joins an
entity's `deriveddatasetguid` (and the entity joins the dataset's
`deriveddataentityguid`) when they share a field that an attribute of the
entity also names (the legacy source:
`backend/m4i-atlas-post-install/scripts/connect_datasets_with_entities.py`).
Read at the entity, that crossing is exactly the walk over three shipped
relationship ends: entity → `attributes` → each attribute's `fields` → each
field's `datasets` (the model's `m4i_data_entity_attribute_assignment`,
`m4i_data_attribute_field_assignment`, `m4i_field_assignment`).

This product has no such field (DD-140) and no offline step to fill one. The
walk recomputes the same set from the entity's own relationship attributes at
read time, over the bulk read that already resolves cards (DD-372).

Delivered here:

- the walk store: a bounded, fixed-path walk over the bulk reads that seeds a
  card section configured by its path, deduped at every round (DET-28, DD-372)
- the shared read graph: a hop's resolved entities answer both the next round's
  seed and, when that hop is also a rendered section, its cards — the entity
  page's Data Attributes section and the walk's first round read the same
  guids once (DET-29, DD-373)
- the entity layout completed: the Datasets section (`#related-datasets`,
  title `search.details.entity.datasetsCards.title`), its stats-bar entry
  (Data Attributes, Child Entities, Datasets, Properties — the legacy order
  with Data Quality still out, DD-369), and its side-navigation link (DET-30)
- the count rule the walk forces: a walk section has no count to show before
  its last round answers, so it shows the loading line then the walk total —
  the seed half of DET-17 does not stretch to walks (DET-28, DD-372)

Explicitly not delivered here, with the increment that will:

| Deferred                                                                                               | Lands with                            | Why                                                                                                                                         |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| The same walk pointed at other ends (a field's entities, a collection's entities, a system's datasets) | Never as walks                        | No legacy page asks for them; DET-16's config takes a new walk row the day one does (DD-372)                                                |
| The dataset page's Data Entities section                                                               | The inverse-edge read (7.21a's table) | Read at the dataset it is the mirrored crossings, seeded from the dataset's own `fields`; it lands with that page's reverse sets, one store |
| Transitive variants ("every dataset under this entity's whole subtree")                                | Never                                 | Unbounded cost, DD-370's refusal; the walk's claim to honesty is its fixed path (DD-372)                                                    |
| Everything else 7.21a deferred                                                                         | The increments 7.21a's table names    | Unchanged (7.8, the lineage chain, 7.9, the trail endpoint)                                                                                 |

## Semantics

Rules DET-28..31, in the DET band 7.21a opened; DET-01..27 stay in force,
and DET-16's config table gains the walk shape its table below names. The rule
ids ride 7.21a's conventions: TS tests name them, the strings ride the bridge
(every key named here is a catalogue key the XLIFF carries in both locales —
checked, no fixture change; `i18n-completeness.spec.ts` stays green untouched),
and the anchors are the legacy ids.

The amended `m4i_data_entity` row of DET-16's table (the other six rows stand):

| Type              | People box | Card sections (legacy order)                                                                                                                                                                                                                                                                                                     | Stats bar (counts, legacy order)                      |
| ----------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `m4i_data_entity` | yes        | Data Attributes · `#related-attributes` · `search.details.entity.attributesCards.title` · `attributes`; Child Entities · `#related-entities` · `search.details.entity.entitiesCards.title` · `childEntity`; Datasets · `#related-datasets` · `search.details.entity.datasetsCards.title` · walk `attributes → fields → datasets` | Data Attributes, Child Entities, Datasets, Properties |

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-28 | A walk section's seed is a bounded walk over forward relationship ends, given to the store as data — for Datasets, the path `attributes → fields → datasets` from DET-16's amended row. Round 1 is the resolved entity's `relationshipAttributes` for the path's first key, keeping DET-17's filter (an `ACTIVE` `relationshipStatus`, a `guid`); round _n+1_ unions, over the entities round _n_ resolved, each one's `relationshipAttributes` for the path's next key, with the same filter. Each round dedupes by guid across the whole walk keeping first sight (a field named by two attributes is read once; a dataset reached by two fields is one card), and orders the union by first reached: round order, then the seed order of the entity that reached it. The path is walked exactly — one round per key, no recursion, no transitive closure (DD-372). The cards and the count are the last round's set, resolved by the DET-18 chunked bulk read. Until that last resolve answers, the section shows one DET-18 loading card and its count line carries `search.services.appSearchResults.loading` ("Loading a page of search results") in place of a number — the walk total is unknown mid-walk (DD-372). A failed round or chunk adds one alert (DET-18's idiom, one per section) and ends the walk with what it reached; an empty last round renders the empty box at count 0, as DET-17's zero case. |
| DET-29 | The screen holds one read graph (DD-373): within one entity read, a guid is requested at most once — its chunks cover every consumer at once: the card bodies of the section that renders it and the walk rounds that pass through it. On the entity page the Data Attributes section and round 1 are the same set, so the walk's first round adds no request beyond the section's own chunks; and a section whose seed keys equal a walk path's first key (the amended row's first section and the walk) resolves its cards from the graph, not from a second read. The graph follows the entity: the editor's save re-read (DD-327) starts a fresh graph and walk, and a guid change drops the old one — an answer for a superseded guid fills nothing, the DET-08 stale-answer guard extended to hops. A guid missing from a chunk's answer (DET-18's case) is not carried into the next round: a deleted intermediate seeds no empty hop.                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| DET-30 | The entity layout renders the Datasets box after Child Entities (the legacy position), under `#related-datasets`, and every part of it is 7.21a's machinery over the DET-28 set: the uniform card body (DET-19), the keyword search and reset line (DET-20), the Relevance/Name sorts (DET-21 — Relevance is the DET-28 walk order), the 9-per-page scroll (DET-22), the bulk chunking (DET-18). The stats bar gains the Datasets stat between Child Entities and Properties (the legacy order, Data Quality still out per DD-369), its count the walk total; the side navigation gains the Datasets link (`search.details.entity.datasets`) in the legacy position — the entry DET-25 dropped returns. The other six layouts render as 7.21a shipped them.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| DET-31 | e2e (authenticated, every browser), extending DET-27's seeded mini-graph with the shared edges (nodes gained, none renamed): the entity's two attributes share one field (round 2's dedupe), and a second field of the first attribute shares a dataset with that shared field (round 3's dedupe), for three datasets in all. Opened at the entity's details URL, the Datasets section counts 3 and holds three cards; the keyword filter narrows them and the reset line restores; no loading line or loading card remains once settled; the stats bar reads Data Attributes, Child Entities, Datasets (3), Properties in that order. Opening the shared field shows its Data Attributes section counting both attributes — the walk's middle hop seen from the other side. A `DataSet` entity and the no-entity deep link keep their 7.21a/DET-14 shapes. The seed rides DET-27's namespaced m4i seed and self-cleans by the same purge helper (DD-223: no shared-service restarts).                                                                                                                                                                                                                                                                                                                                                                                                                                    |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`):

- `apps/atlas/src/app/search/details/entity/datasets-cards/datasets-cards.component.ts`
  — the box DET-30 ports: its App Search query (`supertypenames:
['m4i_dataset']`, `deriveddataentityguid: [entityId]`, the 9-size page, the
  name/DQ sort options — the DQ sorts stay out with their data, DD-369) and the
  facets dropdown (stays out, DD-370)
- `backend/m4i-atlas-post-install/scripts/connect_datasets_with_entities.py`
  — where `deriveddataentityguid` came from: the offline crossing of the
  Flink one-hop markings over the same three ends DET-28 walks; a one-shot
  backfill, not incrementally maintained (DD-372's staleness record)
- `libs/m4i-flink-tasks/m4i_flink_tasks/operations/synchronize_app_search/event_handlers/relationship_audit/relationship_audit.py`
  and `m4i_flink_tasks/model/app_search_document.py` — the one-hop markings
  the crossing consumes (`update_relationship_attributes` rebuilds a document's
  `derived*guid` fields from its current `relationshipAttributes`)
- `apps/atlas/src/app/search/details/entity/entity-details.component.{ts,html}`
  — the `datasetCount$` stat (the length of the document's `deriveddataset`),
  the `#related-datasets` box order, and the navigation entry (DET-30's
  positions)
- `apps/atlas/src/app/services/app-search-results/app-search-results.service.ts`
  — the legacy's paged answers; `search.services.appSearchResults.loading`
  ("Loading a page of search results") is its string, kept for DET-28's
  in-between state
- the 7.21a origin list (`details-cards-list`, `details.component`, the card
  and people parts) — unchanged, this slice adds no new chrome

## Deviations

None against Apache Atlas: no server surface is added or changed; the walk
rides the contracted ERD-01/02 and ERD-06 reads, whose parity scenarios stay
the gate. Against the Aurelius product: the set is computed at read time by a
bounded client walk instead of read from the crossed index field (DD-372) —
which also fixes the legacy's staleness (its crossing ran only at install
time) and costs the section its up-front count (DET-28's loading line). The
walk's narrower search/sort fields and the hidden DQ parts stay 7.21a's
recorded deviations (DD-368, DD-369).

## Acceptance

- Vitest (unit):
    - `src/app/search/details/sections/datasets-walk.spec.ts` — the store:
      rounds in path order, DET-17's filter at every hop, the dedupe by guid
      keeping first sight and the first-reached order, the fixed path (a
      client spy proves one round per key — entries beyond the path are never
      read), the loading card and line until the last resolve, the one alert
      ending the walk, the missing-intermediate drop (DET-28).
    - `src/app/search/details/sections/read-graph.spec.ts` — one request per
      guid per entity read (the shared attributes case, DET-29), the
      save-tick fresh graph, the guid-change drop (a superseded answer fills
      nothing), no graph reuse across guids (DET-29).
    - `src/app/search/details/details.component.spec.ts` — amended: the m4i
      entity renders the Datasets box after Child Entities (DET-30), the
      stats bar reads Data Attributes / Child Entities / Datasets / Properties
      in legacy order with the walk count, the navigation gains the Datasets
      link; the other six layouts' specs keep passing unchanged.
    - `section-config.spec.ts` — amended: the entity row's third entry is the
      walk, key for key, and the store takes the path as data (a second walk
      path in a test config runs it — DET-16's table and the config stay one
      object).
    - `i18n-completeness.spec.ts` unchanged (both keys the slice uses carry
      both locales already; no catalogue key is added).
- e2e (`nx e2e aurelius-atlas-webapp`): the DET-31 scenario in the
  chromium/firefox/webkit matrix; DET-27's scenario keeps its assertions —
  the graph gains edges, not renames.
- Storybook: no new dumb component enters, so no new story (7.21a's
  `DetailsCardSection`/`PeopleBox` stories cover the chrome; UIC-15's rule is
  untouched).
- Purity gate green (WBP-02: signals, standalone, no state-owning
  `BehaviorSubject`), umbrella checks for the app (`nx test
aurelius-atlas-webapp -c ci`, `nx lint`, `nx build`), `uv run
aurelius-atlas-trace check` reports the DET-28..31 gaps as expected
  (local-only by ADR 056/DD-215).

### Definition of done, in order

1. `nx test aurelius-atlas-webapp -c ci` and `nx build aurelius-atlas-webapp`
   green, `nx lint aurelius-atlas-webapp` and
   `nx run aurelius-atlas-webapp:check-purity` clean.
2. `nx e2e aurelius-atlas-webapp` — the DET-31 scenario green in the
   chromium/firefox/webkit matrix, DET-27/DET-14 unchanged. (Rides 7.21a being
   merged: this slice extends its store, config, and seeded e2e graph.)
3. Spec status → `done`, roadmap row flipped, DD-372/DD-373 accepted with a
   person's approval (never self-accepted).
