# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) apply:
an accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-314. The saved-searches 204 stays observable in the body

- **Status:** Proposed
- **Increment:** 8.13
- **Date:** 2026-11-02

**Decision.** `SearchService.getSavedSearches` is typed
`Observable<AtlasUserSavedSearch[] | null>` and maps nothing: a 200 answers the
array, and the server's 204 (no profile for that user, SVS-04) reaches the
subscriber as a `null` body. The method name and the type say the list can be
absent; the caller branches on `null`.

**Reason.** The Python twin distinguishes the two with its return value:
CSD-03's `saved_searches` returns `None` for the 204 and a list for the empty
profile, and its spec gives the distinction its own test because a caller who
reads "no profile" as "no searches" loses information silently. An
`Observable` has no separate no-answer channel — the response status is on the
`HttpResponse` object, and reading it would force every caller of this method
to pass `observe: "response"` for one quirk, or the client would swallow the
204 into `[]` and hide the difference the server keeps on purpose. Carrying it
in the body keeps the plain `.subscribe((searches) => …)` shape for the common
case while keeping both server answers observable. The sibling lib method
`AtlasEntitiesService.getEntityByGuid` already types a nullable answer the same
way (DET-03's missing entity is the error path there; the null here is a
success-path distinction, which is the difference this record exists for).

**Alternatives.** (a) Fold the 204 into `[]` (refused — the caller cannot tell
"the user has no profile" from "the user saved nothing", which CSD-03 calls a
silent wrong). (b) Return `Observable<HttpResponse<AtlasUserSavedSearch[]>>`
and branch on `status === 204` (refused — it breaks the lib's convention that
every method answers the body, APC-02, and it taxes every call site for one
rare state). (c) Throw a typed sentinel error on 204 (refused — 204 is a
success code, and `HttpStatusCode` errors are the failure channel here).

**Consequences:** ACS-03's spec types the union and its Vitest names the
`null` body; consumers that render a saved-search list branch on `null` before
iterating; the pair with CSD-03 is documented in both AGENTS.md files as
`None` ↔ `| null`, not as an exact match.
