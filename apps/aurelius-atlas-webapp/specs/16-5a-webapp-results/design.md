# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-599. The aggregator's two extra facets move into the search door

- **Status:** Proposed
- **Increment:** 16.5a
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The search door answers two facet names that are not card fields (VSR-01): `owner`, a
`terms` aggregation of `Asset`'s owner attribute through the registry, and `serviceType`, computed
in `ViewSearchEngine` from the answered `typeName` counts by adding them up per service type, as
DD-093's `ServiceTypeAggregator` does. Both are empty where the registry holds nothing for them,
as `SearchAggregator` answers today. The aggregator itself stays for quick search and the 11.4
endpoint (VSR-10).

**Reason.** The results page's sidebar needs the four facets, and ADR 064 says the facet machinery
over the derived documents "moves to the family's search door without the wire's query language
and answer wrapping." A roll-up from the cards' fields cannot count the population: the cards are
one page (10) or a kNN window, while `ServiceType` and `owner` count every matched entity. A
second call to quick search for the sidebar would keep the page on two sources that can disagree
between calls, which is the product goal ADR 064 states against.

**Alternatives.**

- The client rolls `serviceType` up from the `typeName` facet: it cannot; the type facet is one
  facet of one request and the roll-up needs every matched type counted, which the door has and
  the client does not.
- The door grows an attribute-addressed facet grammar (`filters`-style paths to any attribute's
  search field): more surface than one named field needs; `owner` is a single known attribute of
  one known type, and `serviceType` is not an attribute at all.

**Consequences.** The door's field table gains one entry, and `ViewSearchEngine` gains a small
post-pass for `serviceType`. The two names are the door's only non-card facet names, and the spec
names both, so there is no open-ended grammar to keep honest. `SearchAggregator` retires with the
wire's last consumer (16.6).

### DD-600. The type filter composes `typeName` with `superTypeNames`; the marker dies

- **Status:** Proposed
- **Increment:** 16.5a
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** A selected type filters as `filters: {any: [{typeName: names}, {superTypeNames:
names}]}` (VSR-04): an entity of a selected type or of any type under one. An empty query with no
selection sends no filter, which answers every active entity (AVR-11). The comma-joined
`typeName`, `includeSubTypes`, and the `_ALL_ENTITY_TYPES` marker leave the results path with the
quick-search request they belonged to.

**Reason.** Quick search expands a type to its sub types server-side (`includeSubTypes`); the door
takes declarative per-field clauses (AVR-03). The stored document already holds the whole super
chain in `superTypeNames` (AVS-01), so the door needs no new machinery: a term over the chain
field is the subtype filter. The client holds no typedefs on the results page and must not fetch
them to expand the chain itself. The marker only existed because quick search refuses an empty
query without a type (QSR-01); the door answers an empty query with everything (AVR-04), so the
bare URL answers without a stand-in type.

**Alternatives.**

- The door learns an `includeSubTypes`-style flag on the type filter: a wire-shaped parameter on a
  redesigned contract, which 16.2 set out to leave behind (its deviation clause names exactly this).
- The client expands each selected type to its sub types and sends the list under `typeName`: a
  typedef walk per browse landing, on the one screen 7.x kept free of typedef calls.

**Consequences.** The composition is one clause the store builds from the selection signal; the
facets and counts need no special case because filters apply before counting (AVR-05). A type
name a registry does not know filters as the term it is and answers nothing, the door's unchanged
behavior for a value that matches no document.

### DD-601. `atlas-view.ts` mirrors `views.py` by hand, as the other DTO clusters do

- **Status:** Proposed
- **Increment:** 16.5a
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `libs/angular/aurelius-atlas-data-access` gains `src/lib/atlas/atlas-view.ts`: the
camelCase interfaces `EntityCard`, `EntityView`, `CardBreadcrumb`, `CardQuality`, `EntityRelation`
and `RelationEntity`, mirroring `aurelius_atlas_model/views.py` field for field, plus the door's
request and answer types (`ViewSearchRequest` with the `mode` of ASV-01, `ViewSearchAnswer` of
`{cards, facets, total}`). `ViewSearchService` (in `src/lib/aurelius/`) speaks one method, `search`,
on `POST {API_BASE_URL}/aurelius/v1/search`. Both files are re-exported from the package root.

