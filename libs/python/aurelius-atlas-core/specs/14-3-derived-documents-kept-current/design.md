# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-518. A changed entity keeps its document, marked stale, until the indexer replaces it

- **Status:** Proposed
- **Increment:** 14.3
- **Date:** 2026-11-12
- **Supersedes:** DD-499, in part: the write marks the document stale instead of dropping it

**Decision.** A write whose entity no longer has the hash of its document keeps the document and sets its
`stale` flag. The indexer lists stale documents beside the missing ones. It writes the entity's new document,
or none, only after the documents the change affects.

**Reason.** The stale document is the one trace of what the entity was. It holds the name and the neighbours
that other documents knew it by. A deleted entity would otherwise leave nothing to list: it has no document
to derive, and the documents that name it would keep naming it. The flag is set where every change passes,
as DD-499 checked the hash there. Until the affected documents are written, the cause stays listed, so a
crash in between repeats the work instead of losing it.

**Alternatives.**

- Dropping the document, as 14.2 does: a deleted entity's neighbours are never found.
- A queue of changes beside the entities: a second store that a write must reach, or lose the change.

**Consequences.** A stale document still holds the old fields until the next round; 14.4 decides whether a
search shows them.

### DD-519. The indexer derives the affected documents again in the same round

- **Status:** Proposed
- **Increment:** 14.3
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** For each entity of a page whose document goes, or whose name, breadcrumb or relation GUIDs
change, the indexer finds the documents that name it with a terms query on the GUID fields. It adds the
entities that its old and new documents name. It derives each of them again from the catalogue the page reads,
and keeps those that differ from what is stored. An affected document whose own name, breadcrumb or relation
GUIDs changed affects others in turn, until none does. A changed definition or email affects no one.

**Reason.** DD-486 states the documents over the catalogue's state, so an affected document is one that
derives differently, and deriving it is the check. Following only identity changes stops the walk where it
must stop. A rename changes the relation names at the other ends, but not their GUIDs, so the walk ends one
hop away. A join (LAS-06) is two hops: an attribute's new field changes the attribute's relation GUIDs, which
reaches its data entity. Breadcrumbs list every entity above, so the documents below a renamed or deleted
entity name it themselves and are found at once.

**Alternatives.**

- Marking the affected documents stale for later rounds: each is written twice, and a chain of joins needs a
  round per hop.
- Atlas tasks: `admin/tasks` would list them, and ASD-05 keeps the documents out of Atlas's API.
- Patching names in place, as the legacy handlers did: DD-486 rejects the order dependence.

**Consequences.** Renaming an entity high in a breadcrumb, such as a domain, derives every document below it
in one round.

### DD-520. A relationship records the state its ends' documents saw

- **Status:** Proposed
- **Increment:** 14.3
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** A stored relationship has `appSearchState`, written by the indexer only. A relationship whose
state is `DELETED` while its record is not, or `ACTIVE` while its record is `DELETED`, is listed. The indexer
derives its ends' documents again, as in DD-519, then writes the state into the record.

**Reason.** A soft delete leaves the relationship listed at both ends, as Atlas keeps the edge (DD-061). The
ends' hashes do not change and nothing marks them. This covers `DELETE /relationship/guid`, an update that
drops a relationship attribute, and an entity's delete. The writers stay as they are, and the listing finds the
relationships soft-deleted before 14.3 too. A created relationship and a removed one change the ends' lists,
so DD-518 covers them.

**Alternatives.**

- Touching the ends at each soft delete: three writers, each reading and writing two more entities per
  relationship.
- Polling for relationships updated since a time: the time must be kept, and the servers' clocks must agree.

**Consequences.** Each soft delete costs the indexer one more write, of the relationship.

### DD-521. Every server process runs the indexer, on by default

- **Status:** Proposed
- **Increment:** 14.3
- **Date:** 2026-11-12
- **Supersedes:** none

**Decision.** The server starts an App Search worker as it starts the embedding one (DD-436). It runs a round
at start and then every ten seconds, unless `AURELIUS_ATLAS_SERVER_APP_SEARCH_ENABLED` is false. A failed round
is logged, and the next tries again.

