# 7.7d Entity editor: markdown fields

- **Status:** proposed
- **Pull request:** —
- **Records:** DD-352, DD-353; extends 7.7a (EDT-03, amended in place); relies
  on DD-321 (the `Markdown` block and its sanitizer, UIC-04/DD-136 (the ui
  library's string and colour rules), DD-128/DD-351 (the bridge and the
  vendored-key pattern), UIC-26 (this increment's ui-library rule)

Part of the
[7.0 umbrella](../7-0-webapp-foundation/spec.md), whose rules WBP-01 to WBP-07
this slice inherits. This page is the `aurelius-atlas-webapp` part of increment
7.7d; its rule table is the increment's shared set. The other part is with
[`aurelius-atlas-ui`](../../../../libs/angular/aurelius-atlas-ui/specs/7-7d-markdown-fields/spec.md).

## Scope

The editor's description fields learn markdown. The shipped types carry their
text in `description` (and the legacy read `definition`, DET-10/DD-320), and
both keys already open as plain textareas (EDT-03) — while the details screen
renders the same value as markdown (DET-10). What you write is therefore not
what you read: links show as brackets, and headings show as `#`.

Delivered here:

- the field: the `definition`/`description` textarea becomes Aurelius's
  markdown editor — a Write/Preview tab pair over the same control (EDT-20,
  UIC-26). The legacy ships this component (`models4insight-markdown-editor`);
  its own app never wired it, so this restores the component rather than
  copying a wiring
- the value: the form control keeps the markdown source, exactly as the
  textarea did. The save body (EDT-06) is untouched — no new attribute shape,
  no transform in either direction
- the preview: rendered through the same `Markdown` block the details box
  uses (DD-321), live as the user types, so the drawer previews what details
  will show
- the strings: three vendored bridge keys (`components.markdownEditor.*`),
  both locales, the DD-351 pattern (DD-353)

Explicitly not delivered here, with the increment that will:

| Deferred                                                   | Lands with | Why                                                                                                        |
| ---------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------- |
| A formatting toolbar (bold/link buttons around the editor) | Never      | The legacy shipped none, and no dictionary carries button strings. Keyboard markdown syntax stays natural  |
| Markdown fields on the type-def editor                     | its screen | That editor is the admin track; the field component is reusable there as-is (UIC-26)                       |
| WYSIWYG editing                                            | Never      | The legacy model is source + preview (DD-352), and a WYSIWYG would rewrite the stored string on every edit |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
in the test title (the TS pattern). The table is shared with the ui-library
part; the trace tool reads the two files as one source.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UIC-26 | `markdown-editor` is the ui library's markdown-writing field: a Bulma `tabs` pair (labels from the caller, DD-136) over one `textarea` and one preview pane. The component is a Signal Forms control (a `FormValueControl` over a string field, DD-354): the model is the markdown source, the textarea edits it, and the preview pane renders that same value through the `Markdown` block (DD-321) live as the user types. The preview is the block's own rendering, so it needs no second parser and no second sanitizer (its `[innerHTML]` guard is the one DET-10 rides, DD-352). Both panes stay mounted and the inactive one hides (`hidden`), so a tab switch costs no re-parse and keeps the textarea's caret and undo history. The tab strip carries `role="tablist"`, one `role="tab"` link per pane with `aria-selected` on the active one and `aria-controls` naming the pane. `textareaId()` seats a caller's id on the textarea so a `<label for>` reaches the field. The textarea carries Bulma's `is-danger` when the bound field is invalid and marked (mirrored through the contract's `invalid` and `touched` inputs, the same state the caller's form sees). `placeholder()` is caller-supplied (DD-136). The component carries no string of its own and no colour (UIC-04, UIC-03). |
| EDT-20 | The editor's description keys (`definition` and `description`, EDT-03's textarea pair) render as the ui library's `markdown-editor` instead of a bare textarea (DD-352). The control keeps the markdown source exactly as the textarea did, so the saved body (EDT-06) carries the same string a textarea save would have sent — the read seeds it, the save sends it, and no transform sits between. The field keeps EDT-03's plumbing unchanged: the bridge label, the `for="editor-<name>"` seat (EDT-11) through the component's `textareaId`, the required marker, and the refused invalid save (EDT-07). The tab starts on Write. The preview rides the same `Markdown` block the details box uses (DET-10, DD-321), so the drawer previews what details will show. The field's three strings (`Write`, `Preview`, the placeholder) ride the vendored keys `components.markdownEditor.writeLabel`/`.previewLabel`/`.placeholder` in both catalogues (DD-353, the DD-351 pattern): the English placeholder restores the legacy component's hardcoded text, and the tab words and the Dutch lines are this project's.                                                                                                                                                                                 |

## Aurelius origin

The Aurelius 17 app (`.scratch/aurelius`, commit `b057389828c10497dd52d9efd4c16547c282c005`):

- `libs/components/src/lib/markdown/editor/` — the `models4insight-markdown-editor`
  this ports: a `FormControl` over a Bulma `columns` pair, textarea beside a
  live `models4insight-markdown` preview, placeholder hardcoded
  ("Please type some markdown to get started..."). It exports no dictionary
  key, and the app itself never used the component (no `models4insight-
markdown-editor` use in `apps/`): its m4i field forms are plain textareas.
  DD-352 replaces its side-by-side columns with the tab pair.
- `libs/components/src/lib/markdown/markdown.component.ts` — the render block
  7.20 already ported (DD-321); this increment reuses it for the preview and
  adds no rendering of its own.
- `libs/components/src/lib/markdown/editor/+stories/` — the legacy story
  (Primary, 500px): the empty-field shape the new story starts from.

## Deviations

None against Apache Atlas: the stock 2.4 dashboard's description field is a
plain textarea, and this increment extends the Aurelius product's own field
component (ADR 052 governs REST parity; the UI rides the Aurelius reference).
No `DV-` row.

## Acceptance

- Vitest (unit, `libs/angular/aurelius-atlas-ui`):
    - `src/lib/markdown-editor/markdown-editor.component.spec.ts` — the
      bound-field loop (setting the field's value fills the textarea, typing
      writes the source back to the model, blur marks the field touched
      through the contract's `touch` output), the preview renders marked
      output live (a heading token proves the shared renderer), the tab pair
      switches panes with `aria-selected` moving and the inactive pane
      `hidden` (UIC-26), `textareaId` seats on the textarea, `is-danger`
      follows the field's invalid-and-marked state, and a disabled field
      disables the textarea.
    - `src/lib/markdown-editor/markdown-editor.component.stories.ts` — a
      `play()` test: type, switch to Preview, the pane shows the rendered
      heading (UIC-10's pattern), across chromium/firefox/webkit in the
      storybook runner.
- Vitest (unit, `apps/aurelius-atlas-webapp`):
    - `src/app/search/editor/form-fields.spec.ts` — the kind of
      `definition`/`description` flips from `textarea` to `markdown` (the
      pinned test, moved on purpose; EDT-20 names the rule in its title).
    - `src/app/search/editor/entity-editor.component.spec.ts` — the render
      test keeps finding `textarea#editor-description` (now inside the
      component) with the seeded value; a new test names EDT-20: the field
      carries the tab pair with Write selected, the label's `for` still points
      at the textarea, and a save sends the raw source string unchanged.
    - `src/app/i18n-completeness.spec.ts` — unchanged and green with the
      three `components.markdownEditor.*` keys present in both catalogues
      (EDT-20, DD-351's pattern).
- Playwright (e2e, `apps/aurelius-atlas-webapp/e2e`) — the editor scenario
  grows one interaction: open the editor, type `# Heading` into the
  description, switch to Preview, see the rendered `h1`, save, and the details
  description box shows the same rendered heading (the write-then-read circle
  in one scenario).
- Docs gates: prettier, markdownlint, `zensical build --strict`.
- Trace: `uv run aurelius-atlas-trace check` reports no new gap (UIC-26 and
  EDT-20 each named by a test title).
