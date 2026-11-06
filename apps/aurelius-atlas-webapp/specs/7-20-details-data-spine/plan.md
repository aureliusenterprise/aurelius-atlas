# 7.20 Implementation plan

The plan for the increment in [`spec.md`](./spec.md). One PR. It touches only
`apps/aurelius-atlas-webapp` (the details screen, a feature-folder store, one
pure helper, the specs), the brand stylesheet (DD-319), the ui library (the
`Markdown` component, DD-321 — review round), and the `marked` dependency,
plus the two ledger rows that name the increment. No server and no
data-access change: the client method (DET-03) and every dumb component
(7.13, 7.16) already ship.

Level of verification while iterating (root `AGENTS.md`): the "Gate" section's
Level-0 steps are offline (`test -c ci`, `lint`, purity, `typecheck`); its
Level-2 step (`nx e2e`) needs Docker plus the SOPS key. CI's
`nx affected -t test e2e -c ci` is the gate.

## Ledger (same PR)

1. Housekeeping (done in the plan branch, reviewable): `.gitignore` gains the
   `.scratch/` entry and the webapp `AGENTS.md` records the legacy-clone pin
   (`b057389828c10497dd52d9efd4c16547c282c005`).
2. Add the roadmap row `7.20 | Details data spine | ... DET-08..14 ... |
Aurelius apps/atlas/src/app/search/details | in progress` to
   `docs/architecture/conversion/index.md`, after the 7.19 row. Run
   `npx prettier --write` on the file after (it re-pads the whole table; the
   content is safe).
3. Add the spec-map row `| 7.20 | Details data spine | apps/aurelius-atlas-webapp
| DET |` to `docs/architecture/conversion/spec-map.md`.
4. No `deviations.md` row: the two intended differences are Aurelius-product,

## The screen store (DET-08, DET-13, DD-318)

