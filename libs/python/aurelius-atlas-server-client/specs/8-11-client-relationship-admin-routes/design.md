# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../../docs/architecture/conversion/design-log.md#rules) apply:
an accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-313. The import's request part is a form field, not a file

- **Status:** Proposed
- **Increment:** 8.11
- **Date:** 2026-11-02

**Decision.** `AdminApi.import_data` sends the optional `AtlasImportRequest` as
a `multipart/form-data` **field** — a part named `request` carrying the
request's JSON as text, with no filename — next to the `data` part holding the
ZIP bytes. In `httpx` terms: `files={"data": (name, bytes), "request": (None,
json_text)}`, the `(None, value)` shape being httpx's no-filename field.

**Reason.** The server reads the part with `form.get("request")` and uses it
only when it `isinstance(text, str)` — Starlette's form gives a plain field as
`str` and a file part as an `UploadFile`, so a `request` part sent as a file is
silently read as the missing `{}`: the options the caller passed would vanish
with no error. The server's own import test posts the same shape —
`files={"data": ...}` with the request as a form field
(`tests/test__aurelius_atlas_server_import.py`, IMS-01). DD-310 says file routes
carry raw bytes, never paths; it never said every part is a file.

**Alternatives.** (a) Send `request` as a file part named `request.json`
(refused — the server's `isinstance` test drops it to `{}`, a silent options
loss). (b) Send the request as a query parameter or header (refused — the
server reads neither; it is a form part in Atlas and here alike). (c) Widen
`_Api.request`'s `files` to `Mapping[str, tuple[str | None, str | bytes]]`
(adopted — the httpx vocabulary already distinguishes the two, and widening
keeps one transport helper for both multipart calls).

**Consequences.** `_Api.request`'s `files` parameter widens; the 8.10 glossary
import and the 8.9 business-metadata import keep their all-file shape
unchanged. The dedicated CLW-04 test asserts the `request` part has **no**
`filename` and the `data` part has one — the line this entry exists to hold.
