# 061\. The governance banner answers live verdicts: the validate-entity mock retires

- **Status:** Proposed
- **Date:** 2026-11-11
- **Deciders:** Aurelius Enterprise

## Decision

**The entity-validation endpoint answers real governance verdicts.** The `validate-entity` auxiliary API reads the active governance rules from the catalogue, runs each over the draft record the editor sent, and answers one verdict per rule — a boolean and the rule's own message. The fixed four-card document it has shipped since increment 8.3 retires, and the Aurelius verdict shape replaces the legacy card shape across the API, both client twins, and the webapp banner in one release.

This supersedes the validate-entity clause of [ADR 055](<https://aureliusenterprise.github.io/view-read-doors/architecture/adr/055-the-lineage-chain-is-a-named-data-surface/index.md>): its R3 ("the JSON shapes the legacy services return are kept verbatim") stands for the lineage chain and retires for this endpoint alone. [DV-67](<https://aureliusenterprise.github.io/view-read-doors/architecture/conversion/deviations/index.md>) ("the app ships as the legacy mock") is superseded by DV-153. The auxiliary-API surface itself — ADR 055's naming, auth, deployment, and parity discipline — stands unchanged.

## Context

The legacy Aurelius application validated a draft record against governance rules with a Flink job the platform ran over stored data; the editor's validation service was never wired to it and answered a canned document. Increment 8.3 ported that service as the mock it was, because the engine to replace it did not exist and the browser contract had a renderer. Increments 12.1 and 12.6 built the engine: a governance rule is now data from a closed vocabulary, and one rule answers one boolean verdict over one record's attributes. The mock is now the only thing between the engine and the editor: an editor user sees four fixed sentences no matter what they type, while the rules that should produce those sentences sit active in the catalogue.

The card shape the mock froze is an accident of the legacy search index, not a contract: the legacy indexed one document per aspect, so the browser groups by aspect, and the verdict flag is a string. A verdict belongs to a rule, several rules can watch one attribute, and the editor's next step (a governance box naming the failing rule) needs the rule's identity, which the card shape throws away.

## Requirements

- **R1:** An editor sees verdicts from the rules the catalogue actually holds, for the draft as typed, within a keystroke's latency.
- **R2:** A rule the engine cannot read is reported as unread, naming the rule; it is never executed and never silently dropped.
- **R3:** The banner stays advisory: a validation failure never interrupts the edit, and never shows a stale or invented verdict.
- **R4:** The endpoint keeps the auxiliary-API discipline: one identity model, its own deployment, the browser's same-origin path.
- **R5:** Apache Atlas's API is untouched — this endpoint exists in no Apache product, so nothing external can break.
- **R6:** A catalogue outage reads as a failure of the check, not as "the record passes with no rules".

## Alternatives

- **Keep shipping the mock (do nothing).** Fails R1 forever: the banner is theatre while real rules exist. Refused.
- **Answer real verdicts inside the legacy card shape.** Meets R1 but fails R2 (a key holds one item, so a second rule per aspect vanishes without a trace) and R6's honest reporting; it also keeps string verdict flags and fake document ids in three hand-written twins. Refused.
- **Serve both shapes for a release window.** The webapp is the shape's only consumer and the system releases as one versioned whole (ADR 019), so the window contains no supported pair that needs it; a half-switched banner fails silently — the worst case R3 forbids. Refused.
- **Move the endpoint into the server.** Fewer containers, but the aux surface exists precisely to keep Aurelius endpoints off Atlas's public contract (ADR 046, 055); the move re-opens that decision for one banner. Refused.

## Tradeoffs

- **Positive:** editors see governance truth while drafting; the rule identity on the wire unblocks the 7.28 governance box and 12.8's stored verdicts; unread rules become visible debt instead of silent zeros.
- **Negative:** the aux app gains its first upstream — a service identity, a token mint, a cache, and a circuit — so one more dependency stands between the editor and an answer (R3's swallow and R6's loud 502 bound the blast radius); the rule set is visible as catalogue-wide, so rule-level per-person visibility would need a new decision later.
- **Neutral / follow-ups:** the prod-realm client join rides the chart track (with 12.3's sibling); rule authoring for the new vocabulary lands with 7.28; storing verdicts at save time is planned at 12.8; `deviations.md` gains DV-153 (supersedes DV-67), and 8.3's VE-01/VE-02 and CL-40 are amended by increment 12.7.
