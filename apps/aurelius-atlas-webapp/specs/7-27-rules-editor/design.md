# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply:
an accepted entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-475. The quality form is a mode of the one drawer, not a second editor

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

### DD-476. The form's fields come from the served vocabulary, not the typedefs

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
(DD-473) and every `+` in the app opens the same form.

**Alternatives.**

- One control per `dq` attribute with a kind-dependent disable: still twelve controls on screen,
  and the "which ones are live" table lives in the browser — the mirror DD-473 closed.
- The Angular signals-schema path the generic form uses (DD-354): the schema wants a static
  shape, and the quality form's shape changes with the kind, so the branch holds explicit
  `Field`s over a values record — the pattern EDT-15's picker values already use.

**Consequences.** A kind added to the engine appears in the form with no webapp change (the
parameter names map through EDT-26's table; a name outside it renders as text). The webapp's
dependency on the server's vocabulary is the same release's (as DD-473's consequence says), so
no version skew needs handling.

### DD-477. A rule saves unchecked only when the quality form does not own it

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
