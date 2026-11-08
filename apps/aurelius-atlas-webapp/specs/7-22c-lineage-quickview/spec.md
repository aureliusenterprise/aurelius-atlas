# 7.22c Lineage diagram: the quickview

- **Status:** proposed
- **Pull request:** —
- **Records:** LDG-19..26; DD-393..396, DD-401..413 (the reader-feedback
  rounds); relies on LDG-01..18 (7.22a/7.22b),
  LM-04 (the answer whose metadata rows the panel shows), DD-128 (the
  dictionary bridge), DD-388..390 (the viewer, its signals, the subset reader),
  DET-20 (the client-side keyword filter's posture, as the reference idiom)

Part of the [7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01
to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

The legacy viewer answers a node click with the model browser: a panel that
slides in from the right with four tabs — **Browse** (the view dropdown),
**Model** (search plus the element and relation tables), **Selection** (the
selected concept's properties, its references, and the views that show it), and
**View** (the drawn view's own info). On the lineage page it is how the reader
sees what the diagram cannot: the concept's data rows — the metadata entries the
lineage-model API returns beside the model (LDG-02), merged into the properties
table the panel renders. 7.22b left the selection as a signal with a stroke;
this slice gives it a panel.

Delivered here:

- the panel: a drawer (the `aurelius-atlas-ui` drawer) with the four tabs over
  the viewer's signals (LDG-19)
- the Selection tab: name, type, description, the properties table merged with
  the concept's metadata row, the referenced/referencing concept tables, the
  referencing-views table, and the id line (LDG-20, LDG-21)
- the model indexes the tables need: concepts by relation, relations by concept,
  views by entity (LDG-22) — computed signals beside the parsed model
- the Browse tab: the view dropdown over the model's organization folder tree,
  and the Model tab: the keyword filter over the model's elements and relations
  with the two tables (LDG-23)
- the View tab: the drawn view's name, description, and properties (LDG-24)
- two-way selection: a row click in the panel selects in the diagram and opens
  the Selection tab; the diagram's selection opens the panel; dismissing the
  panel clears the selection too (LDG-25)
- the Selection tab's search card: the selected element's name opens its own
  details page (LDG-20, DD-405)
- the dictionary: the vendored `modelview2` catalogue keys, so the panel's
  labels ride the bridge like every other ported screen's (LDG-26)

Explicitly not delivered here, with the increment that will:

| Not delivered                                     | Lands with | Why                                                                                       |
| ------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------- |
| The Browse tab's organization folder tree         | —          | Delivered after all: the reader asked for it (DD-395 superseded by DD-406)                |
| The toolbar                                       | 7.22d      | Unchanged from 7.22b's table                                                              |
| The Data governance addon in the Selection tab    | 7.8        | It queries governance quality for the selected guid (DD-369's deferral, unchanged)        |
| Colour legend and palette editing in the View tab | —          | No bucket mapping exists on the details page (7.22b's deferral table, unchanged)          |
| Fuzzy search (mnemonist inverted index, SymSpell) | —          | The webapp's sections already filter client-side on a keyword (DET-20); deviation, DD-396 |

## Semantics

Rules LDG-19..26, continuing the band. The panel's strings are the legacy's
`modelview2.*` dictionary keys, vendored with LDG-26; the table values are
model data, not strings.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LDG-19 | The viewer gains a quickview drawer (the `aurelius-atlas-ui` drawer, `active` two-way) with four tabs in the legacy order: Browse (`modelview2.modelBrowser.modelBrowserBrowse`), Model (`modelview2.modelBrowser.modelBrowserModel`), View (`modelview2.modelBrowser.modelBrowserView`), Selection (`modelview2.modelBrowser.modelBrowserSelection`) — the order the legacy's `keyvalue` pipe yields over its tabs object (DD-410). The Selection tab renders only while a concept is selected and the View tab only while a view is selected (the legacy's tab conditions); the drawer opens on a concept selection or a Browse request, and closes on dismissal. The tab strip spans the drawer's full width and centres its labels (DD-402). The drawer's header reads "Details" (`search.details.components.navigation.details`) and its footer holds a Close button, both the legacy quickview's own chrome (DD-410).                                                                                                                                                                                                                                                                                                                                                       |
| LDG-20 | The Selection tab shows the selected concept (`entitiesById[selection]`, the legacy's lookup): Name (`modelview2.modelBrowser.selection.name`) when it has one, Type as the type icon plus the human-readable type (`modelview2.modelBrowser.selection.type` — `Dataset`, `Process`, `Data Lineage`: the four-entry metamodel table this slice vendors, `lineage_*` rows of `elements`/`relations_by_tag`), Description (`...selection.description`) when it has one, and the concept's id as the grey ID line below the sections. Above the fields, a selected element (not a relation or view) gains the results-screen search card (`aurelius-atlas-ui-entity-card`: name, type badge, no icon) whose title opens that entity's details page (DD-405).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| LDG-21 | The Selection tab's Properties table (`modelview2.modelBrowser.selection.properties`) is the merge `{ ...concept.properties, ...metadataRow.data }` — the concept's `ar3_properties.ar3_property[]` (the `get-properties.ts` reader: name/value pairs, now added to the LDG-11 subset per DD-389) widened by the metadata row whose `id` equals the concept id (LDG-02's list keyed by id, the legacy's `dataByConceptId` merge: the row's `Type name`, `created_by`, `m4i_original_id` are what the lineage reader came for). The two-column table sorts and pages like the sections' tables (5 per page, the legacy's size). Empty merge, no table.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| LDG-22 | The viewer computes three indexes over the parsed model as signals (the legacy's `ModelExplorerService` maps): concepts-by-relation (relation id → its source and target concept ids), relations-by-concept (concept id → the relation ids touching it), and views-by-entity (entity or view-node id → the view ids that contain it). The Selection tab's Referenced concepts table (`...selection.referencedConcepts`) lists the concepts of the selected relation (non-empty only when a relation is selected); Referencing concepts (`...selection.referencingConcepts`) lists the relations touching the selected concept; Referencing views (`...selection.referencingViews`) lists the views containing it in the legacy's own Name / Description table — the view name in a `th scope="row"`, the documentation beside it, the drawn view the selected row, and a row click draws that view (DD-412). Each table is hidden when empty (the legacy's condition).                                                                                                                                                                                                                                                                                                            |
| LDG-23 | The Browse tab holds the view dropdown (label `modelview2.modelBrowser.browse.viewSelect.label`): one row per view of the model (the lineage model carries one), and choosing one sets the drawn view. Below it, the Browse tab renders the model's `ar3_organizations` as a nested folder tree (label `modelview2.modelBrowser.browse.modelTree`): folders hold subfolders and concept leaves, fold and unfold, and a leaf click selects its concept (DD-406). The Model tab (`modelview2.modelBrowser.model.elements` / `.model.relationships` headings) lists the model's elements and relations in two sortable tables over a keyword filter box: an element row is the narrow type-icon cell (the two lineage types have an icon, any other type none, as the legacy's icon component drew) and the name; a relationship row spans both columns with the legacy's three lines — source end (icon + bold name), the italic middle line (the relation's name, else its type's verb — `Flows into` for a data lineage — with the human-readable type in parentheses), and the target end (DD-411) that narrows both as the reader types (the DET-20 posture: client-side, on name and type, case-insensitive). A row click in any of these tables selects the concept (LDG-25). |
| LDG-24 | The View tab shows the selected view's Name (`modelview2.modelBrowser.view.name`), Description (`...view.description`), and Properties table (`...view.properties`, same merge rule as LDG-21 over the view's metadata row). The lineage document's view has a name ("Lineage") and no description or properties, so those sections hide (the legacy's conditions).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| LDG-25 | Selection is one signal read and written by both surfaces (DD-390's seam), and since DD-415 the drawer's open state and the selected concept ride the `drawer` outlet route, so a reload reopens the panel on its tab and concept: a diagram click sets it (LDG-17) and opens the drawer on the Selection tab (the legacy's auto-open); a table row click in the drawer sets it the same way; clearing it (second click, or the drawer's deselect affordances) closes the Selection tab and hides the drawer when no other tab keeps it open (the legacy's close-on-deselect). Dismissing the drawer (scrim, close button, Escape) clears the selection too, so the diagram never keeps a painted box without its panel (DD-403, a deliberate break from the legacy's close). Selecting a view (LDG-23) closes the drawer and re-renders the diagram (the legacy's rule).                                                                                                                                                                                                                                                                                                                                                                                                         |
| LDG-26 | The panel's labels are XLIFF ids under `modelview2.`: the fixture pair `tests/fixtures/modelview2-en-US.json` / `modelview2-nl-NL.json` (the legacy lib's two catalogues, vendored whole), the generator (`tools/generate-legacy-catalogue.mjs`) reads them beside the existing three pairs, and `messages.xlf` / `messages.nl-NL.xlf` regenerate. The two legacy catalogues disagree on one key pair (`browse.viewSelect.nameDisplayName`/`.nameDescription` in en vs `.viewNameDisplayName`/`.viewNameDescription` in nl, same strings); the vendored nl file keeps the en names so the pair is symmetric (DD-401). `i18n-completeness.spec.ts` grows the two fixture imports and stays green on the rest.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
`libs/modelview2/src/lib/model-browser/` and the pieces it reads, cited by path:

- `model-browser.component.{ts,html}` — LDG-19: the four tabs, their order and
  keys, the `condition` visibility, and the auto-open/auto-close subscriptions
  (LDG-25) on `selectedEntity` and `viewId`.
- `selection/selection.component.{ts,html}` — LDG-20/LDG-21/LDG-22: the
  name/type/description fields, the `properties = { ...entity.properties,
...data }` merge over `ModelDataService.dataByConceptId`, the
  referenced/referencing/referencing-views tables and their hide-when-empty
  conditions, and the ID line. The `MODEL_BROWSER_SELECTION_ADDONS` outlet stays
  out (DD-369's 7.8 deferral).
- `model-explorer.service.ts` — LDG-22: the `conceptsByRelationId`,
  `relationsByConceptId`, `viewsByEntityId` (and `entitiesByViewId`) maps built
  over the parsed model.
- `browse/browse.component.{ts,html}` and
  `browse/view-select/view-select.component.{ts,html}` — LDG-23's dropdown: the
  label, no-data message, and choose-a-view rows (the sortable shell's columns:
  name, description), and the organization tree over `ar3_organizations`
  (folders, concept leaves, fold/unfold, leaf-click selection — DD-406; the
  legacy's `MatTree` becomes a plain nested list).
- `model/model.component.{ts,html}` and
  `model-browser-entities-table/**` — LDG-23's tables: the two headings, the
  element and relationship row fields (name, type), and row-click selection. The
  `FuzzySearchInputComponent` becomes the keyword filter (DD-396).
- `view/view.component.{ts,html}` — LDG-24: the name/description/properties
  sections and the referenced/referencing views tables (the lineage model has no
  view references, so they hide). The colour legend and palette parts stay out
  (7.22b's table).
- `parsers/archimate3/get-properties.ts` — LDG-21's element-property reader
  (`ar3_properties.ar3_property[]` → name/value dict), joined back into the
  subset this rule extends (DD-389's consequence).
- `libs/metamodel/src/lib/metamodel.ts` (`elements`/`relations_by_tag`: the
  `lineage_dataset: 'Dataset'`, `lineage_process: 'Process'`,
  `lineage_relation: 'Data Lineage'` rows) — LDG-20's human-readable table,
  vendored at four entries (the three plus the view's `ar3_Diagram`).
- `src/translations/en-US.json` and `nl-NL.json` (the lib's own catalogues) —
  LDG-26's fixture source.
- `libs/components/src/lib/quickview/**` — not ported: the drawer replaces it
  (DD-393, WBP-02).

## Deviations

None against Apache Atlas (the panel reads 8.2's shipped answer; no server
surface changes). Against the Aurelius product:

- the panel is the ui drawer with Bulma tabs, not the legacy quickview component
  (DD-393); the slide-in, scrim, Escape, and close-button dismissal set is the
  drawer's own, already proven in the webapp (alerts feed, editor drawer).
- the Browse tab's tree is a plain nested list with chevrons, not the legacy's
  `MatTree` (DD-406, which supersedes DD-395's drop): the document's folders
  are fixed ("Other", "Relations", "Views"), so the tree is cheap and it is
  where future diagrams and views will hang.
- the Model tab's search is the webapp's keyword filter, not the legacy's fuzzy
  index (DD-396; DD-368's same reasoning for the sections).
- the Selection tab renders without the Data governance addon and without the
  colour legend (7.8 / colour-by deferrals, unchanged from 7.21c and 7.22b).
- the Selection tab's search card has no legacy twin at this spot: the legacy
  deep-linked through `m4i_original_id` in the properties table; the card makes
  the jump visible (DD-405).
- dismissing the drawer deselects the diagram (DD-403): the legacy's close
  left the node marked.
- the drawer has no pin toggle (DD-410): a pinned panel makes no sense for a
  diagram overlay whose dismissal also deselects (DD-403), and the ui drawer
  has no pin state.
- re-clicking the selected row in the Referencing views table does not
  "deselect the view" as the legacy's `deselectView` did (DD-412): the shipped
  chain always draws a view (LDG-12's first-view default), so there is no
  no-view state to return to — the toggle emits nothing there.

## Acceptance

- Vitest (unit, the new `search/details/lineage/` panel components, over the
  vendored 8.2 fixture plus its metadata rows — DD-391's provenance):
    - `selection-panel.component.spec.ts` — the name/type/description fields and
      id line (LDG-20), the property merge with the metadata row and the
      hide-when-empty rule (LDG-21, including a row whose `data` wins over a
      same-named property — the legacy spread order), the three reference tables
      over the LDG-22 indexes: a relation selected shows its two endpoints, a
      concept selected shows its relations and views (LDG-22); the search card
      for an element, none for a relation, and its click routes to the entity's
      details page (DD-405).
    - `model-browser.component.spec.ts` — tab visibility conditions, open on
      selection, close on deselect and view-select, dismissal clearing the
      selection, and the full-width tab strip (LDG-19, LDG-25, DD-402, DD-403).
    - `browse-tab.component.spec.ts` / `model-tab.component.spec.ts` — the
      dropdown lists the model's views and choosing re-renders the viewer
      (LDG-23); the tree folds its folders, marks the selected leaf, and a leaf
      click selects the concept (LDG-23, DD-406); the keyword filter narrows
      both tables as typed and resets on clear (LDG-23, the DET-20 idiom).
    - `view-tab.component.spec.ts` — the view's Name and merged Properties,
      the empty Description hiding (LDG-24).
    - `parse-ar3.spec.ts` — amended: the properties reader (LDG-21) over the
      fixture's element and metadata rows.
    - `i18n-completeness.spec.ts` — green with the regenerated catalogues
      (LDG-26, unchanged spec).
- Playwright (e2e, authenticated, chromium + webkit — the interaction guard the
  repo's rule asks of e2e; no pixel pins): on the seeded lineage (DET-34's
  graph, 7.22b's box): clicking the process node opens the panel on Selection
  showing its name, type "Process", and a Properties table holding the fixture
  chain's own rows (`created_by`, `m4i_original_id` — LDG-21 over the live
  chain) over the element's search card, whose title navigates to the entity's
  details page (DD-405); closing the panel hides it and clears the diagram's
  selection (LDG-25, DD-403); an edge click selects the relation through the
  wide hit path (DD-409); the Browse tab opens from the tab bar, its dropdown
  lists the one "Lineage" view, and its tree shows the folders (LDG-23,
  DD-406).
- Gates: `nx test aurelius-atlas-webapp -c ci`, `nx lint`, the purity script
  (WBP-02), `nx e2e aurelius-atlas-webapp`.
