# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted entry
is never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-589. The door takes desired sets and diffs them server-side

- **Status:** Proposed
- **Increment:** 16.3
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** A request's `classifications`, `labels`, `meanings` and `sections` are the whole
desired set. The server reads the entity's current own tags, labels, term assignments and section
edges, computes the add/remove difference, and applies it through the internals of 3.3a, 5.3a,
5.2c and 3.1a. The client sends no delta and no ordered call sequence.

**Reason.** DD-326's client diff exists because the Atlas replace route "cannot attach a new tag
or detach one, live-probed" — a limitation of one endpoint, not of the server's internals, which
add and remove fine. Moved server-side, the diff has the entity's current state as it reads it,
without the client's risk of a stale seed (7.7a's `ownClassifications` filter, DD-326) and with
propagated tags safe by construction (AVW-08).

**Alternatives.**

- Keep the client diff and proxy the Atlas endpoints: the four-call save and its half-apply
  window stay, which is the failure ADR 064 R8 bans.
- A JSON-Patch body: a patch language to design, spec and test, for sets a replace already says.

**Consequences.** One save is one request (AVR-13's client story ends); AVW-08's rule is the
server's, tested once. The Atlas sub-resource endpoints stay for third parties (AVW-12).

### DD-590. The whole apply is one transaction of the application

- **Status:** Proposed
- **Increment:** 16.3
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The steps of AVW-05 (attributes, then each set's adds and removes) run so that a
failed step undoes the steps before it, and the request answers its refusal having applied
nothing. The store has no transactions (ADR 047), so the door records each step's before-image
as it applies and rewinds them in reverse order on a failure, answering the refusal.

**Reason.** ADR 047 names the store's gap and makes such places application concerns, each
recorded: this is the record. The client sequence this replaces can half-apply (a save that sets
attributes then loses a tag DELETE to a network failure — 7.19's editor-failing-save paths); the
door must not inherit that. A rewind of recorded before-images fits the store's conditional
writes, where a two-phase prepare across indices does not.

**Alternatives.**

- Apply in a fixed safe order and accept partial success: the half-apply window the door exists
  to close.
- Staging the change in a shadow key with a swap: a second write path per entity to design and
  test, against a rewind that reuses the store's versioned writes.

**Consequences.** The rewind is tested on the fake store at each step (AVW-05's acceptance). A
crash mid-apply (the process dies, not a step fails) can still half-apply, as today's sequence
does; the door improves the window, not the guarantee, and the spec says so rather than claiming
atomicity the store cannot give.

### DD-591. Optimistic versioning by updateTime, with the stored view on conflict

- **Status:** Proposed
- **Increment:** 16.3
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** An update carries the `updateTime` of the view it edited. The door compares it to
the stored one under the store's conditional write (ENS's optimistic versioning); a mismatch
answers 409 with the stored view. A create ignores the field.

**Reason.** The client's edit began at one view; the door must answer "someone changed this
since." `updateTime` is in the shape already (AVS-01) and is what the person's screen showed, so
no new token to fetch or remember. Answering with the stored view gives the editor the real
material for a merge or reload, which a bare 409 does not.

**Alternatives.**

- Last-write-wins, as the Atlas sequence effectively is: the silent overwrite today's save can
  cause when two stewards edit one dataset.
- ETag/If-Match: an HTTP-header dance the retry interceptor (7.26) and the proxies pass through
  unchanged; the body field works with everything the client already has and reads the same in
  the 16.5 client cache.

**Consequences.** The editor must send the field; 16.5 wires it. A conflict is a normal answer
the UI must show (a reload-and-reedit path), recorded as such in 16.5's spec, not an error page.

### DD-592. The client keeps inventing the qualified name; the GUID stays the server's

- **Status:** Proposed
- **Increment:** 16.3
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** A create carries the qualified name the editor generated (DD-325 keeps) and no
GUID; the server assigns the GUID and answers it (AVW-06). The `guidAssignments` map of 2.4 has
no twin in this door: one entity per request, so one GUID in the answer.

**Reason.** DD-325's reason stands (the name is part of the person's edit and of the unique-key
check, not server-inventable mid-form). The temp-GUID dance exists only because 2.4's response
carries headers keyed by the temp value; a view answer names the real GUID directly, so the
remap mechanism retires with the response shape that needed it.

**Alternatives.**

- Server-invented qualified names: every m4i screen's naming rule moves to the server with no
  owner (the editor's rule is the product's, DV-84's naming lines).
- Client-chosen GUIDs: the GUID space is the store's (ENS-02's reason), and a clash is a person's
  accident, not a merge input.

**Consequences.** A qualified-name clash is one refusal (AVW-06) instead of 2.4's create-update
ambiguity; the editor shows it as a name-taken message (16.5).

### DD-593. The editor's type slice is one endpoint, cached by type

- **Status:** Proposed
- **Increment:** 16.3
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** `GET /types/for-type/{name}` answers the type plus its supertype chain with the
attributes each declares (AVW-11). It is the editor's only type call; the whole-document
`GET /types/typedefs` stays untouched for third parties.

**Reason.** EDT-04's drawer pulls the entire typedefs document (every type in the store) to
render one form, the single largest payload in the webapp's day. The chain for one type is what
`typeLineage` walks today (editor-state's supertype chain) plus the layout walk of 7.21a, one
small read instead of a walk or a full dump. Caching by type name belongs to the client cache
record (16.5), which AVW-11's stable response makes safe.

**Alternatives.**

- Keep the full-typedefs call: correctness by size, paid on every drawer open, and it grows with
  the corpus.
- A filtered `GET /typedefs?name=X`: Atlas's filtered list answers a container of matching defs,
  without the closure, so the client still walks — half the door.

**Consequences.** One more read path to authorization-check as TYPE_READ-filtered is avoided (the
def is one type; 6.2a's check is the same call 2.3's header read makes). A form built from the
slice must render inherited attributes exactly as the walk did; 7.7a's spec rows (EDT-04..07)
re-run against it in 16.5.

### DD-594. The write's answer is fresh by the write itself: `stale` false

- **Status:** Proposed
- **Increment:** 16.3
- **Date:** 2026-11-14
- **Supersedes:** none

**Decision.** The door derives the answer from the state its request just wrote and answers
`stale` false (AVW-07), whatever the stored document says at that moment. The read door keeps
AVS-06's derivation; only the mutation door overrides the one field.

**Reason.** AVS-06's staleness tells a reader its card may lag a write the derived document has
not caught up with. The mutation door's caller is that write: its own apply just stored the
entity, so no write of its own can be the lag it would be warned about, and an editor told to
re-read after its own save is a loop with no exit. The rest of the view stays the derivation's,
so the answer equals the read door's for every other field (AVW-07's equality).

**Alternatives.**

- Keep the derivation's `stale`: the answer to a save says "this may be behind your save",
  which is false for the saver and pushes a re-read onto every write's happy path.
- Wait for the derived document before answering: the door takes the search pipeline's timing
  into the write's latency (ADR 047 keeps them apart).

**Consequences.** One field differs between the two doors by design, in the caller's favour and
recorded here; 16.5's editor trusts the answer and re-reads only on the 409. If a future
increment makes the derived document part of the write, this entry is superseded and the
override goes away.
