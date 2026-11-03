# 7.7a Implementation plan

The plan for the increment in [`spec.md`](./spec.md). One PR. It touches only
`apps/aurelius-atlas-webapp` (a new `src/app/search/editor/` folder, two drawer
routes, the details pencil and hero `+`, one config key, the specs) plus the
e2e suite and its `.env`, and the two ledger rows. No server, no data-access,
no ui-library change: the client methods (`getEntityByGuid`,
`createOrUpdateEntity`, `updateClassifications`, `getTypedefs`) and the drawer,
Select, chips and hero components already ship. No dictionary key is added —
EDT-11's survey found every string in both catalogues.

The branch stacks on `feat/7-20-details-data-spine`: the editor's save calls
`updateClassifications`, the method 7.20's branch added to the client.

Level of verification while iterating (root `AGENTS.md`): the "Gate" section's
Level-0 steps are offline (`test -c ci`, `lint`, purity, `build`); its Level-2
steps (`nx e2e`, the helm render tests) need Docker plus the SOPS key.

## Ledger (same PR)

1. Replace the `| 7.7 | Entity editor | ... | planned |` row in
   `docs/architecture/conversion/index.md` with two rows, the 7.4a/7.4b
   precedent: `7.7a | Entity editor drawer (edit + create core) | ... EDT-01..12
... | Aurelius apps/atlas/src/app/search/{create,edit}-entity | in progress`
   and `7.7b | Entity editor: relationship pickers | ... | Aurelius
search/components/editor/components/relationships-input | planned`. Run
   `npx prettier --write` on the file after (it re-pads the table).
2. Add the spec-map row `| 7.7a | Entity editor drawer |
apps/aurelius-atlas-webapp | EDT |` to
   `docs/architecture/conversion/spec-map.md`.
3. No `deviations.md` or `java-map.md` row: the five intended differences are
   Aurelius-product (DD-322..DD-326 beside the spec), and the webapp port is
   traced to the Aurelius app, not to Java.
4. Flip the spec's and the roadmap row's status to `done` in the closing docs
   commit (the 7.20 pattern); DD-322..DD-326 stay `Proposed` until a person
   accepts them.

## The config key (`atlasClientId`, EDT-09, DD-324)

1. Edit `src/app/config.ts`: add `readonly atlasClientId?: string` to
   `AppConfig`; in `parseAppConfig` treat it like `otelMetricsExporterUrl`
   (optional, non-empty string when present) and default it to
   `"aurelius-atlas-server"` in the returned object.
2. Edit `src/app/config.spec.ts`: absent → the default; present → the value;
   empty string → rejected.
3. Edit `dev/config.json`: add `"atlasClientId": "aurelius-atlas-server"`.
   No `.env` key (the file is bundled in the dev build only).
4. Edit the chart: `apps/aurelius-atlas-webapp/helm/values.yaml` gains
   `atlasClientId: aurelius-atlas-server` in the `config:` block, and
   `templates/configmap-config.yaml` adds `"atlasClientId" $cfg.atlasClientId`
   to the `$configJson` dict (the template's comment already cites
   `src/app/config.ts` as the pairing). Extend the render test in
   `tests/test__charts_webapp.py`: the rendered `config.json` carries
   `atlasClientId == "aurelius-atlas-server"`.
5. Edit `apps/aurelius-atlas-webapp/AGENTS.md` (the `dev/config.json` bullet):
   one sentence — `atlasClientId` names the Keycloak client whose roles gate
   the write affordances; it pairs with the server's `auth_client_id` and the
   realm's client roles (DD-300, DD-324).

## The write gate (EDT-09)

