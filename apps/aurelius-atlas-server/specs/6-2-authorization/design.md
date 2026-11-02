# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-300. Four fixed roles of the server's client grant Atlas's privileges

- **Status:** Proposed
- **Increment:** 6.2a
- **Date:** 2026-11-01

**Decision.** The server's authorizer grants Atlas's privileges (`AtlasPrivilege`) by four roles of its own
client in the identity provider, read from the token's `resource_access.<client>.roles`: `atlas-read` (type,
entity and classification reads), `atlas-write` (entity, classification, label, business metadata and
relationship changes), `atlas-types` (type definition changes, and reads) and `atlas-admin` (purge, export,
import, admin audits). What each role grants is fixed in the server; who holds a role is decided in the identity
provider only. Checks sit where Atlas's sit, with its action texts and `UNAUTHORIZED_ACCESS`. The user chose this
on 2026-11-01 over porting Atlas's simple-authz policy file.

**Reason.** ADR 038 asks for one place that answers what a person may do, apart from who they are, where
revoking is one act. The identity provider already holds who someone is (ADR 007, DD-250); holding their roles
there too makes granting and revoking one act in one console, with no policy file to deploy. Four roles cover
the distinctions Atlas's default policy draws (readers, stewards, type owners, administrators).

**Alternatives.** Atlas's simple-authz policy (regular expressions over types, entities and classifications,
mapped from users and groups): Atlas-compatible and finer, but a second place to manage and a file to deploy.
An external policy engine: one more service to run everywhere it is validated.

**Consequences.** No permission finer than a role: a user may change every entity type or none (DV-114). The
roles are client roles, so a client that forwards a user's token (the webapp's) maps them into its scope. The
dev realm gives the writer every role and the reader `atlas-read`.
