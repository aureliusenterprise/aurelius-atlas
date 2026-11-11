# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply:
an accepted entry is never edited except its status line, and a changed decision is a new
entry that supersedes the old one.

## Entries

### DD-475. The rule vocabulary travels to the browser as a server resource

- **Status:** Proposed
- **Increment:** 12.5
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** The server answers `GET /api/aurelius/v1/quality/kinds` by rendering the engine's
`KINDS` map, `CASTABLE_TYPES`, and the threshold bounds at request time. The browser renders its
rule form from that answer (7.27). The answer is built from the imported vocabulary, never from
a table written a second time.

**Reason.** The vocabulary changes when a kind is added, and 12.1's spec calls adding a kind a
release. A browser-side table would be a second copy that goes stale silently: the form would
offer a kind the engine rejects, or hide one it accepts, and the scanner would then mark the
stored rule ERROR (DQS-08, DD-454). The legacy kept its rule form's fields in the browser with
no API behind them, which is how its free-text expression rule outlived its engine (DV-146). The
engine already validates at parse time, so one render of `KINDS` is the whole implementation,
and the unit test compares the answer with the map it renders.

**Alternatives.**

- A TypeScript mirror of the table with a parity test: no server change, but parity holds only
  as long as someone runs the test, and every kind addition needs two PRs in two languages.
- Serving the vocabulary from the typedefs (the `dq` attributes of the patch): the attributes
  name the storage shape, not the kinds. Only the engine knows which parameters a kind requires
  and which dimension it measures.

**Consequences.** `aurelius-atlas-server` gains a dependency on `aurelius-atlas-quality`. The
endpoint answers the vocabulary of the deployed server build, so a webapp and a server always
come from one release, as they already do.

### DD-476. Validation of a rule shape rides the engine's parser and answers 200

- **Status:** Proposed
- **Increment:** 12.5
- **Date:** 2026-11-11
- **Supersedes:** none

**Decision.** `POST /api/aurelius/v1/quality/rules/validate` calls `rule_from_atlas_attributes`
on the request body. A parsed rule answers `{valid: true, kind, dimension}`; a
`QualityRuleError` answers `{valid: false, reason}` with the error's own text. Both answers are
200, in JSON, outside Atlas's error shape. Only a body that is not a JSON object is a 400.

**Reason.** An unreadable rule is the expected answer of this endpoint, the same way a failed
login is the answer of a login endpoint. The webapp renders the reason under the fields the
editor owns (7.27), and it needs the engine's sentence, not an error code it maps. Reusing the
parser (DQ-07) keeps the check exact: the same call decides what the scanner can read (DQS-08),
so a rule the endpoint accepts cannot arrive at the scanner as ERROR. A 200 also keeps the
browser's error handling (the data-access error matrix, 7.19) out of a path that is not an
error, and keeps the retries (7.26, APC-13) off a body this endpoint does not store.

**Alternatives.**

- A 400 with the reason in `errorMessage`: Atlas's shape for a bad request, and Atlas has no
  code for "a rule of a shape we do not keep" (SRV-04's codes are type-system codes). The
  webapp would special-case one 400 code out of its alert flow.
- Validation in the browser only: the form would duplicate the engine's rules and drift from it,
  the failure DD-475 exists to close.

**Consequences.** The endpoint's answer is this increment's own JSON contract (like DD-440's
Aurelius codes). It is a checker, never a writer: a saved rule still rides EWR with
`atlas-write` (AUZ), and a validate-then-save client can still be refused at save time — the
save flow re-checks the answer (7.27's EDT rules).
