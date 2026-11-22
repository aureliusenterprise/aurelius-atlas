# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-825. The change list words a prose change and prints it last

- **Status:** Proposed
- **Increment:** 7.40
- **Date:** 2026-11-22

**Decision.** The change list prints `definition` and `description` in their own
section under the two tables of HST-12. Each block shows one text, not two: the
words the write kept are printed plain, the words it added ride `ins`, and the
words it took away ride `del`. A marked word carries a theme wash behind it —
Bulma's success and danger soft helpers — on top of the mark's own
strikethrough and underline. A run of kept words longer than a few is folded to
one marker so a one-sentence edit of a long definition answers in a few lines.
The two attributes leave the attributes table, and the section sends no request.

**Reason.** A definition is the attribute a person most often edits by mistake
and least often wants to retype (DD-822's restore exists for exactly that). 7.37
answers it as `del` of the whole old text and `ins` of the whole new text, so a
one-word fix to a four-hundred-word definition prints eight hundred words and the
reader has to find the fix themselves (HST-15). A word diff answers the same
change in the two lines that hold it. The section prints last rather than first
because the attributes table answers "what fields moved" at a glance and a prose
block needs height: leading with a folded paragraph pushes the short rows the
reader scans off the drawer (HST-15). Folding is a rule of its own (HST-16)
because an unfolded long definition costs the drawer its scroll, and a tooltip is
the worst place to read prose. A long definition marks few words in a lot of text,
so the marks alone are hard to spot; a wash behind them answers where the eye must
land. It rides the theme's own tokens rather than a colour of its own, so the
dark theme gets its own shade with no extra rule, and the mark still carries the
meaning on its own — the colour is reinforcement, never the only signal.

**Alternatives.** A `Descriptions` caption above the blocks: refused, every block
already names the attribute it words, so the caption says the same thing one line
earlier and the reader pays for a word twice. Keeping the two attributes in the attributes table and marking
words inside the Value cell: refused, that cell answers every other attribute with
one short value, and a folded paragraph in it would read as a broken row.
Rendering the markdown and diffing the rendered HTML: refused, marked words cannot
survive a run that crosses a paragraph, list item or heading boundary, and Angular
sanitizes `[innerHTML]` on every binding, so a hand-built HTML diff is a second
sanitizer to get right (DD-321). Side-by-side two-column diff, as a code review
tool draws it: refused, the drawer is a narrow pane and two columns halve the
already narrow measure. A dependency for the diff (`diff`, present transitively at
4.0.4): refused, a word diff is a common-prefix and common-suffix trim plus a
longest-common-subsequence over a small window, roughly forty lines, and it would
be unpinned and unreviewed. Colour replacing the marks, as a syntax highlighter
colours added and removed text: refused, colour alone carries no meaning for a
reader who cannot tell the two hues apart, and it needs a theme rule of its own.
Colour _behind_ the marks was taken up instead, and the marks keep their
strikethrough and underline. Putting the section first: refused on the height
argument above.
