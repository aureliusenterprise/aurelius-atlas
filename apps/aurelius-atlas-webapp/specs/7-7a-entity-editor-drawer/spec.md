# 7.7a Entity editor drawer (edit + create core)

- **Status:** done
- **Pull request:** —
- **Records:** DD-322..DD-329; relies on DD-166 (the drawer outlet shape),
  DD-300 (the four roles), ADR 051 (port rules), UIC-24 (the deletable chip)

## Scope

The entity editor: create an entity or edit an existing one, in a drawer
that opens over the screen the user is on. The drawer is the third member of
the routed `drawer` outlet family beside the settings panel and the alerts
drawer (DD-166's shape), by user direction on 2026-11-03.

Delivered here:

- the drawer: a routed component in the `drawer` aux outlet, opened from the
  details screen's pencil (edit) and the search hero's `+` button (create),
  closed by its X, the backdrop, or Escape — the same dismissal set as the
  other drawers
- the fetch: the editor reads the entity itself (`getEntityByGuid`, the same
  client and URL DET-08 rides); it shares no state with the screen underneath
- the form: one generic form driven by the entity's own type definition
  (DD-323): name (required), definition, the other plain attributes as inputs,
  and the classifications tag box
- create mode: a type picker over the shipped entity types, then the same
  form; a temporary guid on the payload and the real guid back from the
  server's `guidAssignments` (DD-325)
- save: `POST /api/atlas/v2/entity` with the merged entity, then the
  classification diff (the tags added through one `POST .../classifications`,
  the tags removed through one `DELETE` each — DD-326; the replace `PUT` can
  only change attached tags, not attach or detach); success navigates to the
  entity's details screen
- the affordance gate: the pencil and the `+` render only for a token that
  holds `atlas-write` on the server's client (DD-324)
- the failure paths: a failed fetch or a refused save adds an alert (7.19's
  failure idiom) and keeps the user's edits

Explicitly not delivered here, with the increment that will:

| Deferred                                                    | Lands with | Why                                                                                                                              |
| ----------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------- |
| The relationship-attribute pickers                          | 7.7b       | The legacy pickers searched the App Search index this product does not have (DD-140); the search contract needs its own decision |
| The delete flow (the editor footer's Delete button)         | 7.9        | The roadmap assigns it there; the footer ships without it (EDT-10)                                                               |
| The editor's history tab (the entity audit list)            | 7.9        | The audit client exists (8.17); the card is that slice's                                                                         |
| The m4i governance fields (owner, steward, domain, quality) | Never      | The types that carry them do not exist in this product (DD-323)                                                                  |
| Route guards on the editor URL                              | —          | The legacy gates the affordances, not the routes (EDT-09); the server's authorizer is the real gate (DD-300)                     |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
(7.6/7.20's pattern — Vitest names the id in the test title;
`@pytest.mark.covers` applies to no file here; the e2e names it in the
docstring).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EDT-01 | The editor is a routed component in the `drawer` aux outlet (DD-166's family with the settings and alerts panels). The details pencil navigates to the outlet's `edit-entity/<guid>` segment; the search hero's `+` navigates to `create-entity`. The drawer renders over the primary screen, which does not change and does not reload. Closing (X, backdrop, Escape) navigates the outlet away. The open state rides the URL.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| EDT-02 | The editor fetches its entity through `AtlasEntitiesService.getEntityByGuid(guid)` — the same client and URL the details screen rides (APC-01). No second entity client. The drawer shows a loading line while the fetch is in flight. A 404 or a failed read adds an alert (7.19's idiom) and the form stays empty; the drawer stays open so the user can close it.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| EDT-03 | The form fields come from the entity's own entity definition, resolved through the one typedefs call (EDT-04): every attribute of the definition plus its supertype chain (shipped defs carry only their own attributes — `DataSet` carries none of its own, so `Asset`'s and `Referenceable`'s must be walked), ordered `name` first, then the description key, then the rest by name. `name` is a required text input. `definition` or `description` (the two keys the details box shows, DET-10/DD-320 — the shipped types carry `description`) is a textarea. Every other attribute whose type is string, numeric, boolean, date, or a loaded enum gets one input by that type (string → text, numeric → number, boolean → a checkbox with Bulma's anatomy (a `label.checkbox` wraps the input and a bare text node, DD-329), date → a datetime input whose payload value is epoch milliseconds, enum → a select over the enum's values). A `LIST`/`SET`-cardinality string attribute renders a repeating text list. Unique attributes other than `name` render disabled — they locate the entity and are not editable here. `qualifiedName` and `guid` never render. Every other kind (struct, map, struct-array) and every relationship attribute renders nothing in this increment (7.7b) and passes a save untouched. A field's label is the catalogue string where one exists (`search.components.editor.attribute.name`, `.definition`, `.classifications`), else the attribute's `displayName`, else its name. |
| EDT-04 | Create mode starts at a type picker: every entity typedef except the three `AtlasGlossary*` types (the glossary screens own those — 7.14) and the `__`-prefixed internals. Labelled by alias else name, sorted. `Process` and `DataSet` stay listed — they are the product's writable types, and the legacy picker's other exclusions (`AtlasEntity`, `AtlasProcess`, `ProcessProcess`) are not typedefs of this store. Choosing a type builds the form from that definition. Editing renders the type as a static label — the type never changes.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| EDT-05 | The classifications tag box lists the classification typedefs whose `entityTypes` include the entity's type (or a supertype of it) and that are not already chosen; typing filters that list. Adding a tag stores `{typeName, entityGuid: <the entity>, propagate: true, removePropagationsOnEntityDelete: true}` (the legacy shape the server expects). Enter commits a typed name. A pick from the open suggestion list commits through the input's `change` event, and the input clears only on a real add (DD-329). A chosen tag renders as the `classification-chip` component (UIC-16, the details screen's atom) with its delete (UIC-24) and the type's description as tooltip. The legacy editor showed the tags that way, like its relationship input. Removing drops the tag. The box labels itself with `search.components.editor.attribute.classifications`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| EDT-06 | Save merges the form onto a clone of the fetched entity (attributes; relationship attributes and everything else pass through unchanged — EDT-03 renders nothing for them, so a save cannot lose them), sends `POST /api/atlas/v2/entity` with the bare `AtlasEntityWithExtInfo`, and on the mutation response applies the classification diff (DD-326): the tags the box gained ride one `POST /api/atlas/v2/entity/guid/{guid}/classifications`, the tags it lost ride one `DELETE /api/atlas/v2/entity/guid/{guid}/classification/{name}` each, and a tag it kept sends nothing. On success the drawer closes and the app navigates to `/search/details/<guid>` — the created entity's guid from `guidAssignments`, the same guid otherwise. A create payload carries a client-made temporary guid (DD-325).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| EDT-07 | A save with an invalid form marks every control touched, renders each error under its control (`search.components.editor.attribute.nameRequired` under the name field), and renders the notification line `search.components.editor.attribute.notification`. No request fires.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| EDT-08 | A refused or failed save (a 4xx/5xx on either call) adds one error alert through the app's alerts store (7.19's failure idiom, the same pattern DET-13 rides). The drawer stays open with the user's edits intact.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| EDT-09 | The pencil (on the details header) and the `+` (on the search hero) render only when the signed-in token holds the `atlas-write` role of the server's client, named by the app configuration's `atlasClientId` key (`resource_access.<atlasClientId>.roles`, AUZ-01's pair). The client stores roles in memory and re-reads the token, so a role change takes effect at the next page load. The editor drawer itself is not route-guarded (the legacy gates the affordances, not the routes; the server refuses the write anyway — DD-300, AUZ-07).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| EDT-10 | The footer holds Save only. No Delete, no Cancel (EDT-01's close is the abandon path; the legacy had no Cancel either — browser-back was the abandon).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| EDT-11 | Every chrome string rides a bridge key the catalogue already carries in both locales: the drawer titles (`search.editEntity.editEntity`, `search.createEntity.newEntity`), the footer (`search.components.editor.save`), the attribute labels and errors (`search.components.editor.attribute.*` — name/nameRequired/definition/classifications/notification), the tag box (`search.components.editor.components.classificationsInput.addPlaceholder` and `.noClassificationsAvailable`), the tag remove (`search.components.editor.delete`), the picker label (`search.details.typeSelect.label`), the busy lines (`search.services.entityDetails.retrieve`, `search.services.entityUpdate.save`), and the drawer's X (`components.modal.close`). No key is added and no fixture changes (SHL-08).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| EDT-12 | e2e (authenticated, every browser): the dev writer holds `atlas-write`. On a seeded entity the pencil opens the drawer with the entity's name filled; changing the definition (the seeded `description`), saving, and landing on details shows the new text (read back through the details screen, DET-10). Adding a classification tag and saving shows the chip on the details header. Create: the `+` opens the picker, a type is chosen, a name entered, saving lands on the new entity's details with the entered name. The dev reader (`aurelius-reader`, no `atlas-write` — its credentials join the webapp's `.env`/`.env.enc` as a second pair, the `AURELIUS_ATLAS_WEBAPP_READER_*` pattern) signs in through its own context and sees neither the pencil nor the `+`. Shared `dev/*` services are never restarted (DD-223); created entities ride the unique-token name idiom and are deleted by guid at the end of each scenario (namespaced self-cleaning), as are the test's own classification typedefs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`),
`apps/atlas/src/app/search/`:

- `create-entity/create-entity.component.ts` — create mode: seeds a
  placeholder entity into the shared store (a negative random guid and a uuid
  `qualifiedName`); EDT-04/EDT-06 port the shape minus the sentinel guid
  (DD-325)
- `edit-entity/` (routing + resolver) — the edit route by `:id`, the resolver
  clearing the shared store before the fetch; EDT-02 ports the fetch into the
  drawer itself (the drawer owns its read)
- `components/editor/editor.component.{ts,html}` — the editor shell: the
  type-pick-then-form flow, the Save footer, the navigate-to-details after
  save; the history tab and the hold-to-confirm Delete stay deferred (7.9)
- `components/editor/services/editor-form.service.ts` — the save pipeline:
  mark touched, bail when invalid, merge the form onto a clone of the store
  entity, hand it to the update service; EDT-06/EDT-07 port the pipeline
- `search/services/entity-update/entity-update.service.ts` — the
  classification diff-sync after the entity POST; DD-326 ports its shape (the
  replace `PUT` cannot attach or detach, so the diff is the only correct
  client of these endpoints)
- `components/editor/type-select/type-select.component.ts` — the create-mode
  type picker (it walks the `m4i_referenceable` inheritance tree); EDT-04
  ports the picker over this product's type set (DD-323)
- `components/editor/components/classifications-input/` — the tag box over
  the applicable classification defs; EDT-05 ports it (its applicability rule
  is standard Atlas `ClassificationDef.entityTypes`)
- `components/editor/{entity,dataset,domain,collection,field,person,process,system,gov-quality,attribute}/`
  — the ten hand-written `m4i_*` forms; DD-323 replaces all of them with the
  one generic form — no shipped type matches their fields
- `search/details/details.component.html` (the pencil) and
  `search/search.component.html` (the hero `+`) — the two affordances
  EDT-09 ports, gated here by `atlas-write` where the legacy used
  `DATA_STEWARD` (DD-324)

## Deviations

None against Apache Atlas: this slice is an Aurelius product screen; Atlas's
own editor is its dashboard (ADR 046, the parity reference stays). The
endpoints it calls are the ported Atlas v2 write REST (2.4), and it uses them
as the legacy client used them.

Against the Aurelius product, five intended differences are recorded beside
this spec. The editor lives in the drawer outlet, not a full-screen route
(DD-322). One generic entityDef-driven form replaces the ten hand-written m4i
forms (DD-323). The affordance gate reads `atlas-write` instead of
`DATA_STEWARD` (DD-324). Create seeds a negative temporary guid and lands on
the server's guid from `guidAssignments` instead of the shared-store sentinel
shape (DD-325). Classifications save through the add/remove diff of the own
tags only — the propagated ones stay out of reach (DD-326). The deferral table
carries the rest.

## Acceptance

- Vitest (unit, `apps/aurelius-atlas-webapp`):
    - `src/app/search/editor/entity-editor.component.spec.ts` — the fetch
      fires for the route guid and paints the form (EDT-02), the field set
      and input kinds come from the entity def (EDT-03), the type picker
      lists and selects (EDT-04), the classification box adds/filters/removes
      (EDT-05), save posts the merged body then applies the classification
      diff and navigates (EDT-06, the create variant through
      `guidAssignments`), an
      invalid save fires nothing and shows the errors and the notification
      (EDT-07), a failed save adds one alert and keeps edits (EDT-08).
    - `src/app/search/editor/can-write-entities.spec.ts` — the gate answers
      from `resource_access.<atlasClientId>.roles` (EDT-09); a token without
      the client entry denies.
    - details/search component specs — the pencil and `+` appear and hide by
      the gate (EDT-09); the header `+` and pencil navigate the outlet (EDT-01).
    - `i18n-completeness.spec.ts` unchanged and green (EDT-11: no key is
      added; every string rides an existing catalogue entry).
- ui library: none new (the drawer, modal anatomy, and inputs it needs exist;
  if the enum/date inputs need a Bulma part, it enters as a UIC rule under
  7.2's contract).
- e2e (`nx e2e aurelius-atlas-webapp`): the EDT-12 scenarios in the
  chromium/firefox/webkit matrix against the shared dev stack, self-cleaning
  through the purge helper (DD-223: no shared-service restarts).
- Storybook: none — the webapp ships no Storybook host and no screen
  carries a story (the rule covers ui-library pieces, and this
  increment adds none).
- `nx test aurelius-atlas-webapp -c ci`, `nx lint aurelius-atlas-webapp`,
  `nx run aurelius-atlas-webapp:check-purity`, `nx build aurelius-atlas-webapp`,
  `uv run aurelius-atlas-trace check` reports the EDT gaps as expected
  (local-only by ADR 056/DD-215).
