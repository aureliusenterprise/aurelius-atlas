# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one. Both parts of the increment
(webapp and ui library) share this file, as 7.4a's parts share theirs.

## Entries

### DD-352. The description field is a tabbed markdown editor over the shared block

- **Status:** Proposed
- **Increment:** 7.7d
- **Date:** 2026-11-04

**Decision.** The ui library gains `markdown-editor` (UIC-26), the port of the
legacy `models4insight-markdown-editor`: a string field control (a Signal
Forms `FormValueControl`, DD-354 — the legacy's `ControlValueAccessor` shape
retired with the editor's form layer), whose model is the markdown source.
The editor's
`definition`/`description` fields (EDT-03's textarea pair) render it instead
of a bare textarea (EDT-20). The layout is a Bulma `tabs` pair — Write over
the textarea, Preview over the existing `Markdown` block (DD-321) — not the
legacy's side-by-side `columns`. Both panes stay mounted and the inactive one
carries `hidden`, so a switch re-parses nothing and the textarea keeps its
caret and undo history. The preview binds the component's own value, so the
drawer previews exactly the string the save will send, rendered exactly as
the details box renders it. The XSS guard is the block's `[innerHTML]`
sanitizer — the one DET-10 already rides — so no second sanitizer enters and
`dompurify` never returns to the dependency graph (DD-321's alternative
stands).

**Reason.** The value these two keys carry is markdown (the details box
renders it as markdown, DET-10), so a plain textarea shows the user syntax
the product will render. The reviewer asked for an editor with a preview. The
legacy ships the component and the component is the shape of the answer:
source plus live preview, no WYSIWYG. The tab pair, not the columns, because
the editor is a 28rem drawer: two columns of prose at ~12rem each are
unreadable, and the legacy's own app never wired the component, so there is
no wiring or layout to be faithful to. Stacked (textarea always above a live
preview) was the runner-up: it shows both at once, but a long description
doubles the scroll inside a drawer that already scrolls. Tabs also match the
app's one existing tabbed surface (the details screen's section tabs), so the
gesture is learned once.

**Alternatives.** (a) Keep the columns, hidden behind a wider drawer (refused:
the drawer width is 7.12's chrome decision; a field cannot dictate it).
(b) Stacked preview (refused: doubles the scroll; kept as the fallback if the
review prefers it). (c) A `marked` call of the editor's own with
`dompurify` (refused: a second renderer invites the two halves to drift, and
DD-321 already chose the sanitizer). (d) WYSIWYG (refused: it rewrites the
stored source on every edit — the Atlas value is source text, and the legacy
model is source plus preview). (e) Toolbar buttons (refused: the legacy
shipped none, and none of the buttons' words exists in the dictionary).

**Consequences.** UIC-26 and EDT-20 are written; EDT-03 in the 7.7a spec is
amended in place (the description keys' kind is now the field, not the
textarea). Two pinned tests move on purpose: `form-fields.spec.ts` expects
the new kind, and the editor render test finds the same
`textarea#editor-description` one level deeper. The save path is untouched
(EDT-06), so no server or e2e save expectation changes. The component is a
Signal Forms control, so it joins the editor's form through `[formField]`
like every other field (DD-354) — required marker, danger state, and the
invalid-save refusal ride EDT-03/EDT-07's plumbing unchanged. The
ui library adds no dependency: `marked` is already the block's.

### DD-353. The field's three words are vendored bridge keys

- **Status:** Proposed
- **Increment:** 7.7d
- **Date:** 2026-11-04

**Decision.** The field shows three words: `Write`, `Preview`, and the
placeholder "Please type some markdown to get started...". All three ride new
bridge keys — `components.markdownEditor.writeLabel`, `.previewLabel`,
`.placeholder` — vendored into both dictionary fixtures and both XLIFF
catalogues, the DD-351 pattern. The placeholder's English is the legacy
component's own hardcoded text, recovered from the source. The tab words and
all three Dutch lines are this project's, and the design record says so: the
legacy component shipped no dictionary file, so there is no Aurelius text to
vendor for them.

**Reason.** Every shown string must ride a catalogue key (SHL-08), and the
ui library's rule keeps the strings out of the component (UIC-04/DD-136: the
caller binds them). The components namespace is where ui-library chrome
strings live (`components.modal.close`, `components.sortableTableShell.*`).
The completeness gate is fixture-driven, so vendoring the keys into the
fixtures and the catalogues keeps it green and names them, and the gate then
holds both locales for good.

**Alternatives.** (a) Hardcode English in the template (refused: SHL-08, and
DD-351 already ruled this way for the hold tooltip). (b) Reuse a near word
from the bridge — no key carries "Write" or "Preview" (checked all three
fixtures, both locales), and forcing one would mislabel the tab (one word,
one meaning). (c) Leave the placeholder out (refused: the legacy shows it, an
empty markdown box reads as broken, and the empty field is the first thing a
writer meets).

**Consequences.** This is the increment's dictionary addition, alongside
DD-351's pair: four vendored keys in the tree now, each recorded where it was
added. `i18n-completeness.spec.ts` changes not one line — the gate reads the
fixtures. The Dutch is reviewable prose, not Aurelius's, and says so here
first; a later human pass may replace it, and the gate will hold whatever
text replaces it.
