# 7.21c Details sections: producers, consumers, and the process page

- **Status:** proposed
- **Pull request:** —
- **Records:** DD-382, DD-383; amends 7.21a's section table (the
  `m4i_dataset` row) and adds the eighth row (`m4i_generic_process`); corrects
  7.21a's deferral table (its "Producers, Consumers" row — DD-382); relies on
  DET-15..27 (7.21a, the section machinery), DD-365..368 (the forward-walk
  path, the config table, the client-side resolve), AEN-04
  (`getEntitiesByGuids`, 8.17), ERD-01/02 (the bulk read), ERD-06
  (relationship attributes of every read), DD-140 (the App Search index is not
  ported), DD-327 (the save re-read)

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The dataset page of the demo shows the two boxes that tell the reader where data
comes from and where it goes: **Producers** and **Consumers**. 7.21a deferred
them (with the Data Entities and lineage boxes) as "reverse lookups across
other entities' edges". That reading was wrong for the two process boxes
(DD-382): a dataset carries its own ends `outputFromProcesses` and
`inputToProcesses` (the base model's `process_dataset_outputs` and
`dataset_process_inputs`, both SET on both sides), so the sections seed exactly
like every 7.21a section — from the opened entity's `relationshipAttributes`,
resolved by the chunked bulk read. The demo reads them the same way; its App
Search step only turns the guids it already holds into cards.