1. Create `src/app/search/editor/can-write-entities.ts`: export
   `canWriteEntities(): Signal<boolean>` — a small injection helper
   (`inject(Keycloak)`, `inject(APP_CONFIG)`) that reads
   `keycloak.hasResourceRole("atlas-write", config.atlasClientId)` once, when
   first injected (the guard has resolved by then, EDT-09's "roles at page
   load"), and returns `asReadonly()`. No service, no state-owning signal
   beyond the one.
2. Create `can-write-entities.spec.ts` (EDT-09): a fake `Keycloak` whose
   `hasResourceRole` answers by role/client, plus an `APP_CONFIG` value —
   grants when `atlas-write` answers for the configured client; denies when it
   answers for none, and when the client entry is absent.

## The pure form fields (EDT-03, DD-323)

1. Create `src/app/search/editor/form-fields.ts`:
    - `EditorFieldKind = "text" | "textarea" | "number" | "boolean" | "date" |
"enum" | "multi"`; `EditorField = { name, kind, label, required,
disabled, enumValues?: string[] }`.
    - `buildFields(entityDef, defsByName, enumsByName): EditorField[]`: walk
      the def and its `superTypes` transitively (shipped defs carry only their
      own attributeDefs — `DataSet` carries none, live-probed), first-wins
      dedupe by attribute name; drop `qualifiedName` and every name already
      read from the entity header (`guid` is not an attribute); skip
      relationship attributes (the defs' `relationshipAttributeDefs` are never
      walked). Kind map: `string` → text, `int|long|float|double` → number,
      `boolean` → checkbox, `date` → datetime, a name present in `enumsByName`
      → enum (values = `elementDefs` sorted by ordinal), `cardinality
LIST|SET` of a string → multi; every other type (struct, map,
      struct-array) is skipped. `definition`/`description` → textarea
      (EDT-03's description keys); `isUnique && name !== "name"` → same kind,
      `disabled: true`; `required` = `!isOptional` (and true for `name`).
      Order: `name`, the description key when present, the rest by name.
      Label: the catalogue string when one exists
      (`search.components.editor.attribute.name`, `.definition`), else
      `displayName`, else the attribute name.
    - `toFormValues(entity, fields)`: attribute values → form values (dates as
      `datetime-local` strings from epoch ms, multi as string arrays).
    - `mergeOntoEntity(entity, fields, values): AtlasEntity` — clone; write
      each field's value back (dates parsed to epoch ms, numbers to `number`,
      empty singles dropped); `relationshipAttributes` and every unwritten key
      pass through (EDT-06).
2. Create `form-fields.spec.ts`: the supertype walk and dedupe, the drop list
   (`qualifiedName`, struct/map kinds), the kind map per typeName, enum values
   by ordinal, unique-disabled, the name/description-first order, label
   fallback chain, `mergeOntoEntity` pass-through of relationship attributes
   and untouched attributes (EDT-03/EDT-06).

## The editor store (EDT-02, EDT-05, EDT-06, DD-325, DD-326)

1. Create `src/app/search/editor/editor-state.ts`: an `@Injectable()` signal
   store the route component provides (the `DetailsState` pattern).
    - `inject(AtlasEntitiesService)`, `inject(TypeDefsService)`,
      `inject(AlertsService)`, `inject(Router)`.
    - signals: `entity`, `typedefs`, `loading`, `saving`, `mode`
      (`"edit" | "create"`), `selectedTypeName`, `chosen`
      (`AtlasClassification[]`), `saveAttempted`.
    - `loadTypeDefs()`: one `getTypedefs({})` (EDT-04's single call); the
      picker, the field resolver, and the classification box all read it.
    - `loadEntity(guid)`: `getEntityByGuid(guid)` (EDT-02); `next` sets the
      entity and seeds the type and `chosen` from `classifications` whose
      `entityGuid` equals the entity's (DD-326: the box shows only own tags);
      `error` (a 404 among them) pushes
      `alerts.add({severity:"error", source:"search", message:
$localize\`:@@search.services.entityDetails.retrieve:...\`})`and leaves
the form empty (EDT-02 — the drawer stays open);`finalize`clears`loading`.
    - `pickerTypes()` computed: `typedefs.entityDefs` minus `AtlasGlossary*`
      and `__*`, labelled by `options.displayName` else name, sorted (EDT-04).
    - `applicableClassifications()` computed: classificationDefs whose
      `entityTypes` intersect the chosen type's name-or-supertypes, minus the
      chosen names (EDT-05).
    - `save(form)`: EDT-06/07/08. When `form.invalid`, set `saveAttempted`
      and return (EDT-07, no request). Build the entity: edit mode merges
      onto the fetched clone; create mode builds `{typeName, guid:
String(-Math.floor(Math.random() * 1e15))}` with a uuid `qualifiedName`
      (DD-325 — the live probe: a uuid `guid` is refused as a reference, a
      negative numeric one is the create idiom the e2e seed already sends).
      Then `createOrUpdateEntity({entity})`; on the answer take the real guid
      (`guidAssignments[<temp>]` for create, the route guid otherwise) and
      apply the classification diff (DD-326, corrected mid-increment: the
      replace `PUT` cannot attach or detach, so the gained tags ride one
      `addClassifications` POST and the lost ones one DELETE each; a kept tag
      sends nothing). On every answer: the `EntitySaved` tick (DD-327) and
      the root compound navigation `router.navigate([{ outlets: { primary:
["search", "details", realGuid], drawer: null } }])` (DD-328 — a string path
      with a trailing `{outlets}` clears nothing: the outlet instruction
      applies inside the walked primary child, not the root where the drawer
      lives). On any `error`: one
      `alerts.add({severity:"error", source:"search", ...})`, `saving`
      cleared, nothing navigated (EDT-08).
2. No spec for the store by itself — the component spec drives every path
   through it (the 7.20 store-spec precedent is fine to follow instead if the
   pipeline gets hard to reach through the DOM; prefer fewer suites).

## The editor drawer (EDT-01, EDT-04, EDT-10)

1. Create `src/app/search/editor/entity-editor.component.{ts,html,scss}`:
   standalone, `imports: [Drawer, ReactiveFormsModule, Select, CommonModule]`,
   `providers: [EditorState]`, OnPush.
    - `readonly active = signal(true)`; `close()` = `active.set(false)` +
      `router.navigate([{ outlets: { drawer: null } }])` — the AlertsPanel
      shape (DD-166). Mode from the route: the `create-entity` route sets
      create, `edit-entity/:guid` reads the param and calls `loadEntity` (an
      `untracked` effect, the details pattern).
    - title: `$localize` of `search.editEntity.editEntity` / `search.createEntity.newEntity`
      by mode; the X's `ariaLabel` = `components.modal.close` (both keys in
      both locales).
    - body: create mode before a type is picked shows the ui-lib `Select`
      (`[searchVisible]="false"`, label `search.details.typeSelect.label`,
      options = `pickerTypes()`) — choosing sets `selectedTypeName` and builds
      the form (EDT-04). The form itself: one control per `buildFields()`
      entry, `@switch` on kind (text/number → Bulma `input.input`, textarea →
      `textarea.textarea`, boolean → `input[type=checkbox]`, date →
      `input[type=datetime-local]`, enum → the ui-lib `Select` wired through
      `(valueChange)` (it carries no `ControlValueAccessor`), multi → the
      array of text inputs with an add line). Disabled fields carry
      `[disabled]`. Labels and the `nameRequired` error ride EDT-11's keys
      (markers for template text, `$localize` for input-bound strings,
      BRW-02). The classification box (EDT-05): label, the chosen tags as
      Bulma `tags.has-addons` with a `button.delete` per tag (aria-label
      `search.components.editor.delete`), and an input + `datalist` over
      `applicableClassifications()` — Enter on a matching name adds
      `{typeName, entityGuid, propagate: true,
removePropagationsOnEntityDelete: true}` (edit: the entity's guid;
      create: the temp guid, the server re-keys), typing filters the datalist
      natively, no match adds nothing. Placeholder
      `search.components.editor.components.classificationsInput.addPlaceholder`,
      empty note `.noClassificationsAvailable`.
    - footer (EDT-10): the body's last line, one
      `button.button.is-primary.aurelius-editor-save` — label
      `search.components.editor.save`, `aria-busy` and inert while `saving`.
      No Delete (7.9), no Cancel (EDT-01). When `saveAttempted && form.invalid`
      show the notification line
      (`search.components.editor.attribute.notification`, EDT-07) and mark all
      touched (EDT-07). Loading line: `search.services.entityDetails.retrieve`
      while `loading`; busy line `search.services.entityUpdate.save` while
      `saving`.
    - class hooks for e2e: `.aurelius-editor`, `.aurelius-editor-save`,
      `.aurelius-editor-classification-input`, `.aurelius-editor-tag`.
2. Edit `src/app/routes.ts`: two more children of the guarded root beside
   `settings` and `alerts` — `{ path: "edit-entity/:guid", outlet: "drawer",
loadComponent: ... }` and `{ path: "create-entity", outlet: "drawer",
loadComponent: ... }`, comments naming EDT-01/DD-322 (the third and fourth
   members of the drawer family).

## The affordances (EDT-01, EDT-09)

1. Edit `src/app/search/details/details.component.{ts,html}`: `canWrite =
canWriteEntities()`; `@if (canWrite())` a
   `button.button.is-small.aurelius-details-edit` (pencil: `fa-icon` `faPen`,
   `FontAwesomeModule` import, aria-label `search.editEntity.editEntity`) in
   the header box, click →
   `router.navigate([{ outlets: { drawer: ["edit-entity", guid()] } }])`.
2. Edit `src/app/search/search-layout.component.{ts,html}`: same helper; a
   `button.button.is-primary.aurelius-create-entity` (`faPlus`, aria-label
   `search.createEntity.newEntity`) in the hero's `after-title` level
   (`level-right`), click → `[{ outlets: { drawer: ["create-entity"] } }]`.
   Update the slot's stale comment (it points at "the role gate 6.2" — that
   is now this gate).
