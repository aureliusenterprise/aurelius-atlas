# 7.40 History definition diff

- **Status:** in review
- **Pull request:** #445
- **Records:** DD-825 (the change list words a prose change and prints it last).
  Adds HST-15 and HST-16, amends where HST-12 puts its two tables. Relies on
  HST-10..HST-14 (7.37..7.39), AUD-03/AUD-04 (the stored bodies), AUD-06 (the
  audit wire is read-only), EDT-20 (the description key rides the markdown
  field), DET-10/DD-320 (that same key is the entity's description) and
  SHL-08 (every string is catalogued). HST-15 amended in place by 18.8 (SPA-06,
  DD-832): one prose attribute, not two.

## Scope

A change list answers which attribute changed and shows its old and new value
(7.37). For a short value that reads well. For the prose attributes —
`definition` and `description` when 7.40 shipped, the fields the editor paints
as markdown (EDT-20) and the details screen paints as the entity's description
(DET-10) — the answer is useless: a person edits one sentence of a
four-hundred-word text, and the change list prints both full texts in one row.
The reader has to compare two walls of text by eye to find the sentence that
moved. 18.8 left one prose attribute (SPA-01); the section below reads it.

This increment gives those attributes their own section in the change list.
The section prints one text with the changed words marked, the way a review
tool shows a prose edit, instead of two texts side by side.

Not delivered here:

| Deferred                                                | Lands with | Why                                                                                                                                                                                          |
| ------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A rendered markdown view of the prose change            | –          | The reader of a diff wants the words that moved, not the heading they sit under. Marking words inside rendered HTML means marking across element boundaries, which the marks cannot survive. |
| The same word diff for any other attribute              | –          | Every other attribute holds a short value, a list or a struct. 7.37's old-and-new row answers those, and HST-12 keeps them.                                                                  |
| Restoring a prose attribute from the diff               | –          | The restore button of 7.38 (HST-11) already sits on this row in the attributes table. The section is a reading view, so it carries no write control.                                         |
| A diff of the markdown source against its rendered text | –          | Only the source is stored (AUD-03). The rendered text is a view, and a view the store does not hold is not a state to diff.                                                                  |

## Semantics

Each rule the behaviour must obey, in plain words, with an id that tests name
in the Vitest title.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HST-15 | An open change list prints its prose attributes in their own section, and nowhere else. The section sits under the attributes and relationships tables of HST-12, and a change list with no prose change prints no section (HST-10). The section holds exactly the attributes the editor renders as markdown, `description` alone (EDT-20 as amended by 18.8, SPA-06: the m4i dictionary's `definition` is retired): those leave the attributes table, so one attribute answers in one place. The section prints one block per changed attribute, and the block names its own attribute with the localized name the form's field carries (HST-14); the section adds no caption of its own, because every block already says which attribute it words. Under that name prints one text that carries the change. The text marks every word the write added in the `ins` mark and every word it took away in the `del` mark, and prints every word that stayed unmarked. An attribute the write filled for the first time marks its whole text as added, and an attribute the write cleared marks its whole text as removed, in the same marks. The marks are the browser's own `del` and `ins` elements, and they keep their own strikethrough and underline. A marked word also carries a light wash behind it — the added words the success wash, the taken words the danger wash — drawn from the theme's own colours, so a marked word is found at a glance in a light theme and in a dark theme alike. The wash only draws the eye: the mark still says what changed when the colour is not seen. A person who cannot write entities reads the section exactly as a person who can (EDT-09): the section holds no control. |
| HST-16 | A long prose change stays readable, and the section asks for nothing. Words the write kept are printed only around a change: text of the same words on both sides of a marked run is replaced by one marker that says words were left out. The section prints at most the words on either side of each change and folds the rest, so a one-sentence edit of a long definition answers in a few lines and not in the whole definition. A block with no long stretch left out prints in full. Long words and a narrow drawer wrap inside the block and never widen it, and the block keeps the prose readable at the drawer's width. The section builds from the two states the audit row already stores (AUD-03): it sends no request, reads nothing more, and the audit wire stays read-only (AUD-06). A row whose body the server cut down answers not recorded and prints no section (HST-10, AUD-04).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Aurelius origin

Neither reference screen has a change list, so this slice has no parity
reference for the diff (ADR 046):

- Apache Atlas 2.4.0 `audit-table.component.js` — the stock dashboard's audit
  table lists the action, the time and the user only, and never opens a change
  list.
- The Aurelius 17 app (`apps/atlas/src/app/search/components/editor/`), the
  history template — the drawer's history tab shows the translated action, the
  user and the time, and nothing else.

Two shipped shapes carry over instead:

- `apps/aurelius-atlas-webapp/src/app/search/editor/form-fields.ts` (EDT-20) —
  the editor's own rule for which attributes are prose: `DESCRIPTION_KEYS`
  names the prose key and routes it to the markdown field (18.8: `description`
  alone, SPA-06).
  The section takes the same two keys from the same place, so the form and the
  change list agree on what prose is.
- The `del` and `ins` marks of 7.37 (HST-10) — the change list's own old and new
  marks. The section marks words with them rather than inventing a second
  change style.

## Deviations

Against Apache Atlas: none. The stock dashboard shows no change list at all, so
there is nothing to diverge from.

Against the Aurelius 17 app: none. Its history tab shows no per-field detail, so
there is no prose diff to diverge from either.

## Acceptance

- `apps/aurelius-atlas-webapp/src/app/search/editor/audit-details.spec.ts` —
  the differ answers a prose change as one diff with the words it marks, and it
  leaves the two prose attributes out of the attributes table (HST-15). An
  added, a cleared and an unchanged prose attribute answer as they should, and
  a change list with no prose change answers no section (HST-15).
- `apps/aurelius-atlas-webapp/src/app/search/editor/description-diff.spec.ts` —
  the word diff: unchanged words unmarked, added words marked in, taken words
  marked out, a whole text marked when the write filled or cleared it, and a
  long stretch of kept words folded to one marker with the words on either side
  kept (HST-15, HST-16).
- `apps/aurelius-atlas-webapp/src/app/search/editor/entity-editor.component.spec.ts`
  — the section prints under the two tables with one block per prose attribute,
  each block naming its own attribute and the section carrying no caption,
  marked words reach the DOM in the `del` and `ins` marks with
  the theme's wash behind them, the two prose names are gone from the attributes
  table, a folded stretch prints its marker, and the section carries no write
  control for a reader who cannot write (HST-15, HST-16, EDT-09). Opening the
  section sends no request (AUD-06).
- `apps/aurelius-atlas-webapp/src/app/i18n-completeness.spec.ts` — the new keys
  are in both vendored dictionaries and both catalogues (SHL-08).
  Run from the repo root: `nx test aurelius-atlas-webapp -c ci`.
