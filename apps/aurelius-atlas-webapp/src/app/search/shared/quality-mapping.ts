/**
 * The one mapping of the Data Quality score surfaces (DET-56..DET-59,
 * DET-63..DET-66, DD-852, DD-861): 7.25c's score box, stat, and card block
 * derive from the view family's `quality` rows (AVS-01) through these helpers
 * only — the five dimensions in the fixed order, the dimension sort keys, the
 * printable rule-score line (DET-65), the source gate (DET-63/DET-64), and
 * the stat's percent (DET-58). 7.43 moved the mapping here from
 * `details/sections/section-config.ts` so `search/shared/catalogue-card`
 * names it without reaching into `details/` (DD-869).
 */

import { formatPercent } from "@angular/common";
import type { CardQuality, RuleScore } from "aurelius-atlas-data-access";
import type { QualityDimensionRow } from "aurelius-atlas-ui";

/**
 * The five score dimensions in the legacy's fixed row order (DET-56,
 * DET-59): the legacy `data-quality-list` template's five blocks, and the
 * five sort options DET-59 adds — never `overall`, which only the stat
 * reads (DET-58).
 */
export const QUALITY_DIMENSIONS = ["accuracy", "completeness", "timeliness", "uniqueness", "validity"] as const;

/** One of the five score dimensions (the `overall` row is no dimension). */

export type QualityDimension = (typeof QUALITY_DIMENSIONS)[number];

/**
 * The dimension words (DET-56, DET-59): the `dqscore_<dimension>` catalogue
 * keys both catalogues carry — the legacy menu labels, titlecased raw by
 * its `sorting.component` (the same posture DET-21's Name literal takes).
 */
export const QUALITY_DIMENSION_LABELS: Readonly<Record<QualityDimension, string>> = {
    accuracy: $localize`:@@dqscore_accuracy:Accuracy`,
    completeness: $localize`:@@dqscore_completeness:Completeness`,
    timeliness: $localize`:@@dqscore_timeliness:Timeliness`,
    uniqueness: $localize`:@@dqscore_uniqueness:Uniqueness`,
    validity: $localize`:@@dqscore_validity:Validity`,
};

/**
 * The score sort key of one dimension (DET-59): the legacy option value,
 * `dqscore_<dimension>`, which the sections store recognises (DD-854).
 * @param dimension the dimension
 * @returns the sort option's key
 */
export function qualitySortKey(dimension: QualityDimension): string {
    return `dqscore_${dimension}`;
}

/**
 * Whether a score row can render or sort (DET-63): a held row carries a
 * usable score — `null`, `undefined`, and a negative score never do, the
 * same quiet posture DET-49 takes for a broken verdict.
 * @param row the door's score row
 */
function usableScore(row: CardQuality | undefined): row is CardQuality {
    return row !== undefined && typeof row.score === "number" && row.score >= 0;
}

/**
 * The field's rule score row that prints a line (DET-65): a held row with a
 * usable score — DET-63's posture, so `null`, `undefined`, and a negative
 * score never print — and a dimension word to name the line with. DET-66's
 * two sorts ask this one question, so the box can never sort on a row it
 * prints nothing for.
 * @param row the view's row for one rule (AVS-13), or absent
 */
export function printableRuleScore(row: RuleScore | undefined): RuleScore | undefined {
    return row !== undefined && typeof row.score === "number" && row.score >= 0 && row.dimension !== ""
        ? row
        : undefined;
}

/**
 * The `overall` row of a card's or a view's score rows (DET-58, DET-63),
 * or `undefined` when it holds none.
 * @param quality the AVS-01 score rows, or absent
 */
export function overallRow(quality: CardQuality[] | undefined): CardQuality | undefined {
    return quality?.find((row) => row.dimension === "overall");
}

/**
 * Whether the score source stands (DET-63): the `overall` row, with a
 * count above zero — the legacy's own gate on `dqscorecnt_overall`. The
 * box, the stat, and the card's block all ask this one question, so the
 * four surfaces cannot disagree about "sourceless".
 * @param quality the AVS-01 score rows, or absent
 */
export function hasScoreSource(quality: CardQuality[] | undefined): boolean {
    return (overallRow(quality)?.count ?? 0) > 0;
}

/**
 * The dimension rows as UIC-37 draws them (DET-56, DET-60, DD-852, DD-861):
 * the scored dimensions in the fixed order, `overall` left out, a row whose
 * score never renders skipped (DET-63), and a dimension whose `count` is 0
 * dropped (DET-64) — the legacy gates each dimension on the count's truthy
 * value, and its own documents hold 0 for every dimension nothing measured.
 * The gate on the source is the caller's — a card prints its partial set
 * (DET-60), the box shows the placeholder (DET-56). ASQ-05 sums the five
 * dimensions into `overall`, so a sourceless view is the only one whose list
 * can come back empty.
 * @param quality the AVS-01 score rows, or absent
 * @returns the rows in DET-56's order
 */
export function qualityRows(quality: CardQuality[] | undefined): QualityDimensionRow[] {
    const rows: QualityDimensionRow[] = [];
    for (const dimension of QUALITY_DIMENSIONS) {
        const row = quality?.find((entry) => entry.dimension === dimension);
        if (usableScore(row) && row.count > 0) {
            rows.push({ dimension: QUALITY_DIMENSION_LABELS[dimension], score: row.score, count: row.count });
        }
    }
    return rows;
}

/**
 * One dimension's usable score on a card, for the score sort (DET-59,
 * DET-63, DET-64): the card's row for the dimension, or `undefined` when it
 * holds none, the score never renders, or the dimension counts nothing —
 * an uncounted dimension is not a scored one (DET-64), so it takes the
 * sort's last place like an absent row.
 * @param quality the card's AVS-01 score rows, or absent
 * @param dimension the sorted dimension
 */
export function dimensionScore(quality: CardQuality[] | undefined, dimension: QualityDimension): number | undefined {
    const row = quality?.find((entry) => entry.dimension === dimension);
    return usableScore(row) && row.count > 0 ? row.score : undefined;
}

/**
 * The stat's percent value (DET-58, DD-853): exactly the legacy's
 * `| percent: '1.0-1'` — whole percents whole, at most one decimal — so it
 * renders like every other percent on the screen. Angular's
 * `formatPercent` is the pipe's own function.
 * @param score the `overall` row's 0..1 score
 * @returns the percent string in the active locale
 */
export function scorePercent(score: number): string {
    return formatPercent(score, $localize.locale || "en-US", "1.0-1");
}
