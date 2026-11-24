# 071\. A rule's verdicts come through the view family

- **Status:** Proposed
- **Date:** 2026-11-24
- **Deciders:** Aurelius Enterprise

## Decision

**The rewritten webapp reads a rule's verdicts from a fourth door of the view family.** The server answers `POST /api/aurelius/v1/rule/verdicts` with every stored governance verdict of one rule: each judged entity's GUID, the verdict, and the message. The door reads the verdicts index of [ADR 060](<https://aureliusenterprise.github.io/feat-7-25c-quality-scores/architecture/adr/060-the-app-search-api-returns-as-a-view-over-the-one-store/index.md>) through the same `EntityDocuments` contract the other doors read, needs `ENTITY_READ` like they do, and answers in the view family's shape style.

This is the rule page's read: the compliant and non-compliant lists, and the counts beside the compliance chart. The entities behind the verdicts arrive as the search door's cards, the way every other box on the details screen resolves its rows ([ADR 064](<https://aureliusenterprise.github.io/feat-7-25c-quality-scores/architecture/adr/064-the-webapp-reads-rich-catalogue-data-through-one-aurelius-view-family/index.md>)).

**The App Search wire stays closed to new consumers.** [ADR 064](<https://aureliusenterprise.github.io/feat-7-25c-quality-scores/architecture/adr/064-the-webapp-reads-rich-catalogue-data-through-one-aurelius-view-family/index.md>) fixed the exit path of `atlas-dev-gov-quality`: it answers the original webapp and gains no new consumer. The rewritten webapp does not call `/api/as/v1/`; the verdicts it shows ride the Aurelius prefix beside the other doors. The index itself is not renamed, re-derived, or moved by this record.

## Context

The legacy details screen for a governance rule (`m4i_gov_data_quality`) asked the `atlas-dev-gov-quality` engine twice: once filtered `compliant='1'` and once `compliant='0'`, each on the rule's own GUID. The answers gave the counts above the page, the compliance chart, and the two card lists. The 7.25a increment delivered the box each *other* page carries; the rule page's own half — the roadmap's 7.25c — still shows only the Fields box.

The data exists. The App Search worker judges every active governance rule over every entity of its type and keeps the verdicts current (`app_search_governance.py`, ASG-06). 16.5h already reads that index for the cards, but per *entity* (`verdicts_by_entity`, AVS-11). What the rule page needs is the same index read by *rule* — a read the view family has never opened.

There are three ways to hand it to the browser: call the App Search wire from the new webapp, join the verdicts into the rule's own view, or open a small door. The first breaks ADR 064's exit path. The second is the wrong shape: the rule's view would carry one row per judged entity of its type, an unbounded list joined per read, against ADR 064's rule that a view reads its own document and joins nothing per request. The third costs one route over a read the store already has.

## Requirements

- R1: One request answers every verdict of one rule: entity GUID, verdict, message.
- R2: The door reads what the worker last wrote (ASG-06); it judges nothing and starts no task.
- R3: The door needs `ENTITY_READ`, as the other view doors do (AVR-01).
- R4: A rule with no verdicts answers the empty list, not an error.
- R5: No answer of the App Search wire or Apache Atlas's API changes (ADR 060, ASG-07).
- R6: The webapp resolves the judged entities through the search door like every other box, so the rows are the shared rich cards.

## Alternatives considered

| Alternative | Why not |
| --- | --- |
| The webapp calls `POST /api/as/v1/engines/atlas-dev-gov-quality/search` | ADR 064: the wire is on an exit path and gains no new consumer. |
| The rule's `EntityView` carries its verdicts | Unbounded per-type rows joined per read; breaks the document-only rule of ADR 064 and makes every rule read expensive. |
| A live re-judge over the rule's type (the aux `validate-entity` call per entity) | O(entities) evaluations per page open, out of step with the worker's answer, and the banner's contract (ADR 061) is a draft. |
| The compliance boxes read the App Search engine through the legacy Angular `GovernanceQualitySearchService` | Ports the legacy client whole instead of the one call the screen needs; ties the new webapp to the retiring wire. |

## Consequences

- The view family grows to four doors; the spec map's VDR namespace covers it (16.5i), and ADR 064's "one shape, three doors" holds for the shape family — this door answers verdict rows, not cards, because a verdict is not an entity.
- The rule page (7.25b) is buildable: counts, chart, and both card lists read one door plus the search door's card resolve the details screen already runs.
- No new index, task, or deployment surface: the door reads `aurelius-atlas-gov-quality`, the alias 14.6 created.
- If the verdicts index is ever retired with the App Search wire, this door is the seam that survives: its contract names verdicts, not engine documents.
