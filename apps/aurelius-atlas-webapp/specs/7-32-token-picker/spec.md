# 7.32 A dumb relationship picker in the ui library

- **Status:** in progress
- **Pull request:** —
- **Records:** DD-713 (the `TokenPicker` ui-lib component, UIC-44), DD-714 (a
  row's trail is the `Breadcrumbs` component with its links off, amending
  UIC-11 and superseding DD-713's joined-string trail). Relies on
  7.7c (EDT-13..EDT-19, DD-338..DD-343), 7.7a (EDT-05/DD-335, DD-336's combobox),
  7.31 (EDT-14 amended/DD-711, EDT-33, UIC-43/DD-712), DD-189 (the chip), DD-190
  (the type badge), DD-341 (data wiring stays in the app), DD-136 (caller text),
  DD-606/DD-624 (the trail rule and its plain-text crumb).

The editor's relationship picker is the classification box's anatomy wrapped
around a search (7.7a, 7.7c). When 7.31 gave its rows the type and the trail,
the component grew to three hundred and forty lines, and none of its box, its
chips, or its keyboard model had a home in the ui library — where every other
presentational part of the product lives. The picker's markup and the
classification box in the editor are two copies of the same box, so a change to
one does not reach the other. This increment moves the box into the library as a
dumb component and leaves the search in the webapp.

## Scope

- the new `TokenPicker` in `aurelius-atlas-ui`: a bordered box holding deletable
  chips and a borderless input, a suggestion panel with the ARIA combobox
  keyboard model, and a row that prints a name, a type badge and a trail — the
  last with the `Breadcrumbs` component (UIC-44, DD-714);
- the `Breadcrumbs` component gains a linkless mode for a trail nested inside a
  control that owns the activation (UIC-11 amended, DD-714);
- the relationship picker becomes a thin webapp component that answers the box's
  `typed` event with rows and turns a pick back into the saved value (EDT-14,
  EDT-33 unchanged);
- the box's element classes, which the tests and the e2e suite reach, move to
  the component's own names (`.aurelius-token-*`).

Not in scope:

| Not delivered                                      | Lands with | Why                                                                                                       |
| -------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------- |
| The classification box on the new picker           | –          | Its chips are not suggestions and its rows carry none of the row's parts; reuniting them is a second step |
| A type-ahead on the search field                   | 7.4c       | That is the discovery surface, not the editor's box                                                       |
| Any change to what a row prints or how it is found | –          | 7.31 shipped both (EDT-14 amended, EDT-33); this increment moves the same behaviour                       |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UIC-44 | `TokenPicker` is the presentational half of a chip-and-suggest control (DD-713). Its `selected` chips ride inside a bordered box and are deletable through the chip's UIC-24 delete; its input sits borderless beside them; its `rows` open as a full-width panel while the box holds focus, with the panel model of DD-335 and the keyboard and ARIA combobox wiring of DD-336. A `single` box hides its input once it holds one chip. It resolves nothing: a row's name and badge arrive as finished strings and icons, and its trail arrives as the crumbs the `Breadcrumbs` component takes (DD-714). Everything it shows is an input and every intent is an output (`typed`, `picked`, `removed`, `entered`); it injects no service, so it never searches (DD-341). Its caller-localised text arrives as inputs (DD-136) and its ids mint from one `idBase` so two boxes on a page never collide. A row is a `div` with `role="option"` — the option is the row (EDT-33), the picker owns the keyboard, and the row's trail must nest no control (DD-714). |

The behaviour the webapp keeps is the shipped rules and no others: EDT-14's
search (the view door, the limits, the 250 ms debounce, the client name-prefix
check, the exclusions, the pick path) and EDT-33's row parts. The empty box that
gains focus browses (DD-343): the box reports the entry through `entered` and the
webapp runs the browse.

## Aurelius origin

The legacy `.scratch/aurelius/apps/atlas/src/app/search/components/editor/
components/relationships-input/` component is one component that both renders
the box and calls the search service, which is why no dumb part of it was ever
extracted (UIC-11..UIC-20 took the parts that were separable). The box itself is
the legacy classification control's anatomy (7.7a's DD-335). This increment
changes no rule that traces to the legacy code — it moves the presentational
half of EDT-14 into the library where the port's own conventions place it.

## Deviations

Against Apache Atlas: none. No REST contract, endpoint, or stored shape changes.

Against the demo: none.

## Acceptance

- `libs/angular/aurelius-atlas-ui/src/lib/token-picker/token-picker.component.spec.ts`
  — UIC-44 (chips in the box, the focus-gated panel, the row's parts, the
  combobox wiring and its ids, the arrow and Enter model, Escape, the single
  rule, the danger state and its error id, the chip delete, the trail printed
  by the `Breadcrumbs` component with no links, the row being a `div` option)
  and the component's story with its `play()` interaction test.
- `libs/angular/aurelius-atlas-ui/src/lib/breadcrumbs/breadcrumbs.component.spec.ts`
  — UIC-11 amended: `links` off prints every crumb plain, marks none active,
  carries no `aria-current` and emits nothing.
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-relationship-input.component.spec.ts`
  — the same EDT-14 and EDT-33 pins as 7.31, driven through the rendered box
  (the door body, the debounce, the name filter, the exclusions, the pick, the
  browse on entry, the chip delete).
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts`
  — the editor's picker reaches the box's classes and the error wiring through
  the library component.
- `apps/aurelius-atlas-webapp/e2e/test__aurelius_atlas_webapp.py` and
  `test__aurelius_atlas_webapp_quality_rules.py` — the relationship flows drive
  the box by its new class names (EDT-14, EDT-17).
- Run: `nx test aurelius-atlas-ui -c ci`, `nx test aurelius-atlas-webapp -c ci`,
  `nx e2e aurelius-atlas-webapp` (level 2).
