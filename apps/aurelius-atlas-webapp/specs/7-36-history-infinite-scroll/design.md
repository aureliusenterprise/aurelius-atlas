# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-820. The trail pages itself from its newest key

- **Status:** Proposed
- **Increment:** 7.36
- **Date:** 2026-11-22

**Decision.** The History pane loads the entity's audit trail one page at a
time, driven by the results list's `InfiniteScrollContainer`. The pane owns
three signals on top of the list it already had: whether a page is in flight,
whether the trail is ended, and the oldest `eventKey` it holds. The first read
sends `count=100` and no cursor. Each next read sends the same `count` and
`startKey` of that oldest key, appends the answer, and drops any event whose
`eventKey` it already lists — the server's cursor is inclusive (AUD-08). A page
shorter than 100 ends the trail. The pane sends no `offset` and no `sortBy`.

**Reason.** The legacy service walked the trail to its end, so a reader who
scrolled far enough saw every event (DV-190 measured how far this app's
newest-100 cap left them). The container already in the UI library supplies the
sentinel, the spinner and the load button (UIC-21, UIC-22) and jsdom falls back
to the button, so the tests drive it without an observer. The key cursor is the
only paging the endpoint offers that keeps the newest-first order: `offset`
turns the server onto its sorted path (AUD-07), which would flip the list, and
an offset-based walk also shifts under a writer that adds events mid-scroll.
`eventKey` is unique per stored event — the listener builds it from the guid,
the timestamp, the position in the batch and a second clock read (AUD-05) — so
it is safe as both the cursor and the `@for` track key. The inclusive repeat is
dropped client-side rather than asked away, because the server's rule is
Atlas's own and Aurelius Atlas must not bend it for one screen.

**Alternatives.** A "Load more" button in the pane's foot: refused, the
container is the product's one paging pattern and the foot belongs to the form
tab (HST-07). The `offset` walk the legacy used: refused, it answers oldest
first (AUD-07) and shifts while the entity is edited. A server-side "has more"
flag on the response: refused, the endpoint answers a bare array as Atlas's
does, and the short-page rule already ends the trail; a trail that ends on an
exact multiple of the page size shows one dead sentinel ask, which costs one
read and no data. Keeping the newest-100 cap: refused, it is the reported gap.