1. Create `src/app/search/details/details-state.ts`: an `@Injectable()`
   signal store the route component provides (the `SearchState` pattern).
    - `inject(AtlasEntitiesService)`, `inject(AlertsService)`.
    - `readonly entity = signal<AtlasEntity | null>(null)`,
      `readonly loading = signal(false)`.
    - `load(guid: string)`: capture the guid; set `loading` true; subscribe
      `getEntityByGuid(guid)`; in `next` set the entity **only if the guid
      still matches the latest requested** (the legacy `latestEntityId` guard,
      DET-08); in `error` push an `alerts.add({severity:"error", source:
"search", message: $localize\`...:Retrieving the entity details\`})`and
clear the entity (DET-13);`finalize`clears`loading`.
    - No resolver, no cache (DD-318's decision).

## The pure property filter (DET-11)

1. Create `src/app/search/details/property-filter.ts`:
    - `LEGACY_PROPERTY_BLACKLIST: ReadonlySet<string>` — copy the key set from
      the legacy source
      `.scratch/aurelius/apps/atlas/src/app/search/services/filtered-properties/blacklist-properties.ts`
      verbatim, with a citation comment naming that path.
    - `detailProperties(entity, shownDescription?): { key: string; value:
KnownValue }[]`: merge `attributes` then `relationshipAttributes` (the
      relationship value wins a clash — the legacy
      `{...attributes, ...relationshipAttributes}` spread order), drop nil
      values, blacklisted keys, and the key the description box shows
      (`shownDescription`, DD-320), drop values whose shape is
      neither scalar nor a `guid`-bearing array, sort by key. A `guid`-bearing
      array becomes the `properties-item` link shape
      (`{ guid, displayText: displayText ?? name ?? guid }`); scalars
      (`string`/`number`/`boolean`) pass through; anything else earns no row.
2. Create `property-filter.spec.ts` — merge order, nil drop, blacklist drop,
   sort, scalar/link/other classification, the displayText/name/guid fallback
   chain (DET-11).

## The breadcrumb store (DET-12, DD-317)

1. Create `src/app/search/details/details-breadcrumb-state.ts`: an
   `@Injectable()` signal holder the route component provides. `readonly
trail = signal<Breadcrumb[]>([])` (the `Breadcrumb` type imported from
   `aurelius-atlas-ui`), plus `setTrail(items)` and `clear()`. No fetch, no
   derivation (DD-317). Nothing in the details code calls `setTrail` yet —
   the seam is the API join's first line.
2. Create `details-breadcrumb-state.spec.ts` — reads empty, `setTrail`/read
   round-trips, `clear` empties (DET-12).

## The screen itself (DET-09, DET-10, DET-11, DET-13)

1. Edit `src/app/search/details/details.component.ts`:
    - imports add `TypeName`, `ClassificationChip`, `PropertiesItem` (the
      `Accordion`, `Breadcrumbs` stay).
    - providers add `DetailsState`, `DetailsBreadcrumbState`.
    - `inject(DetailsState)`; a `computed`/`effect` calls `state.load(guid())`
      when the `guid` signal changes (DET-08). (An `untracked` effect, or the
      existing route-param signal feeding `load` — no new subscription pattern
      that trips the purity gate.)
    - expose `entity = computed(() => state.entity())`, `loading`,
      `title` (`attributes.name || attributes.qualifiedName || titleFallback`),
      `descriptionKey` (`attributes.definition`, else `attributes.description`,
      each only when `typeof === "string"`, else `null`; `description` reads
      it, DET-10/DD-320), `properties = computed(() =>
detailProperties(entity(), descriptionKey()))`,
      `propertyCount`, `classifications` (from `entity.classifications`),
      `typeName`, and `trail` (from the breadcrumb store).
    - `onLinkClick(guid)` and the existing `onCrumbClick(guid)` both navigate
      `/search/details/:guid` (DET-06/DET-11).
2. Edit `details.component.html`:
    - title `{{ title() }}` (was the constant fallback); the type line becomes
      `<aurelius-atlas-ui-type-name [typeName]="typeName()" [showBaseTypeName]="true"/>`;
      a classifications block renders `<aurelius-atlas-ui-classification-chip
*ngFor=... [label]="c.typeName"/>` (DET-09).
    - description box content: the `Markdown` component on the text, the
      legacy placeholder line (`search.components.description.notAvailable`,
      `is-italic has-text-centered`) when there is none (DET-10, DD-321).
    - count line `{{ propertyCount() }}`; the accordion `<tbody>` gains a
      `properties-item` row per `properties()`, Key = the key, Value =
      `properties-item [value]` with `(itemClicked)="onLinkClick($event)"`
      (DET-11). Keep the Key/Value `<thead>` (DET-04). With zero rows the
      accordion shows the legacy placeholder line
      `components.sortableTableShell.noData` (DET-11).
    - a loading line under the header, `*ngIf="loading() && !entity()"`,
      labelled `@@search.services.entityDetails.retrieve` (DET-13).
    - the `breadcrumbs` component gains `[items]="trail()"` (empty by default,
      DET-12); `activeGuid` and `(itemClicked)` stay.
    - keep every existing class hook (`aurelius-details-title`,
      `aurelius-details-type`, `aurelius-details-description`,
      `aurelius-details-property-count`, `aurelius-details-properties`,
      `#description-details`, `#properties-details`, `.aurelius-details-nav`)
      so 7.6's specs and DET-07's e2e keep their selectors.
3. Edit `details.component.scss` only if the new header rows need spacing.

## Tests

1. Edit `src/app/search/details/details.component.spec.ts`:
    - replace "issues no HTTP requests" (7.6, superseded by DET-08) with: the
      render fires `GET …/entity/guid/<route-guid>` and nothing else; flush a
      stub entity, assert title/type-name/chips/description/rows/count (DET-09/
      10/11); a guid change re-fires; a superseded guid's answer paints
      nothing (DET-08).
    - loading: before flush, the loading line is present (DET-13); error
      (`req.error({status:404})`) leaves the DET-02 empty chrome and adds no
      row; `req.error({status:500})` renders an alert entry via
      `AlertsService` (spy or provider), DET-13.
    - link-array row: flush an entity with a `guid`-bearing relationship
      value; click the anchor, assert `Router.navigate(["/search/details",
linkedGuid])` (DET-11).
    - keep the DET-01 anatomy, DET-02 empty state (now on a no-answer guid),
      DET-04 strings, DET-06 crumb routing, DET-05 purity specs green.
2. Confirm `i18n-completeness.spec.ts` still passes: 7.20 uses only keys the
   bridge carries (`search.services.entityDetails.retrieve`,
   `search.details.default.*`, `search.details.components.properties.*`,
   `search.details.components.classification.*` if the chip's lead needs one,
   `search.details.typeSelect.label`). Add no catalogue keys (DET-04, SHL-08).

## e2e (DET-14)

1. Edit `e2e/test__aurelius_atlas_webapp.py`:
    - add `test__details_screen_shows_a_seeded_entity`: seed one entity with
      the 7.4a `_seed_entities` helper (a `DataSet` type, a unique single-token
      name), set its `description` through the EWR-15 attribute update
      (`PUT /entity/guid/{guid}?name=description`), goto
      `/en-US/search/details/<guid>`, assert the title shows the seeded name,
      the type-name line reads `DataSet`, and the description box carries the
      seeded text with zero properties rows and the count reading 0
      (`name`/`qualifiedName` ride the title, blacklisted per DET-11;
      `description` rides the box per DET-10/DD-320). Uses the
      `authenticated` fixture and the `user_token`; never restarts a shared
      `dev/*` service (DD-223).
    - extend the 7.4a card-to-details scenario (SRH-05) with the live-title
      assertion now the header renders from data.
    - rename `test__details_skeleton_renders_at_the_deep_link` (DET-07) to
      `test__details_screen_answers_a_404_deep_link_with_the_empty_state` and
      drop its no-API-request assertion — the screen fetches now, the 404
      answers empty, no alert dot rides the bell (DET-13). The nl-NL chrome
      scenario stays; a guid nothing owns still answers empty.

## The markdown block (DET-10, DD-321 — review round)

1. Create `libs/angular/aurelius-atlas-ui/src/lib/markdown/`: the
   `Markdown` component (`aurelius-atlas-ui-markdown`) — `marked` with a
   per-component instance carrying the legacy Bulma renderer mappings
   (heading → `title is-N`, blockquote → `article.message`, table →
   `table-container > table.table.is-striped`, image → `figure.image`), the
   HTML bound through `[innerHTML]` (Angular's sanitizer is the XSS guard);
   exported from the library's public API, with its Vitest spec (the four
   mappings, markdown emphasis, the sanitized `javascript:` URL and stripped
   raw markup) and its Storybook story. The legacy
   `libs/components/src/lib/markdown/` registers its renderers on the global
   `MarkdownService` from the constructor — the port drops that shape.

## Gate

1. `npx prettier --write` every new/edited TS, HTML, and md before staging.
   `nx test aurelius-atlas-ui -c ci` and `nx lint aurelius-atlas-ui` cover
   the markdown component.
2. Level-0 offline: `nx test aurelius-atlas-webapp -c ci`,
   `nx lint aurelius-atlas-webapp`,
   `nx run aurelius-atlas-webapp:check-purity`, `nx typecheck` (if the project
   declares it), `uv run aurelius-atlas-trace check` (report the DET gaps).
3. Level-2: `nx e2e aurelius-atlas-webapp` (chromium/firefox/webkit).
4. Commit through pre-commit (conventional-commit title:
   `feat(webapp): 7.20 the details data spine (DET-08..14)`), open one PR,
   flip the spec/roadmap to `done` and get the `DD-317`/`DD-318` status lines
   moved to Accepted by a person (never self-accept).

## Out of scope (do not build here)

- The type dispatch and the nine `m4i_*` layouts; the `m4i_*` header blocks
  (People, quality stats, related-cards lists, lineage) — deferred table.
- Any server change, a trail endpoint, or a new data-access/ui method — the
  client and components are already complete (8.17–8.19, 7.13/7.16).
- The `meanings`/term chips, edit affordance, delete flow, audit/BM cards —
  the 7.7/7.8/7.9 slices.
