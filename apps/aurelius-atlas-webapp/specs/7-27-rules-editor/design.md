# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply:
an accepted entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-477. The quality form is a mode of the one drawer, not a second editor

- **Status:** Proposed
- **Increment:** 7.27
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** The editor drawer (`src/app/search/editor/`) renders the quality form when its
type is `m4i_data_quality` and the rule is a vocabulary one (create mode, or edit mode over an
entity that names a `dqcheckkind`). Everything
around the form — the route and drawer open state (EDT-01), the entity read (EDT-02), the type
fixed off the route (DD-330), the classifications box (EDT-05), the save and its landing
(EDT-06), the governance banner (EDT-23), the write gate (EDT-08) — is the drawer's, unchanged.
The mode is a branch over the field set, keyed off the type name, the same dispatch the legacy
had (`editors-by-type.ts`), now inside one component tree instead of a registry of ten.

**Reason.** The legacy's ten hand-written editors each re-implemented the read, the save, and
the validation trigger; that is how its quality editor kept a save path (`id = -1`) no other
type used. The generic drawer already owns all of it, and 7.24 already proved the pattern of a
type-specific seam inside it (the relationship pickers, EDT-13..17, DD-338). A second editor
component would fork the save, the classifications diff, and the alerts, and lose the fixes
they get later. The mode reads the type because every door into the drawer arrives with one:
the create route carries it (DD-330), the edit read answers it.

**Alternatives.**

- A separate routed quality editor. It forks everything above, and the e2e and the purity gate
  would each carry two editors to prove.
- Keeping the generic attribute form and only prefilling it. Cheap, but the form would still
  draw `dqpattern` for a `COLUMN_IN_SET` rule and accept nonsense — the hole DET-35's rules
  already fall into (DQS-08 ERROR), which is the point of this slice.

**Consequences.** The drawer component grows one branch and one child component
(`quality-fields`); the generic path is untouched for every other type. The quality branch must
be tested as a pair with the generic one (the spec's Acceptance names both cases in the same
file).

### DD-478. The form's fields come from the served vocabulary, not the typedefs