**Reason.** AVS-07 makes `views.py` the one definition of the fields and names the webapp's
mirrored models as its readers; the lib's posture (DD-187's line) is hand-mirrored DTOs with the
server's camelCase wire names, one cluster per contract. A generator over the server's OpenAPI
would answer a different shape than the doors answer: the doors are Aurelius-native routes whose
documents (`models.py`) exist to document the shape, not to generate a client, and no other
cluster in the lib is generated.

**Alternatives.**

- OpenAPI codegen for the Aurelius prefix: one generated cluster among twenty hand-mirrored ones
  is two conventions to keep, and the generated types would not match the naming the screens use.
- Reusing `AtlasEntityHeader` and `AtlasQuickSearchResult` for the door's answer: the card is not a
  header (AVS: breadcrumb, relations, quality and stale on it; no `attributes` bag), and reusing
  the wire's wrapping is what ADR 064's exit path removes.

**Consequences.** 16.5b and 16.5c read their screens from the same cluster, so the mirror is
written once for the family. A field added in `views.py` needs its mirror added in the same PR,
as the other clusters already require.

### DD-602. The results store asks one door for all three modes

- **Status:** Proposed
- **Increment:** 16.5a
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The results store always calls `ViewSearchService.search` (VSR-03): the stored mode
names the request's `mode` key (`words` becomes `keyword`), and the store's two old clients,
`SearchService.quickSearch` and `SearchByMeaningService.search`, leave the results path. The
door's `total` is the header's count in the keyword mode; the meaning mode keeps SBW-04's
shown-count and window rules (VSR-05), and SBW-06's fallback keys on the same answer,
`AURELIUS-404-00-001` (VSR-08).

**Reason.** Two endpoints chosen by a keystroke of the mode setting is the arrangement 11.5 built
and 11.5b narrowed; the door's `mode` key (DD-595) moves the choice into the body, where the door
refuses and logs it. The fallback detection survives unchanged because 16.4 gave the door SBM-06's
errors (ASV-09), so the store's error path keeps one shape for both old causes.

**Alternatives.**

- The door for Words, 11.4's route for the meaning modes: the screen keeps two answer shapes and
  two error paths to keep in step, and 11.4's route is the wire's answer wrapping, the thing the
  family exists to replace.
- A mode control on the results page: SBX-03 removed the hero's switch deliberately (the choice is
  stored and applies everywhere); the roadmap's "mode switch" is the settings control choosing the
  door's key, which is this decision.

**Consequences.** The results path holds one request shape and one error path. 11.4's endpoint and
quick search answer their other callers unchanged (VSR-10), and retire on their own schedules.

### DD-603. The sidebar's facet keys become the door's field names, titles unchanged

- **Status:** Proposed
- **Increment:** 16.5a
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The sidebar keys rename to the door's facet names: `__typeName` becomes `typeName`,
`__state` becomes `status`, `Asset.owner` becomes `owner`, and `ServiceType` becomes
`serviceType` (VSR-06). The `FACET_TITLES` map carries the same four localised titles on the new
keys, and no i18n key is added or removed. The type facet asks the door at 100 values, DD-093's
facet size, inside the door's own bound of 250 (AVR-05); the seen-value merge (DD-426) keeps its
rule unchanged on the plain `{value, count}` entries.

**Reason.** A translating layer between the door's answer and the sidebar would keep the legacy
`__`-keys alive as private names for a screen that no longer calls that wire; the titles are the
only legacy-visible part, and they sit in one map the screen owns. The 100-size ask keeps the
sidebar's type list as wide as quick search answered it, so a catalogue of many types shows no
narrower a menu than before.

**Alternatives.**

- Keep the legacy keys as the sidebar's internal names and translate the door's answer: a mapping
  with one consumer, and the next screen (16.5b) would inherit the same translation for its facets.
- Ask every facet at 100: the door's default of 10 fits the three narrow facets, and asking wide
  for all four buys nothing the answer carries.

**Consequences.** The four titles travel unchanged through the DD-128 bridge (no catalogue edit),
and `i18n-completeness` stays green. The merge rule reads the door's entries directly because the
door's facet entries are `{value, count}` with no `{raw}`-style wrapper (16.2's deviation clause).
