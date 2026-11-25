import { dimensionScore, hasScoreSource, overallRow, qualityRows, scorePercent } from "./quality-mapping";

/**
 * The one score mapping (DET-56..DET-59, DET-63..DET-65, DD-852, DD-861):
 * the view's AVS-01 rows through the shared helpers, carried here verbatim
 * from the config table's spec when 7.43 moved the mapping to
 * `search/shared/quality-mapping.ts` (DD-869). The layout rows that name
 * the score box stay in `layouts.spec.ts`.
 */
describe("Quality mapping (DET-56, DET-63, DET-64)", () => {
    it("derives the score rows and the stat's value from the view's rows (DET-56, DET-63, DET-64)", () => {
        // DET-63's skip rule and DET-64's count gate live in one helper
        // (DD-852, DD-861): the dimensions in the fixed order, `overall` left
        // out, a row whose score never renders skipped, and a dimension the
        // roll-up counts 0 dropped — the legacy's own truthy count gate.
        const rows = [
            { dimension: "validity", score: 0.5, count: 2, total: 4 },
            { dimension: "accuracy", score: 0.75, count: 1, total: 2 },
            { dimension: "overall", score: 0.9, count: 5, total: 5 },
            { dimension: "timeliness", score: null as unknown as number, count: 1, total: 1 },
            { dimension: "uniqueness", score: -1, count: 1, total: 1 },
            { dimension: "completeness", score: 0.25, count: 0, total: 1 },
        ];
        expect(qualityRows(rows).map((row) => [row.dimension, row.score, row.count])).toEqual([
            ["Accuracy", 0.75, 1],
            ["Validity", 0.5, 2],
        ]);

        // DET-64 keeps a dimension that counts something even when its score
        // is 0: a measured 0 is a result, an uncounted dimension is an absence.
        expect(
            qualityRows([
                { dimension: "overall", score: 0, count: 1, total: 1 },
                { dimension: "uniqueness", score: 0, count: 1, total: 1 },
            ]).map((row) => [row.dimension, row.score, row.count]),
        ).toEqual([["Uniqueness", 0, 1]]);

        // DET-59's last place reads the same gate (DET-64): an uncounted row
        // sorts like an absent one, and a 0-count row never wins a sort.
        expect(dimensionScore(rows, "validity")).toBe(0.5);
        expect(dimensionScore(rows, "completeness")).toBeUndefined();
        expect(dimensionScore(rows, "uniqueness")).toBeUndefined();
        expect(dimensionScore(rows, "accuracy")).toBe(0.75);

        // DET-58's source test: the `overall` row with a count above zero —
        // 0 count, no row, and no quality at all are all sourceless.
        expect(overallRow(rows)?.dimension).toBe("overall");
        expect(hasScoreSource(rows)).toBe(true);
        expect(hasScoreSource([{ dimension: "overall", score: 0.5, count: 0, total: 1 }])).toBe(false);
        expect(hasScoreSource([{ dimension: "accuracy", score: 0.5, count: 1, total: 1 }])).toBe(false);
        expect(hasScoreSource(undefined)).toBe(false);

        // DET-58's percent: whole percents whole, at most one decimal.
        expect(scorePercent(1)).toBe("100%");
        expect(scorePercent(0.75)).toBe("75%");
        expect(scorePercent(0.666)).toBe("66.6%");
    });
});