3. Neither route is guarded (EDT-09 — the server refuses; the drawer then
   shows its failure paths).

## Tests

1. Create `src/app/search/editor/entity-editor.component.spec.ts` (the
   `details.component.spec.ts` harness: `provideHttpClient` + testing +
   `provideRouter` spy, fake `ActivatedRoute`, fake `Keycloak` + `APP_CONFIG`
   for the gate):
    - edit: the mount fires `GET .../entity/guid/<route-guid>` and one
      `GET .../types/typedefs`, flush paints name/definition/enabled fields
      per the stub defs (EDT-02, EDT-03); the typedef 404 path adds one alert
      and keeps an empty form (EDT-02).
    - create: the picker lists the non-glossary, non-`__` types sorted,
      choosing builds the form (EDT-04).
    - tag box: add via input+Enter, remove via the delete button, filtered
      list (EDT-05).
    - save: flush the entity, change the definition, click Save — assert the
      `POST .../v2/entity` body carries the merged attributes with
      relationship attributes untouched, flush it, assert `PUT
.../entity/guid/<guid>/classifications` body = the chosen tags, flush
      it, assert `Router.navigate(["/search/details", guid], {outlets:
{drawer: null}})` (EDT-06). Create variant: the body's `guid` is
      negative-numeric, the `qualifiedName` a uuid, the navigation uses the
      `guidAssignments` answer (EDT-06, DD-325).
    - invalid: clear `name`, click Save — no HTTP request, the control error
      and the notification line render (EDT-07).
    - refused: error the POST (403) — exactly one alert entry, drawer stays
      open, edits intact, no navigation (EDT-08).
