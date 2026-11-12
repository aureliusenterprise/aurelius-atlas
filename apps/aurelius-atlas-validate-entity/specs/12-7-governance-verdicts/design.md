# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) apply: an
accepted entry is never edited except its status line, and a changed decision
is a new entry that supersedes the old one.

## Entries

### DD-498. The verdict answer is a flat array, grouped by attribute in the client

- **Status:** Proposed
- **Increment:** 12.7
- **Date:** 2026-11-11

**Decision.** `POST /` answers `{verdicts, unreadRules}`. One active rule
contributes one verdict: `ruleGuid`, `ruleName`, `attribute`, `dimension`,
`compliant` (a JSON boolean), `message` (VEV-02). The response groups nothing;
the banner groups by `attribute`, keeping the legacy `description` alias map
(EDT-24 amended). The mock's keyed cards and their `isNonCompliant`, `raw`
wrappers, and `doc-` ids retire with it.

**Reason.** The card shape was an App Search by-product: the legacy indexed one
document per aspect and the browser inherited the keying (VE-02's origin). A
verdict belongs to a rule, not to an aspect — two rules can watch one attribute
and the banner shows one line per rule — so keyed cards force a lossy merge and
throw away the rule identity the editor needs for the 7.28 rule box. Rule
identity is also the honest shape for `unreadRules`: a stored expression rule
names the rule it could not read, not the aspect it failed (DV-146). A boolean
`compliant` ends the string `"0"`/`"1"` the mock froze (that was the legacy
Flink writer's quirk); the engine already answers a boolean (GQ-04, DD-489).

**Alternatives.** Keep the card shape and fill it from verdicts (refused: one
item per key loses all but one rule per aspect, and every leaf carries a `raw`
wrapper and a fake `doc-` id). Key by rule guid (refused: the grouping key is
the attribute — the banner's rows sit under a control and nothing else). Cards
plus a parallel flat array (refused: two shapes for one surface; DV-149
retires the card one).

### DD-499. The rules read rides the app's own service identity, not the caller's token

- **Status:** Proposed
- **Increment:** 12.7
- **Date:** 2026-11-11

**Decision.** The catalogue leg signs as its own service identity
(VEV-04): Keycloak client `aurelius-atlas-validate-entity`
(client-credentials, service account holding `atlas-read` on
`aurelius-atlas-server`), minted once by the app and refreshed ahead of expiry
— DD-458's pattern, made by the same
`aurelius_atlas_otel.ClientCredentialsTokenSource` the scanner uses. The
caller's token verifies at the gate (VE-03 of 8.3 unchanged) and is never
forwarded. The rule cache is keyed to that one identity (VEV-05).

**Reason.** Forwarding the caller's token (8.2's LM-04) is the natural sibling
and was refused on the cache: the rule set must be cached to survive the
editor's 200 ms debounce, and a cache filled under user A's visibility and
served to user B leaks what each may see — a correctness hole, not a
preference. Cached-under-one-identity is exactly what the scanner decided for
the same read (DD-458: the identity names the job in every catalogue read),
and the product intent matches: governance rules are catalogue-wide metadata
every editor is meant to see — the legacy evaluated them for everyone, and
per-user rule visibility would silently empty the banner for some editors,
which the quiet swallow (EDT-23) would hide. The audit trail then names the
app for its own metadata reads, which is the truth.

**Alternatives.** Forward the caller's token and drop the cache (refused: the
editor fires a rules search on every keystroke burst — the server pays for a
keystroke). One shared cache plus forwarding (refused: the leak above). Anonymous
search (refused: 6.2's authorization requires a token; nothing to hold).

### DD-500. The catalogue leg travels one breaker; an outage answers 502

- **Status:** Proposed
- **Increment:** 12.7
- **Date:** 2026-11-11

**Decision.** The upstream pool carries one pybreaker circuit (LM-11's shape,
LM-13's predicate): transport failures and `5xx` open it; a `4xx` is a fact
about the request and resets it. An unreachable, refusing, or open-circuited
server answers `502` with the Atlas error body (DV-80's posture) — VEV-06. A
rule that parses wrong is not an outage: it rides in `unreadRules` and the
answer is a `200` (VEV-03).

**Reason.** 8.3 had no upstream and no breaker; with one now, the failure
modes split cleanly and each has exactly one answer. The outage case must fail
loud: the mock taught the browser that an empty answer is normal (the quiet
swallow, EDT-23), so a silently swallowed store failure would render "no
governance rules" forever while every rule sits unread — a `502` on the error
channel is what the editor already swallows _and_ what an operator sees. The
4xx case must not open the circuit (a bad query from one restart loop must
blackhole the leg for the reset window) and must reach the caller — a `401`
from a stale mint is the server's fact to report. LM-12's fast-fail rides
because the breaker is in front of the pool: while open, the caller answers
`502` without a socket.

**Alternatives.** Retry the search (refused: DD-215's posture — one retry
moves the hang, the breaker bounds the outage and the debounce retries anyway).
Treat a parse failure as an outage (refused: one malformed stored rule would
take the banner down for everyone — the legacy swallowed expression errors for
the same reason; DV-146's honest version records them per rule instead).

### DD-501. The clean cut: one PR, no compat shim for the card shape

- **Status:** Proposed
- **Increment:** 12.7
- **Date:** 2026-11-11

**Decision.** The verdict shape, the Python client twin (CL-40 amended), the
Angular twin, and the banner switch in this one PR. The app never answers the
card document again and no code path parses it. `mock.py` is deleted with its
scenarios.

**Reason.** The workspace releases as one versioned whole (ADR 019): the app
and the webapp that calls it deploy together, and the browser is the shape's
only consumer (ADR 055 named it; nothing else calls the aux API — no external
client is on record). A dual-shape release would keep the `raw` wrappers alive
in three twins for a window in which no supported pair needs them, and would
leave the banner's parse ambiguous exactly where the mock once hid it (an
unreadable answer renders nothing, so a half-switch fails silently — the worst
outcome). Deleting the mock is the point of DV-149; keeping its models would
make the deviation permanent.

**Alternatives.** Content-negotiate both shapes (refused: two contracts in CI
forever; ADR 017's compatible-change rule protects the Atlas public contract,
not this Aurelius-origin internal one). Ship the app first and the webapp next
PR (refused: between the two, the live banner parses nothing and shows nothing
— a silent regression, and the e2e banner pin could not join either PR).

### DD-508. A lost index create on a shared store is success, not a start failure

- **Status:** Proposed
- **Increment:** 12.7
- **Date:** 2026-11-12

**Decision.** The server's index-preparation steps (`ElasticsearchEntityDocuments.prepare`,
`ElasticsearchTypedefDocument.prepare`, `ElasticsearchEntityAuditRepository.prepare`)
create each index through one helper, `ensure_index`: a create that answers
`resource_already_exists_exception` is success — the index stands, made whole by
the other server — and the step then takes the existing-index path (settings,
mappings). Any other error still raises. Shared infra is deliberate (DD-223):
suites ride the dev Elasticsearch side by side, and this PR's stack starts its
own Atlas server on that same store, so two servers can boot there in the same
second.

**Reason.** The CI run of this PR paired the new validate-entity stack with the
server suite's own stack on the dev store: both ran `prepare` against the same
aliases, one lost the create race, Elasticsearch answered 400
`resource_already_exists_exception`, the lifespan raised, uvicorn exited 3, and
62 server-scenario tests errored in setup. The loser's create was never a real
error — both servers make the same index from the same definitions — and a
start that treats it as one turns a coincidence of timing into a suite failure.
The check-then-create stayed (the answer's cost is one search); only the create
learned to lose gracefully.

**Alternatives.** Serialize the e2e suites so no two servers boot together
(refused: shared infra is the point, and CI parallelism is DD-223's trade). Give
each stack its own store (refused: the same reasoning, and the memory). Retry
`prepare` on any 400 (refused: a wrong mapping must stay a start failure — the
helper distinguishes the one answer that means "someone already made it").

### DD-509. The validate-entity e2e stack's server keeps host port 21008

- **Status:** Proposed
- **Increment:** 12.7
- **Date:** 2026-11-12

**Decision.** The 12.7 stack's Atlas server publishes loopback host port 21008.
It was 21007 when the increment was written; main's db-scanner stack (#323)
claimed 21007 for its server meanwhile, and the two suites would fail each
other's `docker compose up` if they ever ran side by side. The next free port
joins the ladder: 21000 serve, 21001 the server suite, 21003 the app, 21005/
21006/21007 the three scanners, 21008 this stack.

**Reason.** Every e2e stack publishes its chain's ports loopback-pinned so the
suite's client speaks to them from the host (CIA-03), which makes the host port
a repo-wide resource with no allocator but the comment that names its neighbours.
A silent double-booking fails as an `address already in use` inside whichever
suite loses, far from its cause; naming the ladder in the comment is the cheap
guard.

**Alternatives.** Ephemeral ports (`:21000` published unbound, the conftest
reading the mapped port — the pattern the webapp suite's `get_service_port`
could adopt; refused here: the fixed port is what lets the app's compose alias,
the realm's registered return URLs, and the suite's pin agree without a lookup,
the server suite's precedent). Renumber db-scanner instead (refused: it is
merged; the moving PR yields).
