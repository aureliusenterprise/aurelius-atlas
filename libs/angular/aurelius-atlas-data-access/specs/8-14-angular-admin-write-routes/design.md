# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) apply:
an accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-315. The export answer is a typed `{ body, contentType }` pair

- **Status:** Proposed
- **Increment:** 8.14
- **Date:** 2026-11-02

**Decision.** `AdminService.export` is typed
`Observable<AtlasExportAnswer>` with
`AtlasExportAnswer = { body: ArrayBuffer | null; contentType: string }`, built
with `observe: "response"` off and the header read from a full-response read of
`responseType: "arraybuffer"`: the ZIP bytes ride in `body`, the `Content-Type`
header in `contentType`. The server's 204 (an empty export asked to omit its
ZIP, EXP-05) answers `{ body: null, contentType: "" }`.

**Reason.** The Python twin returns the pair as a `(bytes, content-type)`
tuple (CLW-03, DD-310): the caller hands the bytes to a download and needs the
type the server picked to label it. An `Observable` has one value channel, so
the pair has to be a value. Dropping the header would strand every caller on a
guessed MIME type — the same loss DD-314 refused for the saved-searches 204,
where folding a distinguishable server answer into a common one loses
information silently. Returning `Observable<HttpResponse<ArrayBuffer>>`
instead would tax every call site with `.body`/`.headers` plumbing for one
method; the named pair keeps the lib's convention that a method answers a body
(APC-02) while carrying both facts. `null` for the 204 follows ACS-03's
established shape for "the server answered success with nothing".

**Alternatives.** (a) Return the `ArrayBuffer` alone and hard-code
`application/zip` at the call site (refused — the content type is a wire fact
the server owns; the Python twin reads it from the header rather than guess it
(D-310's shape), and a client that hard-codes it breaks the day the server
answers another type).
(b) Return `HttpResponse<ArrayBuffer>` (refused — breaks APC-02's body-only
shape, the same refusal as DD-314's option b). (c) Return only the ZIP and
throw on 204 (refused — 204 is a success code; EXP-05's omit-ZIP answer is a
legitimate outcome the Python twin returns as `b""`).

**Consequences:** AAC-04's spec types the pair and its Vitest names the
`{ body: null, contentType: "" }` answer; the pair with CLW-03 is documented
in both AGENTS.md files as `(bytes, content-type)` ↔ `AtlasExportAnswer`, not
as an exact match; the download-to-disk screen (a later increment) consumes
`body` through `new Blob([body], { type: contentType })`.
