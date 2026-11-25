# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the
design log apply: an accepted entry is never edited except its status line, and
a changed decision is a new entry that supersedes the old one.

## DD-883. Shared chrome labels are module constants, not a service and not per-screen members

- **Status:** Proposed
- **Increment:** 7.56
- **Date:** 2026-11-25
- **Supersedes:** –

**Decision.** The four chrome strings that two or three `search` screens pass to
the same ui parts (`LOAD_NEXT_PAGE`, `FACET_SHOW_MORE`, `FACET_SHOW_LESS`,
`FILTER_NOT_AVAILABLE`) live in `search/shared/labels.ts` as exported module
constants, each holding the `$localize` expression with the id it already had. The
screens keep a member per label that reads the constant, and their templates bind
the member as before. Only strings with two or more users moved; the details
screen's single-use chrome copy and its screen-private strings stayed as members.

**Why.** The ui library's parts take their copy from the caller (UIC-21, UIC-34,
VCF-10, and DD-136 states that rule for the facet list explicitly), so the
strings must live in the app, not in the library — but the four that several
screens pass to the _same_ part are one literal written two or three times, and
the next-page label had drifted to three owners. Putting them in `shared/` is
DD-869's own rule: code two features need lives in a shared layer. Module
constants, not a service, because a label is fixed copy and owns no value — a
service here would add an injection token and a provider for four strings that
never change, and SPL-10's standard for the settings facade is exactly that a
surface should own no state it does not need. The screens keep their members so
the diff stays small and the templates are untouched: the member is the seam the
template knows, and rewriting 30 template bindings to import a constant directly
would churn every `.html` in `search/` for no behaviour change. The line for what
moves is drawn at actual use, not at category: `peopleEmpty` looks like chrome
copy but one screen prints it, so hoisting it would make `shared/` a place where
single-use strings go to look tidy.

**Alternatives considered.** _A `ChromeLabelsService` (or extending
`SettingsService`)._ The plan's target shape keeps stores free of presentation,
and this is pure presentation copy; a service adds injection to three components
and a provider to test harnesses for values that are constant at build time.
_$localize directly in each template again._ The labels became TypeScript members
because they feed component inputs, not element text (BRW-02), and the templates
are unchanged in this increment by intent. _Hoist all of the details screen's
chrome copy._ That moves four single-use strings into a shared module — more
shared surface, no duplication removed, and it makes `shared/labels.ts` a list of
labels some of which belong to one caller (the failure mode DD-880 avoided on the
input side).
