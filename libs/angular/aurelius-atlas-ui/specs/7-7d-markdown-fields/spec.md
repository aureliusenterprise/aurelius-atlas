# 7.7d Entity editor: markdown fields

- **Status:** proposed
- **Pull request:** —
- **Records:** DD-352, DD-353; relies on DD-321 (the `Markdown` block and its
  sanitizer), UIC-04/UIC-03 (the ui library's string and colour rules),
  UIC-10 (stories with `play()` tests), UIC-15 (the library's line), DD-335
  (the combobox's `textareaId` seat, the same seam)

Part of the
[7.0 umbrella](../../../../../apps/aurelius-atlas-webapp/specs/7-0-webapp-foundation/spec.md),
whose rules WBP-01 to WBP-07 this slice inherits, and of the design-system track
opened by [7.2](../7-2-design-system/spec.md), whose UIC rule series this
increment carries on (UIC-26).

This page is the `aurelius-atlas-ui` part of increment 7.7d; its rule table is
the increment's shared set. The other part is with
[`aurelius-atlas-webapp`](../../../../../apps/aurelius-atlas-webapp/specs/7-7d-markdown-fields/spec.md).

## Scope

The ui library gains the markdown-writing field the entity editor's
description keys ride (EDT-20): `markdown-editor`, the port of the legacy
`models4insight-markdown-editor` (`libs/components/src/lib/markdown/editor/`).
The library already owns the reading half — the `Markdown` block (DD-321, from
the 7.20 details pass); this is its writing half, so the two share one
renderer and one sanitizer.

- the component: a Signal Forms control (a `FormValueControl` over a string
  field, DD-354), a Bulma `tabs` pair over a `textarea` and a preview pane
  (UIC-26). The legacy's
  `columns` pair (textarea beside preview) cannot fit the editor's 28rem
  drawer, and the tab pair replaces it (DD-352)
- the strings and colours: none of its own (UIC-04, UIC-03) — labels and the
  placeholder are caller inputs, the legacy's own defaults dropped for the
  same reason the search field's are (DD-136)
- the preview: the `Markdown` component, mounted and hidden until the Preview
  tab is active, so the library renders markdown one way (DD-321 stands)

Explicitly not delivered here:

| Not delivered here                                           | Delivered by                                                             |
| ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| Wiring the field into the editor form (the description keys) | the webapp part of this increment (EDT-20)                               |
| A formatting toolbar, WYSIWYG                                | nobody (the legacy shipped source + preview; DD-352 keeps that model)    |
| A sanitization change or a second renderer                   | nobody (the block's `[innerHTML]` guard is the one DET-10 already rides) |

## Semantics

The rule table is the increment's shared set (the trace tool reads the two
parts as one source); the webapp part holds the EDT-20 row beside this one.
Tests name the ids in the test title (the TS pattern, UIC-11..25's precedent).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UIC-26 | `markdown-editor` is the ui library's markdown-writing field: a Bulma `tabs` pair (labels from the caller, DD-136) over one `textarea` and one preview pane. The component is a Signal Forms control (a `FormValueControl` over a string field, DD-354): the model is the markdown source, the textarea edits it, and the preview pane renders that same value through the `Markdown` block (DD-321) live as the user types. The preview is the block's own rendering, so it needs no second parser and no second sanitizer (its `[innerHTML]` guard is the one DET-10 rides, DD-352). Both panes stay mounted and the inactive one hides (`hidden`), so a tab switch costs no re-parse and keeps the textarea's caret and undo history. The tab strip carries `role="tablist"`, one `role="tab"` link per pane with `aria-selected` on the active one and `aria-controls` naming the pane. `textareaId()` seats a caller's id on the textarea so a `<label for>` reaches the field. The textarea carries Bulma's `is-danger` when the bound field is invalid and marked (mirrored through the contract's `invalid` and `touched` inputs, the same state the caller's form sees). `placeholder()` is caller-supplied (DD-136). The component carries no string of its own and no colour (UIC-04, UIC-03). |

## Aurelius origin

The Aurelius 17 repo (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`):

- `libs/components/src/lib/markdown/editor/markdown-editor.component.*` — the
  component UIC-26 ports: a private `FormControl`, an `@Input() markdown`
  setter over it, and a `columns` template (textarea column, preview column
  with `max-height: 100ch`). Its placeholder is a hardcoded string with no
  dictionary key; the port makes it an input (DD-136).
- `libs/components/src/lib/markdown/markdown.component.ts` — the render block,
  ported by 7.20 (DD-321) and reused here untouched.

## Deviations

None against Apache Atlas (ADR 052 governs REST parity; the UI rides the
Aurelius reference). The deviation from the Aurelius component itself —
columns to tabs — is DD-352.

## Acceptance

- Vitest: `src/lib/markdown-editor/markdown-editor.component.spec.ts` (the
  UIC-26 rules above, each in a named test).
- Storybook: a `markdown-editor` story with a `play()` test that types,
  switches to Preview, and finds the rendered heading; passed in the
  storybook runner on chromium/firefox/webkit (UIC-10).
- The purity gate stays green (no legacy construct, DD-131/DD-137); the
  library adds no dependency (`marked` is already the block's, DD-321).
