# 7.56 The shared chrome labels move to `search/shared/labels.ts`

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-883 (here). No new rule ids. Cites UIC-21 and SRH-04 (the
  infinite-scroll container takes its next-page copy from the caller), UIC-34 and
  DD-136 (the facet list's show-more/show-less labels are caller-supplied),
  VCF-10 and SRH-07 (the filter popover's empty line), HST-08 (the audit trail
  pages with the same next-page words), SHL-08 (both locales carry every key),
  and DD-869 (the layering rule that puts code two features need in `shared/`).

## Scope

Four strings that the ui components take as caller-supplied copy — the next-page
label, the facet show-more and show-less labels, and the filter popover's empty
line — were declared as `$localize` members on each screen that mounts those
components. The first three sit on the details screen and the results screen, and
the next-page label sits on a third component (the editor's audit tab). This
increment hoists them into one module and leaves every member in place reading it.

The change (no behaviour, template text, or string change):

- A new `search/shared/labels.ts` exports four constants —
  `LOAD_NEXT_PAGE`, `FACET_SHOW_MORE`, `FACET_SHOW_LESS`, `FILTER_NOT_AVAILABLE` —
  each the same `$localize` expression the screens carried, with the same id.
- The three screens keep their own member names (`loadLabel`, `showMoreLabel`,
  `showLessLabel`, `notAvailableLabel` on details, `noFilters` on results,
  `auditLoadLabel` on the audit tab) and now assign the constant. No template
  binding, css class, id, or role changes, so every unit and e2e pin is untouched.
- Only these four moved. The details screen keeps its six remaining `$localize`
  members: four are chrome copy used once (`searchPlaceholder`, `resultWord`,
  `filterLabel`, `peopleEmpty` — the first three name a
  `search.details.components.detailsCardsList.*` key no other screen reads), and
  two belong to this screen alone (`editTitle`, the pencil's label, and
  `titleFallback`, DET-02's title fallback). Hoisting any of them would put
  single-use copy in a shared module and imply a sharing that does not exist.
- The spec does not change. These labels are pinned by the screens' own rendering
  tests (the facet menu, the filter popover, and the paged lists assert the
  words), and those tests drive the whole screen — nothing to move, nothing to
  add. The four constants have no test of their own, matching how the other
  exported localised constants in this tree (`GOV_QUALITY_TITLE`,
  `DATA_QUALITY_NOT_AVAILABLE`) are pinned: through what renders them.

It does **not** deliver: a labels module for the whole app (only the four strings
two or three screens actually share); the single-use details labels (listed
above); any change to a string, a css class, an id, or a role (the ids are
byte-identical, so `src/locale/messages*.xlf` and both locale fixtures do not
move); the rest of the details split (the header's remaining pieces, the score
box, the card sections); or a change to `java-map.md` and `deviations.md`
(nothing here touches Atlas behaviour).

## Semantics

No new rule ids. What this increment pins, as stated:

- **The ui components' caller-supplied rule is unchanged.** UIC-21, UIC-34, and
  VCF-10 all take their copy as inputs from the mount; this increment changes who
  owns the literal, not who passes it. Each screen still hands the string to the
  part.
- **The catalogue is unchanged.** The four `$localize` ids move verbatim, so the
  generated catalogues and both locale fixtures stay byte-equal (SHL-08), and the
  i18n completeness spec passes with the same six checks.
- **One definition per string.** The four duplicated literals become one each, so
  a wording change is a one-line edit instead of a search for twins.
- **The layering rule still holds.** `shared/` imports nothing from a feature —
  the new module has no imports at all — and the features continue to read down
  into `shared/` (DD-869, enforced by `check-webapp-purity.sh`).
- **1,047 tests stay green** across 85 files, unchanged: no test moves, no test
  added, and the words the screens print are identical.

## Java origin

Apache Atlas 2.4.0 has no Aurelius labels module. The four strings are already
ported and specced as caller-supplied copy for the ui parts (UIC-21, UIC-34,
VCF-10). Moving Aurelius code between Aurelius files adds nothing a parity test
can see, so this increment adds no row to `java-map.md`.
