# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-026. Dynamic attributes and search lookups wait for their increments

- **Status:** Proposed
- **Increment:** 1.3
- **Date:** 2026-10-18

**Decision.** The entity type's dynamic attributes (`dynAttribute:` templates, their parsing and
evaluation order) are ported with entity writes in 2.4. The root entity type's lookup of business
attributes for search is ported with basic search in 4.1. Both resolve nothing a type definition is
checked against.

**Reason.** They are used only when entities are written or searched, and can only be tested there;
porting them now would leave them untested by any endpoint until then (as DD-025 argues for values).

**Alternatives.** Port them with the rest of `AtlasEntityType` now: a larger increment whose extra code
no rule of 1.3 can exercise.

**Consequences.** 2.4 adds the template parsing to `EntityType`; 4.1 adds the lookup to the root type.

### DD-027. Derived type sets keep first-seen order

- **Status:** Proposed
- **Increment:** 1.3
- **Date:** 2026-10-18

**Decision.** All super types are listed in the order the depth-first walk of the super types first
reaches them; sub types and relationship attributes in the order the registry resolves its types, which
is the order the definitions were added in.

**Reason.** Java keeps them in `HashSet`s and `HashMap`s, whose order Atlas does not define; first-seen
order is stable, as for the definitions' own sets (DD-021). Where the order picks a winner, as for
inherited relationship attributes, Java's winner is equally arbitrary.

**Alternatives.** Sort them by name: stable too, but unrelated to how the hierarchy was declared.

**Consequences.** `subTypes` in responses may be ordered differently from Atlas's; parity scenarios
compare them without order (DD-021, from 1.6).