- **Status:** Proposed
- **Increment:** 7.27
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** The quality form's kind list, dimension text, and parameter set come from 12.5's
kinds resource (QRE-01), cached in `QualityRuleService` after the first load. Each parameter
renders as the input its name implies (EDT-26's map): a Select over `castableTypes` for `type`,
a chips control for the two list parameters, number inputs for the three number parameters,
text for the rest. The typedefs are still read (the drawer reads them anyway), but the quality
branch draws no control straight from an attribute def.

**Reason.** The typedefs describe storage, not intent: `dqmin` and `dqmax` are plain doubles,
`dqvalues` a plain array, and nothing in them says which kind needs which (that is the engine's
`KindSpec`). A form drawn from the typedefs would show all twelve `dq` attributes for every
kind. The kinds resource names required and optional per kind, so the form can only build a
shape the engine parses. The service caches because the vocabulary is static per server build
(DD-475) and every `+` in the app opens the same form.

**Alternatives.**

- One control per `dq` attribute with a kind-dependent disable: still twelve controls on screen,
  and the "which ones are live" table lives in the browser — the mirror DD-475 closed.
- The Angular signals-schema path the generic form uses (DD-354): the schema wants a static
  shape, and the quality form's shape changes with the kind, so the branch holds explicit
  `Field`s over a values record — the pattern EDT-15's picker values already use.

**Consequences.** A kind added to the engine appears in the form with no webapp change (the
parameter names map through EDT-26's table; a name outside it renders as text). The webapp's
dependency on the server's vocabulary is the same release's (as DD-475's consequence says), so
no version skew needs handling.

### DD-479. A rule saves unchecked only when the quality form does not own it

- **Status:** Proposed
- **Increment:** 7.27
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** The validate-before-save call (EDT-28) guards the rules the quality form edits:
creates, and edits of a rule whose draft names a `dqcheckkind`. A legacy rule without the kind
(the DQ-07 `dataqualitytype`/`dataqualityoperator` pair) opens in the generic form and saves
without the call. Re-authoring one into the vocabulary — opening its pair's meaning in the kind
form — is a human act: the banner names the rule's kind-free state, and the user chooses to
convert. The browser never guesses which kind a free-text `expression` meant.

**Reason.** The engine reads both shapes (DQ-07), so a legacy rule is not broken, and the
scanner still runs it through the pair map (DQS-08's ERROR band). Forcing the drawer to convert
it would mean the browser deciding the rule's kind from its expression, which is the exact
guess DV-146 refused when it retired the stored expressions. The pair-map rules are a closing
population (the sample corpus's `nl1--*` rules), and the store's audits plus 7.25's score
verdicts make an unreadable one visible where it matters.

**Alternatives.**

- Convert on open, silently. It invents a kind the author never chose — a stored-meaning change
  no increment owns.
- Refuse to edit legacy rules at all. It punishes the reader for the author's history, and EWR
  refuses nothing today — the webapp would gate harder than the server.

**Consequences.** The drawer's mode test is "the type is the rule type and the draft names a
kind" (EDT-25/29's seam). A legacy rule converted through the kind form gains `dqcheckkind`;
its old pair attributes ride the untouched pass-through, so the engine's parser still reads it
as a vocabulary rule (the `dqcheckkind` branch wins, `atlas.py`). If the pair population ever
needs a sweep, that is a scanner-side report (a later increment), not an editor feature.

### DD-480. The human vocabulary copy rides the webapp catalogue

- **Status:** Proposed
- **Increment:** 7.27
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** The check kinds, their one-line descriptions, and the dimensions get human
names and copy in the webapp's two catalogues (EDT-31), keyed by the engine's name through
static `$localize` maps in the quality form. The kinds resource (QRE-01) still carries the
engine's names only, and so do the stored attributes and the validate body. A kind the
catalogue does not name falls back to its raw name with no description line.

**Reason.** The names are UI copy, and the webapp is where copy lives and gets translated —
the two catalogues already carry every other label on this screen, in both locales. Serving
them from the vocabulary would push display strings through an API designed for storage
semantics (DD-475's own line: the resource answers the engine's shape), and would still
need a second round to translate them, since `$localize` cannot translate a string that only
exists at runtime. The static maps keyed by kind name are the only shape that keeps the
translation gate (`i18n-completeness.spec.ts`) honest.

**Alternatives.**

- `kindLabel`/`kindDescription` fields on the kinds resource. The server answers with English
  UI strings, the catalogue gate cannot see them, and Dutch users get English — the split the
  bridge exists to prevent.
- Runtime dictionary files fetched beside the kinds. A third round-trip for strings the build
  already knows, outside every other screen's i18n pattern.

**Consequences.** A new engine kind shows in the form with its raw name and no description
until the catalogues name it — a translation task, not a deployment blocker. The fallback is
tested (EDT-31) so the unmapped case is a known state, not a crash.

### DD-481. The threshold is a slider beside an editable number

- **Status:** Proposed
- **Increment:** 7.27
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** The threshold control is an HTML range input beside a number input, side by
side (EDT-32). Both take their bounds from the served `thresholdMin`/`thresholdMax` (QRE-01),
step 0.05; one value backs both, editing either moves the other. An empty number rests the
slider at the engine's default (1.0) without writing the value. The pair sits in the form's
field rhythm like any other field.

**Reason.** A threshold is a ratio a person reasons about as a position ("nearly all rows"),
and a slider answers that; but exact values (0.97) are typed, not dragged, so the number
field stays first-class. The native pair needs no library and holds the served bounds, so a
server that widens the range widens both controls with no webapp change. Resting the slider
at 1.0 on an empty number keeps EDT-27's rule (empty means the engine's default) visible
without storing a value the author never set.

**Alternatives.**

- Slider only. Precise values become impossible.
- A styled slider component from the UI library. The native range is reachable, keyboard-
  operable, and restyled in plain CSS — the pair is two inputs, not a design-system moment.

**Consequences.** The form's threshold row is the only side-by-side pair, so the drawer's
spacing rule needed to reach across the quality component's boundary (the `+` sibling rule
in the drawer's styles). Storybook and unit tests cover both drag and type paths.

### DD-482. A rule's page is a layout row with a Fields box

- **Status:** Proposed
- **Increment:** 7.27
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** `m4i_data_quality` gets a row in the details layout table (DET-38): a Fields
card section seeded from the rule's `fields` relationship end, with the usual stat and
side-nav entry, riding the same generic box machinery every DET-17 box uses. The rest of the
page is the default anatomy (description box, properties accordion).

**Reason.** A rule is defined by the fields it checks, and every other page already answers
"what does this relate to?" with a box (DET-17). Showing a rule without its fields asks the
user to open the editor to learn what the rule covers. The layout table is exactly the seam
for this (DD-359's design): adding a type's page is adding a row, no new component.

**Alternatives.**

- No row (the generic fallback page). The rule page then shows properties only, and the
  fields — the rule's whole point — are hidden inside one attribute cell.

**Consequences.** The section-config table tests gain the ninth row. The box inherits every
box behaviour (search, sort, paging, the read gate) for free, and the rule→field edge the
editor writes (EDT-26's save body carries `fields`) is the same edge the field page's rules
box (DET-35) reads from the other side.

### DD-483. Rules enter through the generic doors (DET-37 withdrawn)

- **Status:** Proposed
- **Increment:** 7.27
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** There is no box-scoped create `+` on the field's rules box (the earlier DET-37
is withdrawn before merge, on review). A rule is created through the generic create door —
the hero `+` and its type picker, with `Data Quality` as one of the selectable types — and
edited through the pencil on the rule's own details page, exactly like every other entity.
The `dqField` prefill query parameters, the box-header action, and the card-section header
slot it used are removed with it.

**Reason.** Review call on this PR: "rules are just different types of entities after all."
A second create door for one type forks the write path (two routes to prove, two prefill
shapes to keep honest) for a shortcut the generic door already covers in one extra pick.
The drawer's create route (DD-330's) is per-type and uniform; the box stays a pure reader,
which is what every other box is.

**Alternatives.**

- The box `+` with the field prefill (DET-37 as first specced). Kept as the recorded
  alternative: it saves one select and one picker-add on the create path, and costs a
  type-unique door, a prefill contract, and a slot in a dumb UI component.

**Consequences.** The e2e creates its rule through the generic door and picks the field in
the relationship picker by hand. If a future increment re-proposes a shortcut, it supersedes
this entry rather than re-adding the button.