The legacy also renders the **process page** (7.21a left it to "a later 7.x
slice"). `m4i_generic_process` is a direct dispatch name in the legacy table,
and its three boxes are its own forward ends: Systems (`system`), Inputs
(`inputs`), Outputs (`outputs`). As 7.21a's config table makes a layout a row
(DD-366), the page is one row: **the eighth layout**.

Delivered here:

- the amended dataset row: the Producers box (`#related-producers`, seed
  `outputFromProcesses`), the Consumers box (`#related-consumers`, seed
  `inputToProcesses`), their stats entries and their side-navigation links, in
  the legacy order (DET-32)
- the eighth layout row: `m4i_generic_process` — no People box, the three
  sections, the stats bar, the side navigation (DET-33)
- the e2e proof on both shapes: the seeded m4i mini-graph gains a process that
  produces and consumes the dataset, and the same process opened from the
  dataset's Producers card is the process page with its three boxes (DET-34)

Every part of the two boxes and the three boxes is the machinery 7.21a ships:
the seed and its count (DET-17), the chunked bulk resolve and the loading rows
(DET-18), the uniform card body (DET-19), the keyword filter and reset line
(DET-20), the sorts (DET-21), the 9-per-page scroll (DET-22), the stats bar
(DET-24), the side navigation (DET-25), the alias badge and icon (DET-26). No
new component enters and no server change is in scope: the server's read fills
both sides of a relationship (ERD-06), which the 7.7c editor scenarios already
pin through the API.

Explicitly not delivered here, with the increment that will:

| Deferred                                                    | Lands with                                         | Why                                                                                                                                   |
| ----------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| The dataset page's Data Entities section                    | The inverse-edge read (7.21a's table, 7.21b's row) | It is 7.21b's crossing read from the other side; unchanged                                                                            |
| The dataset page's lineage-model box                        | [7.22b](../7-22b-lineage-diagram/spec.md)          | It landed with LDG-09..18: the auxiliary chain (8.2 over the 5.1 feed, 7.22a) answers the model                                       |
| The process page's lineage-model box                        | [7.22b](../7-22b-lineage-diagram/spec.md)          | As the row above. LDG-09 seats it after Systems, before Inputs                                                                        |
| The lineage-model stat and nav link (both pages)            | [7.22d](../7-22d-lineage-toolbar-png/spec.md)      | LDG-32 returns them from the box's own state. DD-383's hold-out stays until then: a link to a box not yet rendered strands the reader |
| The governance-quality boxes (both pages)                   | 7.8                                                | Unchanged: the rule-evaluation engine does not exist (DD-369)                                                                         |
| The person layout                                           | A later 7.x slice                                  | Unchanged from 7.21a: out of the user-set set until its boxes have a source                                                           |
| A card list of the processes a person owns (`ProcessOwner`) | With the person layout                             | No legacy page renders it today                                                                                                       |
| Everything else 7.21a deferred                              | The increments 7.21a's table names                 | Unchanged (7.8, 7.9, the trail endpoint, the search work)                                                                             |

## Semantics

Rules DET-32..34, in the DET band 7.21a opened; DET-01..27 stay in force, and
DET-16's config table gains the two rows its table below names — the amended
dataset row and the new process row. The rule ids ride 7.21a's conventions: TS
tests name them, the strings ride the bridge (every key named here is a
catalogue key the XLIFF carries in both locales — checked, no fixture change;
`i18n-completeness.spec.ts` stays green untouched), and the anchors are the
legacy ids.

The two rows (the other six stand as 7.21a shipped them; 7.21b amends the
entity row independently of these):

| Type                  | People box | Card sections (legacy order)                                                                                                                                                                                                                                                                                                                                                                              | Stats bar (counts, legacy order)                         |
| --------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `m4i_dataset`         | no         | Fields · `#related-fields` · `search.details.dataset.fieldsCards.title` · `fields`; Child Datasets · `#related-datasets` · `search.details.dataset.datasetsCards.title` · `childDataset`; Producers · `#related-producers` · `search.details.dataset.producersCards.title` · `outputFromProcesses`; Consumers · `#related-consumers` · `search.details.dataset.consumersCards.title` · `inputToProcesses` | Fields, Child Datasets, Producers, Consumers, Properties |
| `m4i_generic_process` | no         | Systems · `#related-systems` · `search.details.process.systemsCards.title` · `system`; Inputs · `#related-inputs` · `search.details.process.inputCards.title` · `inputs`; Outputs · `#related-outputs` · `search.details.process.outputCards.title` · `outputs`                                                                                                                                           | Systems, Inputs, Outputs, Properties                     |

7.22b amends both rows with the Lineage Model box (LDG-09): the dataset page
renders it between Child Datasets and Producers, the process page between
Systems and Inputs. It is the diagram, not a card section (DD-388), so the
layout row carries its position as `lineageAfter` rather than as a section
entry, and the stats bar and side nav gain no entry until 7.22d returns them
(LDG-32).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-32 | The dataset layout renders two more card sections after Child Datasets, the legacy positions: Producers under `#related-producers` (title `search.details.dataset.producersCards.title`, seed key `outputFromProcesses`) and Consumers under `#related-consumers` (title `search.details.dataset.consumersCards.title`, seed key `inputToProcesses`). Both are ordinary DET-17 seeds — the opened dataset's own ACTIVE ends — resolved by DET-18's chunked bulk read; every other rule of a section applies unchanged (DET-19..22). The stats bar gains the Producers and Consumers counts after Child Datasets and before Properties (the legacy order; the lineage-model and Data Quality stats stay out — Data Quality by DD-369, the lineage model until 7.22d's LDG-32 returns it from the box's state, amended by 7.22b: the box itself renders here since LDG-09, between Child Datasets and Producers), and the side navigation gains the two links (`search.details.dataset.producers`, `search.details.dataset.consumers`) in the legacy positions. The cards are processes: the uniform body (DET-19) renders on them unchanged, and a title click routes the screen to the process (which renders DET-33's layout).                                                                                                        |
| DET-33 | `m4i_generic_process` joins DET-16's table as the eighth layout — a direct dispatch name, and DET-15's supertype walk lands on it the way it lands on the seven. Its legacy page (DD-383) has no People box; its order below the header is Systems · `#related-systems` · `search.details.process.systemsCards.title` · `system`, Inputs · `#related-inputs` · `search.details.process.inputCards.title` · `inputs`, Outputs · `#related-outputs` · `search.details.process.outputCards.title` · `outputs` (the legacy's lineage-model box was deferred with its source; 7.22b draws it — LDG-09 seats it after Systems and before Inputs, and DET-16's table row and this order now include it). The stats bar is Systems, Inputs, Outputs, Properties (the lineage-model stat stays out with its nav link until 7.22d returns both, LDG-32; DD-383's hold-out holds until then), and the side navigation is Description, Systems, Inputs, Outputs, Properties — the legacy list minus the deferred boxes (the DD-369 rule DET-25 applies). Every section is DET-17's seed over the process's own ends, with DET-18..22 unchanged; the inputs and outputs cards are datasets.                                                                                                                                                         |
| DET-34 | e2e (authenticated, every browser), extending DET-27's seeded mini-graph with lineage nodes (none renamed): an `m4i_system`, an `m4i_generic_process` seeded through the process's own ends (`inputs` to the dataset, `outputs` to it, `system` to the system), and a second `m4i_generic_process` left unconnected (the zero case). Opened at the m4i dataset's details URL, the screen shows: the seeded Fields box as DET-27 leaves it, the Producers box counting 1 with the process card, and the Consumers box counting 1 — the dataset's own ends, read through the bulk path (DET-32); the stats bar reads Fields, Child Datasets (0), Producers (1), Consumers (1), Properties in that order. Opening the process's Producers card routes the screen to the process, which renders DET-33's layout: the Systems card, the Inputs box holding the dataset, the Outputs box holding the dataset, and no People box (DET-33). The unconnected process renders its three boxes at zero (DET-33). DET-27's scenario keeps its own guards, the `DataSet` default shape among them (the walk ends at `Process`, and `Process` names no layout of its own — DET-33/DD-383). The seed rides DET-27's namespaced m4i seed and self-cleans by the same purge helper, which gains the two new types (DD-223: no shared-service restarts). |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
`apps/atlas/src/app/search/details/`:

- `details.component.ts` — the dispatch table's `m4i_generic_process:` entry
  (DET-33's direct name) and its `getSuperTypes` fallback (unchanged, DET-15)
- `dataset/dataset-details.component.html` — the `#related-producers` and
  `#related-consumers` boxes, their `nav.level` stats (between the lineage
  model and Data Quality), and the two navigation entries (DET-32's positions)
- `dataset/producers-cards/producers-cards.component.ts` — DET-32's seed: the
  component selects the entity's own `relationshipAttributes.outputFromProcesses`
  and hands those guids to an App Search `guid: [...]` filter with the
  `supertypenames: ['m4i_generic_process']` condition; the title is
  `search.details.dataset.producersCards.title` and the sort options are
  `['name']` (DET-21's pair covers it, DQ out per DD-369)
- `dataset/consumers-cards/consumers-cards.component.ts` — the same for
  `inputToProcesses` and `#related-consumers`
- `process/process-details.component.html` — DET-33's page: the stats bar, the
  box order (Systems, lineage model, Inputs, Outputs, gov quality,
  Properties), and the side-navigation list
- `process/systems-cards/`, `process/inputs-cards/`,
  `process/outputs-cards/` — the three seeds: the process's own `system`,
  `inputs`, `outputs` relationship ends; their titles are
  `search.details.process.systemsCards.title`,
  `search.details.process.inputCards.title`,
  `search.details.process.outputCards.title`
- the 7.21a origin list (`details-cards-list`, the card and people parts) —
  unchanged, this slice adds no new chrome

## Deviations

None against Apache Atlas: no server surface is added or changed; the sections
ride the contracted ERD-01/02 and ERD-06 reads, whose parity scenarios stay
the gate. Against the Aurelius product:

- the legacy's two dataset boxes filtered their App Search answer to
  `supertypenames: ['m4i_generic_process']`; the seed cannot type-filter, so an
  entity attached to these ends of some other type renders a card like any
  other (DD-382; the shipped model names `Process` on both far ends, so the
  filter is a no-op on modelled data)
- the legacy's lineage-model box rendered a diagram (its data path awaits
  increment 5.1 per ADR 055): both pages kept it deferred with the same
  reason, and their stats and navigation listed the rendered box set only
  (DD-383, the DD-369 rule). 7.22b draws the box on both layouts (LDG-09,
  over the 7.22a data path); its stat and nav link stay out until that
  slice's own deferral, 7.22d's LDG-32, returns them from the box's state.
- the legacy card bodies were per type; the uniform body stays (DD-367)
- the legacy's facet dropdown and descendants toggle stay out (DD-370), and
  the section's search/sort fields keep DD-368's narrower net

## Acceptance

- Vitest (unit):
    - `section-config.spec.ts` — amended: the table holds exactly the eight
      layouts (DET-16's count gains the process name); the dataset row lists
      four sections and the process row lists three, anchors and seed keys key
      for key this spec's table (DET-32, DET-33); the People-box flag covers
      the eighth name (false)
    - `layout.state.spec.ts` — amended: `m4i_generic_process` answers its
      layout with no typedef read (DET-33's direct hit); `Process` still walks
      to the default (its typedef read answers the built-in error — DET-15
      unchanged)
    - `details.component.spec.ts` — amended: an `m4i_dataset` entity with
      seeded `outputFromProcesses`/`inputToProcesses` ends renders the two
      boxes with resolved process cards (DET-32), the stats bar reads
      Fields/Child Datasets/Producers/Consumers/Properties with the seed
      counts, and the navigation carries the two links in order; an
      `m4i_generic_process` entity renders the three boxes and no People box,
      with its stats and navigation per DET-33's row
    - `i18n-completeness.spec.ts` unchanged (every key these rows name already
      carries both locales; no catalogue key is added)
- e2e (`nx e2e aurelius-atlas-webapp`): the DET-34 scenario in the
  chromium/firefox/webkit matrix; DET-27's scenario keeps its assertions — the
  graph gains nodes and edges, not renames.
- Storybook: no new dumb component enters, so no new story (7.21a's
  `DetailsCardSection`/`PeopleBox` stories cover the chrome; UIC-15's rule is
  untouched).
- Purity gate green (WBP-02: signals, standalone, no state-owning
  `BehaviorSubject`), umbrella checks for the app (`nx test
aurelius-atlas-webapp -c ci`, `nx lint`, `nx build`), `uv run
aurelius-atlas-trace check` reports the DET-32..34 gaps as expected
  (local-only by ADR 056/DD-215).

### Definition of done, in order

1. `nx test aurelius-atlas-webapp -c ci` and `nx build aurelius-atlas-webapp`
   green, `nx lint aurelius-atlas-webapp` and
   `nx run aurelius-atlas-webapp:check-purity` clean.
2. `nx e2e aurelius-atlas-webapp` — the DET-34 scenario green in the
   chromium/firefox/webkit matrix, DET-27/DET-14 unchanged. (Rides 7.21a being
   merged: this slice extends its config table and seeded e2e graph.)
3. Spec status → `done`, roadmap row flipped, DD-382/DD-383 accepted with a
   person's approval (never self-accepted).
