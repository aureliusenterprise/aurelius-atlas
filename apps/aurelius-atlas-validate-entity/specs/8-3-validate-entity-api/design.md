# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-201. The 8.3 mock ships as module data; the verifier is injectable

- **Status:** Accepted
- **Increment:** 8.3
- **Date:** 2026-10-23

**Decision.** `aurelius_atlas_validate_entity.mock.MOCK_VALIDATION` holds the
legacy `output` dict verbatim, as module data — the endpoint answers
`json` of that constant, byte-for-byte. `create_app(settings, auth=None)`
takes the shared `KeycloakAuth` verifier; production builds one from the
settings, tests inject one pointed at the fake issuer. No request model:
`POST /` does not read its body (the legacy mock ignores it, and the port
keeps that).

**Reason.** The app is a constant: every rule about it is the document's
shape (VE-02) and the auth gate (VE-03), so the document lives in one
place as data, and the scenario/unit tests compare whole bodies with no
volatile fields. An injectable verifier is the DD-197/8.1 pattern (the
auth library's own test double is the reference); a request model would
invent a contract the mock does not have (DV-67: the body is ignored,
malformed bodies answer the document too — VE-01).

**Alternatives.** Pydantic models for the mock document (refused — the
document is a fixed literal; modelling it adds code that can drift from
the bytes the browser contract is). A `Request`-reading handler that
validates the entity (refused — DV-67 is the stated mock: validation is a
future server rule, not this increment).

**Consequences.** The 8.x app set is uniform (auth lib, otel lib, liveness,
TLS, settings shape); the parity scenario is byte equality, so a change to
the document is a visible contract change. When real validation lands
(future server rule), this app's endpoint gains an input contract and the
constant moves to a fallback path — a new increment, a superseded DV-67.
