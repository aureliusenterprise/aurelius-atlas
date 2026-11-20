# 7.31 Editor drawer room and richer relationship rows

- **Status:** in progress
- **Pull request:** —
- **Records:** DD-711 (the relationship picker searches the view family's door,
  EDT-14 amended, EDT-33), DD-712 (the drawer's `size` input, UIC-43). Relies on
  7.7c (EDT-13..EDT-19, DD-338..DD-343), 7.7a (EDT-05/DD-335, DD-336's combobox),
  16.1 (AVS-01/AVS-03, the card shape), 16.2 (AVR-02/AVR-04/AVR-11, the search
  door), 16.5a (VSR-03, the door's webapp client), 16.5d (VCF-01, the rich card),
  16.5g (VDR-11, the trail rule), DD-157 (the drawer's anatomy), DD-379 (the type
  display names), DD-378 (the type icons).

Two pieces of feedback on the editor. A relationship picker's suggestion list
shows one name per row, and two entities in the store can carry the same name —
the reader cannot tell them apart before choosing one. The catalogue's cards
solve the same problem by printing the entity's type beside its name and the
trail under it
(16.5d). And on a wide screen the editor drawer holds the same 28rem panel the
settings and alerts drawers use, which leaves most of the screen unused and
squeezes the form.

## Scope

- the picker's rows: each suggestion prints the entity's type and its trail, the
  way a card does (EDT-33);
- the picker's search: it asks the view family's door, which answers cards with
  the type and the stored trail on them (EDT-14 amended);
- the drawer's width: the panel takes `narrow` (28rem, today) or `wide`, and the
  editor asks `wide` (UIC-43);
- the unchanged neighbours: the box's anatomy, the debounce, the limits, the
  exclusions, the chip, the save, and the required gate (EDT-13..EDT-19) all
  stand, and the settings and alerts drawers keep the narrow panel.

Not in scope:

| Not delivered                                           | Lands with | Why                                                                                        |
| ------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------ |
| A side-by-side markdown pane pair (7.7d's stack stands) | –          | The editor's Write/Preview tabs are the shipped shape; a wider panel does not ask for them |
| The legacy picker's facet strip and its results count   | Never      | The legacy's App Search facets have no Aurelius answer (DD-140); the panel is a hint       |
| The trail's stored data (the indexer derives it)        | 14.2       | The picker only reads what the card carries                                                |
| A wide settings or alerts drawer                        | –          | Those panels hold a short form and a feed; the user's feedback named the editor            |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UIC-43 | The `Drawer`'s panel takes a `size` input with two values, `narrow` and `wide`; `narrow` is the default and keeps the panel today's 28rem, and `wide` grows it to 44rem (DD-712). Both values are capped by the viewport (`min(…, 100vw)`), so a small screen is unchanged, and the panel stays anchored to the inline-end edge with the same head, subhead, body and foot slots (DD-157, UIC-25). The input changes only the panel's width: nothing else in the anatomy follows it, so a caller that leaves it out renders exactly what it renders today (the settings and alerts drawers).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| EDT-14 | **Amended (7.31):** each picker is the classification box's anatomy (DD-335/DD-336) — the chosen entities ride inside the bordered box as `classification-chip` components (UIC-16) with the UIC-24 delete, and the text input sits borderless in the same box. Typing at least one character searches through the view family's search door (16.2, VSR-03) with `filters.typeName` naming the field's target type and its sub types (the same `any` of `typeName`/`superTypeNames` the results screen sends, VSR-04), `limit` 10, and the typed text sent so it matches the beginning of a name (DD-711). The search is debounced (250 ms), like the stock's delayed select2. An empty box that gains focus — and text cleared back to empty — runs the same search with no text and `limit` 5: a browse of up to five candidates of the target type (DD-343). Of the cards the door answers, the panel keeps the ones whose display text begins with the typed text, case-insensitively, which is the name-prefix rule the stock attribute search applied server-side. The rest of the rule is unchanged (EDT-33). |
| EDT-33 | A picker's suggestion row is one option carrying the entity's name and its type on the first line, and the trail below (DD-711). The name is the card's `displayText` (AVS-03). The type is the card's `typeName` by its dictionary display name with the app's type icon and colour class (DD-379, DD-378) — the badge a card's title line carries (VCF-01). The trail is the card's stored parents, top down, by the shared crumb rule (VDR-06, VDR-11: no stored parent, no trail); the row is the entity itself, so its own crumb is not printed. The option's accessible name is the whole row: name, type, then trail. The row clears the touch floor EDT-14 already sets (24px, 48px on coarse pointers) and stays a `role="option"` inside the box's listbox (DD-336). The exclusions, the pick path and the keyboard model are EDT-14's and do not change; a card always carries a guid, so the panel has no unpickable row.                                                                                                                                                                                |

## Aurelius origin

The relationship picker is the legacy
`.scratch/aurelius/apps/atlas/src/app/search/components/editor/components/relationships-input/relationships-input.component.html`
(pinned commit). Its suggestion list seats one
`models4insight-details-card [searchResult]="option"` per `.dropdown-item`, so
the legacy row already carried the entity's badge and the card body — it is the
search-result card, the same shell the catalogue rows use. The legacy picker's
facets and results count come from the App Search index this product does not
have (DD-140), so they stay out.

The name, type and trail the row prints are the fields 16.1's card carries
(`EntityCard`: `displayText`, `typeName`, `breadcrumb`, AVS-01) and 16.5d's
rich card renders from them (VCF-01). The trail rule is 16.5g's shared one
(`shared/trail.ts`, VDR-06/VDR-11).

## Deviations

Against Apache Atlas: DV-177. The stock dashboard's picker searches
`GET /api/atlas/v2/search/attribute` (the endpoint this port keeps, and the one
7.7c chose in DD-339) and shows the found header's `displayText` only. The
Aurelius picker asks the view family's search door instead, because the door is
what answers a breadcrumb, and keeps the name-prefix rule on the client. The
Atlas endpoint, its parameters, and its answers are unchanged for every other
client (ADR 046).

Against the demo: none. The demo's picker row is a card; the Aurelius row is a
compact version of the same fields, sized for a panel inside a form.

## Acceptance

- `libs/angular/aurelius-atlas-ui/src/lib/drawer/drawer.component.spec.ts` —
  UIC-43 (the narrow default, the wide class, the small-screen cap) and the
  drawer's own story (`drawer.component.stories.ts`) for the pinned panel rect.
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-relationship-input.component.spec.ts`
  — EDT-14 (the door body: `typeName` plus sub types, the limits, the prefix, the
  250 ms debounce, the client-side name filter, the exclusions, the pick path,
  the combobox and its aria wiring) and EDT-33 (name, type badge and icon, trail,
  the accessible name, and the no-stored-parent row).
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts`
  — the editor mounts the picker in a wide drawer.
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp.py` — the
  mandatory-relationship flow (`test__the_editor_requires_a_mandatory_relationship`)
  still lands its pick through the panel's own rows, which now read name, type
  and trail (EDT-13, EDT-14, EDT-17, EDT-33).
- Run: `nx test aurelius-atlas-ui -c ci`, `nx test aurelius-atlas-webapp -c ci`,
  `nx e2e aurelius-atlas-webapp` (level 2).
