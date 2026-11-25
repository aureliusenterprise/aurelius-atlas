# 7.43 Section config split

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-869 (here). No new rule ids. Cites DET-15/16/24/25/48/53/56
  ..66 (7.20, 7.21c, 7.22b, 7.22d, 7.24, 7.25a, 7.25c, 7.25e, 7.27, 7.29: the
  layout table and the score mapping whose code moves), VCF-10/VCF-18/DD-619
  (7.21b, 16.5e: the facet groups the table carries), LDG-09/LDG-32 (7.22b,
  7.22d: the lineage box rows), AVS-01 (16.5d: the score rows the helpers read),
  and DD-852/DD-861 (7.25c, 7.25d: the one-mapping rule the helpers keep).

## Scope

`search/details/sections/section-config.ts` grew to 1,338 lines carrying three
different things: the shapes every layout consumer names, the eleven-row layout
table, and the Data Quality score mapping. The mapping is not config — it
derives rows and sorts from the view's `quality` answers (AVS-01) — and its
location forced `search/shared/catalogue-card.component.ts` to import **up**
from `search/shared/` into `search/details/sections/`, the one wrong-way edge
in the search feature.

This increment splits the file three ways:

- `sections/section.model.ts` holds the shapes: `FacetGroupKey`, `SectionDef`,
  `StatSource`, `StatDef`, `StatGroupDef`, `NavDef`, `TypeLayout`,
  `ComplianceChartDef`, `M4iLayoutType`. Pure types, no value.
- `sections/layouts.ts` holds the table and the constants a row names:
  `LAYOUTS`, `layoutForTypeName`, `hasGovQualityBox`, `FACET_GROUP_TITLES`,
  `RULE_SORT_KEYS`, `RULE_SORT_LABELS`, `GOV_QUALITY_TITLE`, `SCORE_ANCHOR`,
  `DATA_QUALITY_NOT_AVAILABLE`, and the two private builders.
- `search/shared/quality-mapping.ts` holds the score mapping:
  `QUALITY_DIMENSIONS`, `QualityDimension`, `QUALITY_DIMENSION_LABELS`,
  `qualitySortKey`, `printableRuleScore`, `overallRow`, `hasScoreSource`,
  `qualityRows`, `dimensionScore`, `scorePercent`. Placed in `search/shared/`
  so the card and the details screen name it as a peer (DD-869).

`section-config.ts` and `section-config.spec.ts` are deleted. The spec splits
with it: `layouts.spec.ts` (git-mv'd, so history follows the table) keeps the
layout rows, and `search/shared/quality-mapping.spec.ts` carries the score test
verbatim, rule ids and all (DET-56, DET-63, DET-64).

Every declaration moved byte-for-byte. Eight importers were repointed: six
production (`layout.state`, `gov-quality.state`, `related-sections.state`,
`details.component`, `catalogue-card.component`) and two specs
(`layout.state.spec`, `related-sections.state.spec`).

It does **not** deliver: any behaviour, template, or string change; a rename of
the rule-id references inside accepted specs and the `java-map` rows that name
`section-config.ts` at the increment that wrote them (the ledger records the
move here instead, and those pages are history — see DD-869); the remaining
wrong-way import `catalogue-card` → `details/shared/people` (the `PEOPLE_ENDS`
edge is Phase 3's, together with the purity rules that make the boundary
enforceable); or the layout rules for `src/testing/`.

## Semantics

No new rule ids. What this increment pins, as stated:

- **The table moves whole.** The eleven rows render identically: same anchors,
  same `@localize` keys, same section order, same stats and nav. Proven by the
  unchanged `layouts.spec.ts` — the same 18 `it`s, same assertions, against the
  moved table.
- **One owner per concept.** A type lives where its consumers meet (the model),
  a row lives in the table (the config), a derived value lives beside the code
  that derives it (the mapping). A helper of the score mapping may not import
  the table, and the table may not import the mapping — the two are peers now,
  both above or below.
- **The wrong-way edge that dies is the score one.** `catalogue-card` imports
  `./quality-mapping`, not `../details/sections/...`. The `PEOPLE_ENDS` edge
  stands until Phase 3 moves the people rows or the rule names an owner.
- **The trace tool sees every rule id still named.** Each moved test carries
  the ids it carried before; `uv run aurelius-atlas-trace check` reports no new
  gap.

## Java origin

Apache Atlas 2.4.0 ships ten copy-pasted AngularJS details templates, not a
config table or a score mapping. Both are Aurelius code — the table is DET-16's
DD-366 answer and the mapping is 7.25c's DD-852 answer — so this increment adds
no row to [Java map](../../../../docs/architecture/conversion/java-map.md).

## Deviations

None from Apache Atlas. A file split moves no value a parity test can see, so
the increment adds no row to
[Deviations](../../../../docs/architecture/conversion/deviations.md).

## Acceptance

| Check                                             | Command                                                                                            | Level |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ----- |
| The suite passes with the same total as before    | `nx test aurelius-atlas-webapp -c ci`                                                              | 1     |
| No spec lost or gained a test                     | per-file count A/B for the four touched specs                                                      | 0     |
| The moved table's own spec passes unchanged       | `nx test … --include="**/layouts.spec.ts"`                                                         | 1     |
| The purity gate stays green                       | `nx test aurelius-atlas-webapp -c ci` (dependsOn)                                                  | 1     |
| The bundle still type-checks and builds           | `nx build aurelius-atlas-webapp`                                                                   | 1     |
| No file under `src/app/` imports `section-config` | `grep -rn "section-config" src/app` — one comment names the old file as provenance, no import does | 0     |
| Every rule id still names a test                  | `uv run aurelius-atlas-trace check`                                                                | 0     |

Before: 1,045 tests in 80 files. After: 1,045 tests in 81 files — the one new
file is the spec that split off, and the per-file counts of the four touched
specs are identical (`layouts.spec` 18 + `quality-mapping.spec` 1 = the old
`section-config.spec` 19).
