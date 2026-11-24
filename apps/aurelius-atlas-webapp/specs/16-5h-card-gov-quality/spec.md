# 16.5h Governance verdicts on the rich cards: the mark on the card

- **Status:** in review
- **Pull request:** #458
- **Records:** with the core part (DD-838 to DD-840, DV-198); VCF-01 amended;
  relies on 16.5h's core part (ASG-08, AVS-11, VDR-13), 16.5d (VCF-01..07,
  DD-616), 7.24 (DET-42's box, DV-155), UIC-38 (DD-447)

This page is the `aurelius-atlas-webapp` part of increment 16.5h; its rule table
is the increment's shared set. The other part is with
[`aurelius-atlas-core`][part-0], which reads the verdicts and joins them into the
door's cards.

The legacy results card carried the governance mark in its quality column: a
warning triangle with the count of refused rules and a hover dropdown of them
(`governance-quality-list`). The ui lib already holds that part, rebuilt dumb
(UIC-38, DD-447), but no screen has ever mounted it — 16.5d shipped the shared
card with the quality column closed (VCF-01, `showQuality` false), because the
door answered no verdicts. 16.5h's core part now answers them on the card
(AVS-11). This part opens the column and wires the mark.

## Scope

- the shared rich card's governance mark: the count, the dropdown rows, the
  success check, the no-mark posture (VCF-19, VCF-20);
- the card shell's quality column, opened by the one shared card (VCF-19);
- the unchanged neighbours: the details box (DET-42), the section cards, the
  request count (VCF-21).

Not in scope:

| Not delivered                                                                            | Lands with |
| ---------------------------------------------------------------------------------------- | ---------- |
| The verdicts read and door join (ASG-08, AVS-11, VDR-13)                                 | [part-0]   |
| The details box's own read: it keeps the aux validate call (DET-42, DD-520, DV-155)      | –          |
| A verdicts fetch of the card's own (the legacy's N+1, replaced by the door join, DV-198) | –          |

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VCF-19 | The shared rich card mounts the governance mark (UIC-38) in the card shell's quality column, which the shared card now opens (VCF-01 amended): one warning with `verdicts.length` and the rows' hover dropdown, each row the verdict's message alone (DD-839). The card draws the rows straight from `card.verdicts` (AVS-11): no fetch, no loading state, the mark paints with the card                  |
| VCF-20 | The mark answers the card's judged mark (AVS-01's `governed`): a card with `governed` true shows the warning with its count, or the green check when its verdicts answer none (UIC-38's success state). A card with `governed` not true shows no mark at all — an entity whose type has no governance rules is not compliant, it is unjudged, and the legacy's blanket green check (DV-198) is not ported |
| VCF-21 | Nothing else changes: the details box keeps its own rules list and live verdict join (DET-42, DV-155), the section cards ride the same door answer (VCF-02), and a page still costs one search request (no per-card verdict fetch, DV-198)                                                                                                                                                                |

## Aurelius origin

- `search/components/governance-quality-list/` (legacy): the card's mark, fed by
  one App Search request per card (the core part's origin). The legacy trigger
  was the warning triangle with the count, its dropdown one row per refusal with
  `noncompliant_message` as the heading and `result` as the line — a line no
  document ever filled (ASG-03). The legacy showed the green check whenever the
  per-card fetch returned nothing, judged or not.
- The legacy mounted the column under the `SHOW_GOV_QUALITY` token and its CSS
  bottom-aligned the mark in the column (`.quality`: a flex column,
  `align-items: flex-end`), so the mark sits at the card's bottom-right. The
  card shell's column (UIC-12) is the same flex column, and the mark inherits
  that position (DD-447's port kept it).
- UIC-38 (DD-447) rebuilt the legacy states verbatim. This increment is the
  mount 7.24 left for it: DET-42's box took the details screen's copy of the
  feature from the aux API, and the card never got its copy (DV-155's split).

## Deviations

Against Apache Atlas: none (the verdicts are m4i/Aurelius demo furniture, DV-155).

Against the demo: DV-198 new — the card no longer fetches its own verdicts (the
door joins them, DV-198's first difference) and draws no mark for an unjudged
entity (where the demo drew the green check for every card).

## Acceptance

- `src/app/search/shared/catalogue-card.component.spec.ts`: a judged card with
  refusals draws the warning with the count and the dropdown rows, each its one
  message, in the card's order (VCF-19); a judged card with none draws the green
  check; an unjudged card draws no mark and no quality column (VCF-20); the
  card's trail, chips, description and people rows stay green (VCF-17).
- `e2e/test__aurelius_atlas_webapp.py`: a seeded rule and record (the banner
  scenario's seeders) reach the results page's card as a warning mark whose
  dropdown carries the rule's refusal message (VCF-19, VDR-13), and a seed of a
  type with no rule draws no mark (VCF-20). The verdicts land through the
  worker's round, so the assertions wait on the mark, not on the seed.
- `libs/angular/aurelius-atlas-ui`: UIC-38's component and spec stay green
  unchanged (the lib gains nothing).

[part-0]: ../../../../libs/python/aurelius-atlas-core/specs/16-5h-card-gov-quality/spec.md