**Reason.** LAS-10 wants no operator's step. The documents need nothing outside the store, unlike the
embeddings' model, so there is nothing to configure. The writes are conditional, so two processes in one round
lose work, never documents.

**Alternatives.**

- One elected process: a lease to keep, for work that conditional writes already make safe.
- Off by default: a catalogue whose documents go stale unless an operator asks.

**Consequences.** An installation that does not use the original webapp's search pays for the rounds. The
setting turns them off.

### DD-676. A write wakes the App Search indexer; the poll stays as the floor

- **Status:** Proposed
- **Increment:** 14.3 (a change, 2026-11-17)
- **Date:** 2026-11-17
- **Supersedes:** DD-521's pace of a round every poll interval; the rest of DD-521 stands

**Decision.** The entity store calls its write listeners after every committed write, and each store set's App
Search worker is one of them. Woken, the worker waits the settle time, 0.5 seconds by default
(`AURELIUS_ATLAS_SERVER_APP_SEARCH_SETTLE_SECONDS`), then runs a round. It clears the wake before each round,
so a write during a round brings the next one as soon as it ends. Without a wake it still runs a round every
poll interval, 10 seconds by default.

**Reason.** A breadcrumb, a derived relation or a quality total trailed its change by up to the poll interval,
so a person who renamed a domain or moved a dataset saw the old path for up to ten seconds. Waking on the
write derives it within about the settle time. When many entities change, as in an import, the writes keep
the worker awake, and it derives them in its pages of 100 back to back, not one page per poll. The settle
gathers a burst of single writes into one round instead of one round each.

**Alternatives.**

- A shorter poll: rounds and store reads every second on an idle catalogue, and still a second of delay.
- Deriving the documents inside the write: every write pays for the breadcrumbs and relations it affects, and
  a failure there would fail the write; the worker keeps both apart (DD-521).
- A queue of changed GUIDs: the store already lists the stale documents, so a wake is enough.

**Consequences.** A write wakes only its own process's worker; writes through another server process reach
it at its next poll. A recovered write (ENS-07) also waits for the poll. On a busy catalogue the worker runs
almost continuously, bounded by its page size.

### DD-678. A writing request answers once its App Search documents are derived

- **Status:** Proposed
- **Increment:** 14.3 (a change, 2026-11-18)
- **Date:** 2026-11-18
- **Supersedes:** DD-521's "no request waits for a round"; DD-676 stands

**Decision.** A write made while the server answers a request registers the store set's App Search worker for
that request, besides waking it. A middleware around the routers holds the answer's last body part until each
registered worker has run a round of its documents and governance verdicts, at most
`AURELIUS_ATLAS_SERVER_APP_SEARCH_ANSWER_SECONDS`, 5 seconds by default. A round still running then goes on in
the background and the answer leaves. Rounds run one at a time, so a request's round follows the background
round under way rather than racing it. A request that wrote nothing passes unchanged; writes outside a
request, as a task's, only wake the worker (DD-676). The data quality stays with the background rounds: the
request's write woke the worker, so its full round, quality included, follows the answer.

**Reason.** The details page reads the breadcrumb from the entity's stored App Search document (AVS-02) and
reloads it right after a save. Woken in the background, the worker still trailed that reload by its settle and
its round, so adding a domain to a data entity showed the old trail. Deriving before the answer makes the
reload read the new one. The round is the same one the worker runs, so the request derives every document the
change affects, the children's breadcrumbs included, with the indexer's checks (ASU-03 to ASU-05).

**Alternatives.**

- Waking the worker only (DD-676): the page reloads before the round ends.
- The webapp waits and reloads again: every client would need it, and how long to wait is a guess.
- The data quality in the request's round too: a save waits for every quality rule's results and totals,
  which the page doesn't reload with.
- Deriving inside the entity store's write: every write, the background ones included, would pay for it, and
  its failure would fail the write.

**Consequences.** A save answers after its documents and verdicts; the data quality results and totals follow
a moment later in the background, as a batch. A large import answers after the limit and its documents follow
in the background. A failed round doesn't fail the request; it is logged and the next round tries again.
