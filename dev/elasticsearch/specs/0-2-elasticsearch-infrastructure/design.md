# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved
from the
[Design Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted
entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-006. Development and tests run Elasticsearch with security on

- **Status:** Proposed
- **Increment:** 0.2
- **Date:** 2026-10-17

**Decision.** `dev/elasticsearch` and the test fixture run with `xpack.security` enabled: TLS on the
HTTP layer with a certificate from the workspace CA (dev) or an ephemeral CA (tests), and basic
authentication for the built-in `elastic` user. The store library has no option to skip certificate
verification.

**Reason.** It is the posture production needs, and the one `dev/postgres` already has; a store that
only ever ran without security would meet TLS and authentication for the first time in production.

**Alternatives.** Security disabled in development: faster start-up and simpler `curl`, but a
different code path (plain HTTP, no credentials) from production, and a verification switch in the
library that someone eventually leaves off.

**Consequences.** Dev tools need the CA file and the password
(`curl --cacert dev/elasticsearch/certs/ca.pem -u elastic:…`). A dedicated application user with
least privilege replaces `elastic` when authorization arrives (6.2).