2. Extend `details.component.spec.ts` and `search-layout.component.spec.ts`
   (or create the layout spec if the affordance tests need the fake): the
   pencil/`+` render only when the fake `Keycloak` grants `atlas-write`; the
   click navigates the drawer outlet (EDT-01, EDT-09).
3. `i18n-completeness.spec.ts` untouched and green (EDT-11 — no new key).

## e2e (EDT-12)

1. Edit `e2e/conftest.py`: add `reader_username` / `reader_password`
   (`AURELIUS_ATLAS_WEBAPP_READER_USERNAME/_PASSWORD`, same
   `Settings`/`SecretStr` shape); a session-scoped
   `_reader_storage_state` (the writer fixture's pattern — sign-in, retry,
   capture) and a `reader_authenticated` page fixture built from it.
2. Edit `apps/aurelius-atlas-webapp/.env` and re-run `nx encrypt
aurelius-atlas-webapp` (CI regenerates plaintext from `.env.enc`) to carry
   the reader pair (the passwords already exist in `dev/keycloak/.env` —
   copy them; the reader holds `atlas-read` only, 6.2a).
3. Edit `e2e/test__aurelius_atlas_webapp.py` — four scenarios, unique
   single-token names, each deleting what it created (guids from the
   responses; no `_purge_type` on the shared `DataSet` type):
    - `test__the_editor_edits_a_seeded_entity`: seed a `DataSet`
      (`_seed_entities`), set its `description` (the DET-14 attribute-PUT
      idiom), open details, click `.aurelius-details-edit`, assert the drawer
      shows the seeded name, edit the definition textarea, Save, assert the
      landed details shows the new text (DET-10 read-back).
    - `test__the_editor_tags_an_entity`: seed a classification typedef
      `e2e_edt_<run>` (`entityTypes: ["DataSet"]`, POST `/types/typedefs`),
      seed an entity, add the tag in the drawer, Save, assert the chip in
      `.aurelius-details-classifications`; cleanup: delete the entity,
      `DELETE /types/typedefs/typedef/name/<tag>`.
    - `test__the_editor_creates_an_entity`: from browse click
      `.aurelius-create-entity`, pick `DataSet` in the Select, enter a name,
      Save, assert the URL's guid and the landed details title; delete the
      entity by guid.
    - `test__the_reader_sees_no_editor_affordances`: with
      `reader_authenticated`, details shows no `.aurelius-details-edit` and
      browse shows no `.aurelius-create-entity`.
    - Never restart a shared `dev/*` service (DD-223).
