# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-369. The standalone stack serves the webapp at its root, behind the webapp's own nginx

- **Status:** Proposed
- **Increment:** 9.5d
- **Date:** 2026-11-07
- **Supersedes:** none; DD-363's redirect of `/` to `/atlas2/` gives way to the webapp

**Decision.** The stack's entry passes `/` and every path not otherwise routed to the webapp image's own
nginx, which serves the locales and passes `/api/` on to the server. A one-shot service of the same image fills
the image's nginx template into a volume, as the chart's init container does. The webapp signs in to the demo
realm through its public client `aurelius`.

**Reason.** The webapp's build serves at the root of its origin: its locales live at `/en-US/` and `/nl-NL/`,
its silent sign-in page at `/silent-check-sso.html`, and it calls the server at `/api/atlas/`. Serving it
under a path such as `/webapp/` would take a different build. Keeping its own nginx keeps its security headers
and its proxy as the chart deploys them. Filling the template the chart's way, from the image's own copy,
follows any change to the template without a second copy in the stack, and a placeholder left fails the
start.

**Alternatives.**

- The webapp under a path prefix: a separate build with another base href and API address.
- The stack's nginx serving the webapp's files itself: the webapp's headers and proxy rewritten in a second
  place.
- A filled copy of the template committed to the stack, as the webapp's e2e stack has: it drifts from the
  template.

**Consequences.** `https://localhost:9000/` is the webapp, no longer a redirect to the dashboards. The stack
needs the webapp image and certificate, built with `nx docker-build` and `nx certgen` of the webapp. Its
telemetry has no collector: `/otel/` drops the browser's pushes, and the webapp's nginx logs that its edge
spans find no exporter.
