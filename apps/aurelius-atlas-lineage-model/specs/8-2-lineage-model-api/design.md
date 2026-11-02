# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-200. The 8.2 proxy app injects its upstream HTTP client; the e2e Atlas is a canned-file server

- **Status:** Accepted
- **Increment:** 8.2
- **Date:** 2026-10-23

**Decision.** `create_app(settings, auth=None, http=None)` takes the upstream
`httpx.Client` the lineage fetch and the `/extract` call run on; production
builds one (timeout, CA), tests inject a `MockTransport`. The e2e stand-in
for the Atlas lineage feed (5.1, DV-69) is a **canned-file fixture Atlas**: a
dhi.io Python image serving `http.server`, whose `--directory` is the suite's
fixture directory, answering `GET /v2/lineage/<guid>` from
`<guid>.lineage.json` (404 for an absent file, matching Atlas).

**Reason.** The app's contract is a proxy: everything interesting about it
is which upstream requests it makes with which headers, so the client must
be inspectable — an injectable client makes the fetch/extract calls, the
forwarded `Authorization` header, and the 404/400/5xx mapping unit-testable
with no sockets (the 8.1 suite's fake issuer established the pattern). For
e2e, the real Atlas feed is increment 5.1; the fixture is the smallest
process that speaks the `v2/lineage/{guid}` shape — no build, no app image,
no Python in the sandbox image (the stdlib ships with the dhi.io python
image), and a file tree a reviewer can read as the scenario data. Serving
it from plain files keeps the fixture honest about the wire shape: the
camelCase JSON is Atlas's, not a mock's invention.

**Alternatives.** A python fixture container with a hand-written handler
(refused — the stdlib server plus a file per guid is the same test surface
with less code to own). testcontainers MockServer/WireMock (refused — a
Java/Go image for a two-route contract; the workspace's e2e stack stays
dhi.io images plus stdlib). Pointing the suite at a real Atlas (refused —
5.1 is not built; DV-69 is the stated stub).

**Consequences.** The 8.2 e2e chain (Keycloak → lineage-model → real
data2model → fixture Atlas) exercises the full browser path minus the
metadata store. When 5.1 lands, the suite repoints `ATLAS_BASE_URL` at the
server and keeps the canned fixtures as regression data.