4. Run focused first: `npx nx e2e aurelius-atlas-webapp --args="-k editor"`.

## Gate

1. `npx prettier --write` every new/edited TS, HTML, and md before staging.
2. Level-0 offline: `nx test aurelius-atlas-webapp -c ci` (247 + new specs),
   `nx lint aurelius-atlas-webapp`,
   `nx run aurelius-atlas-webapp:check-purity`,
   `nx build aurelius-atlas-webapp`,
   `uv run aurelius-atlas-trace check` (report the EDT gaps; local-only per
   ADR 056/DD-215).
3. Level-2: `uv run pytest tests/test__charts_webapp.py` (the new config key),
   `npx nx e2e aurelius-atlas-webapp` (the known
   `edge_span_rides...[chromium]` Tempo flake, if hit, is green in isolation).
4. Live check against the running dev stack (`nx serve` :4300): the writer
   pencil/`+`/save round-trip in the browser.
5. Commit through pre-commit (title
   `feat(webapp): 7.7a the entity editor drawer (EDT-01..12)`), open one PR,
   flip the spec/roadmap statuses.

## Out of scope (do not build here)

- The relationship-attribute pickers (7.7b) — relationship attributes render
  nothing and pass saves through untouched.
- The editor Delete button, the history tab, route guards, the m4i governance
  fields — the spec's deferral table.
- Any server, data-access, ui-library, or dictionary change (EDT-11's survey:
  every string already exists; every client method already ships).
