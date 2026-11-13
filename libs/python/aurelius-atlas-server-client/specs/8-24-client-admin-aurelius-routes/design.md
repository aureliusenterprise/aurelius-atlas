# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) apply:
an accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-561. The metrics list always sends `mininfo`, and the ageout keeps its 204

- **Status:** Proposed
- **Increment:** 8.24
- **Date:** 2026-11-13

**Decision.** `AdminApi.metrics_stats` sends the `mininfo` query parameter on
every call, `true` or `false`. It is the only flag of the client that always
travels. `AdminApi.ageout_audits` returns `None` for the 204 of an aging that
queued nothing, and the list of tasks for any 200.

**Reason.** `routes/admin.py` reads `mininfo` with a `FlagParam` whose default is
`true` — the one parameter of the server whose Java default is not false. The
client's `_present` helper leaves false flags and zero pages out, because an
absent flag reads as its default false (the CL-13 convention); applied to
`mininfo`, a caller's `min_info=False` would leave the parameter out and the
route would answer the full statistics, the opposite of what was asked. The
ageout answers 204 when its service queues no task (AGE-03). The task list of a
criteria that matched nothing but queued nothing is that 204, so `None` (nothing
queued) and `[]` (the server never answers an empty 200 today, and a future one
would still mean "matched, queued nothing") stay apart — CSD-03's rule for the
saved-searches read, taken up again for the same reason.

**Alternatives.** (a) `_present`-render `mininfo` like every other flag (refused
— it inverts the meaning of `False` for the one default-true parameter).
(b) A client-side `min_info: bool | None` that sends the parameter only when
given (refused — three states where the route has two; always sending one string
is one fewer shape). (c) `ageout_audits` returning `[]` for the 204 (refused —
it merges the two answers CSD-03 chose to keep apart).

**Consequences.** The CLW-08 test asserts `mininfo=true` and
`mininfo=false` both travel. The CLW-11 test asserts the 204 answers `None`. No
existing method changes.

### DD-562. The Aurelius-native shapes live in the client library

- **Status:** Proposed
- **Increment:** 8.24
- **Date:** 2026-11-13

**Decision.** The client library defines its own `SemanticSearchParameters`,
`QualityKind`, `QualityVocabulary`, and `QualityRuleCheck` in a new
`aurelius_atlas_server_client/aurelius.py`. It reuses everything the routes
share with Apache Atlas (`QuickSearchParameters`, `AtlasQuickSearchResult`) from
`aurelius-atlas-model`.

**Reason.** The four shapes are the server app's (`aurelius_atlas_server/models.py`,
their own module docstring: "not Apache Atlas shapes, so they live here"). A
client cannot import the server app — the dependency would run backwards and the
aux apps' contract rule (DD-125) forbids copying a whole app for four models.
This is the CL-12 precedent: `lineage.py` holds the client's lenient `LineageInfo`
because the strict model was the app's. The quality vocabulary and the semantic
body are small, stable, and camelCase on the wire like every `AtlasModel`, so
the models round-trip the server's own answers by alias.

**Alternatives.** (a) Parse those answers as plain dicts (refused — the client's
contract rule is that every answer arrives as a model). (b) Move the four models
down into `aurelius-atlas-model` and let the server import them (refused — the
model library is the Apache Atlas wire contract, and DD-562's four are Aurelius's
own vocabulary; moving them teaches the model library about an app). (c) Move
them up into a new shared contract package (refused — a fourth package for four
models, where one module per library is the pattern that already works).

**Consequences.** The client's `__init__` exports the four names. The webapp
already reads the same JSON as its own Angular types (12.5, 12.10), so the two
libraries state the shape each in its own language, as they do for every other
route.
