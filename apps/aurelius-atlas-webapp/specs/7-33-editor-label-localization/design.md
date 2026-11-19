# 7.33 Design decisions

## DD-722. The editor labels every field from the catalogue

- **Status:** Proposed
- **Increment:** 7.33
- **Date:** 2026-11-19
- **Relates to:** EDT-03 (7-7a, amended in place: the label precedence), EDT-13 (7-7c, amended
  in place: the picker's attribute part), EDT-33/EDT-34 (here), SHL-08 (DD-128's dictionary
  bridge), DD-356 (the star, kept), DD-379 (the picker's target-type bracket, kept).

**Decision.** The editor builds one label map, `attributeLabels()`, of every attribute the
shipped metamodel can render, and passes it to both field builders (EDT-33/EDT-34). Each entry
is a `$localize` string under the Aurelius dictionary key
`search.components.editor.attribute.<attribute name>`, so both locales carry it and
`i18n-completeness.spec.ts` proves it. `labelOf` keeps EDT-03's precedence, and the map simply
joins the first rung: catalogue string, then `displayName`, then the name. The relationship
pickers read the same map (EDT-34), keeping DD-379's bracket. The English source text follows
the typedef `displayName` wherever that reads as words, fixes the two "Complaint" typos, and
otherwise humanizes the camelCase name with its acronyms intact (`hasPII` → "Has PII",
`clientId` → "Client ID").

**Reason.** The user asked that every editor label be a human-readable name, localized to the
locale the user reads in. The shipped metamodel cannot give that: the m4i dictionary leaves
three attributes without any displayName, repeats the raw name as the displayName of four more,
and the vendored Area0 base model names no attribute at all — it is byte-pinned, so it can never
carry one. Relationship attributes name nothing. The legacy dashboard solved this in the same
place Aurelius already has the machinery: its catalogue carried a string per attribute, resolved
before the typedef. Aurelius already translates every other string on the editor through the
SHL-08 bridge, and the extractor plus the completeness spec make a missing key fail the build.

**Alternatives.**

- **Fix the typedefs instead.** Edit the m4i dictionary's displayNames. It fixes eight names and
  none of the base-model attributes (vendored, untouchable), none of the 55 relationship names,
  and no locale — `displayName` is one English string. It also forces the three sample bundles
  and MDD-02's pin to move for a screen-only concern.
- **Humanize the raw name in the webapp.** A pure function turns `processOwner` into "Process
  Owner" for any name, with no catalogue. It is locale-blind — the user asked for translated
  labels — and its guesses ("Exec Time", "Params") are worse than curated words. The map's
  English source text is humanized text, curated once, so the idea survives inside this choice.
- **Translate at runtime over the store's strings.** The server would send a key and the webapp
  resolve it. The catalogue bridge is compile-time `$localize` with no runtime lookup anywhere in
  the app, and inventing one service for labels breaks SHL-08's "the catalogue is the reference".

## DD-723. A catalogue name the metamodel carries without a key keeps today's label

- **Status:** Proposed
- **Increment:** 7.33
- **Date:** 2026-11-19
- **Relates to:** EDT-33/EDT-34 (here), DD-722 (the map), DD-323 (one def-driven form),
  DD-379 (the target bracket shows the type display name).

**Decision.** The map covers the names the shipped metamodel renders. An attribute an admin
installs later has no key, and its label falls through to the `displayName`, else the raw name —
EDT-03 and EDT-13 unchanged for it. No humanizer runs on it.

**Reason.** An installed type is data, not this increment's scope. The raw name is what shipped
before, and it is what Apache Atlas itself shows; guessing words out of `snake_case` names like
`ozone_bucket`'s `volume` invents a label the author never wrote. The raw path stays proven by
the e2e, which asserts an installed relationship's bare name (DD-724 removes the bracket).

**Alternatives.**

- **Humanize any unknown name.** A label the author never chose, in no locale, shown for data an
  author did choose the name of. It also changes what an admin sees in a type they installed
  with their own displayName-less choices, with no translation possible.
- **Fail the editor for an unknown name.** An installed type is normal; the editor must keep
  working for it.

---

## DD-724. The relationship picker's label drops the target-type bracket

**Date:** 2026-07-29
**Status:** Accepted
**Context:** Relates to EDT-34 (here), EDT-13 (7-7c), DD-379, DD-341, DD-722
**Increments:** 7-33 (amends 7-7c)

**Decision.** A relationship picker's field label is the catalogue string, else the
`displayName`, else the name — with no `(Target Type)` bracket appended (DD-724). The target
type stays visible where it always was: each chosen chip leads with it (DD-341, DD-379), and
the picker's search is scoped to it. This amends EDT-13's "with the target type in brackets"
clause in place; the create picker (EDT-14) and the chip lead are unchanged.

**Reason.** The bracket repeated what the chips already say one line below the label, so a
picker that already reads `model: [Model · orders-prod]` said "Model" twice. The legacy
dashboard's relationship labels are the catalogue string alone — it had no bracket at all — so
removing it moves toward parity rather than away from it. The bracket came in with 7.21a (DD-379)
to carry the translated target type before the catalogue label existed; now that every
relationship attribute on the shipped metamodel has a catalogue string (EDT-34), the label has
its own readable word and the bracket is surplus.

**Alternatives.**

- **Keep the bracket for unknown target types.** A relationship whose target type is installed
  later gets a raw name and would lose the type hint. Rejected: that hint rides the chips too,
  and keeping the bracket only for some fields would make the labels inconsistent.
- **Move the type into the label and drop the chip lead.** The chip's lead is the entity's own
  type, read from the chosen entity (DD-341); the label is built from the field definition.
  They are different values and both are wanted.
