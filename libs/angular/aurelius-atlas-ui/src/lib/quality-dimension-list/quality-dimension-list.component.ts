import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { PercentPipe } from "@angular/common";

import { DataQualityPie } from "../data-quality-pie/data-quality-pie.component";

/** One quality-dimension row of the list (UIC-37). */
export interface QualityDimensionRow {
    /** The dimension word, as the caller localises or carries it. */
    dimension: string;
    /** The score, 0..1 (the legacy `dqscore_<dimension>.raw`). */
    score: number;
    /** How many rules the dimension counts (the legacy `dqscorecnt_*`). */
    count: number;
}

/**
 * The data-quality dimension rows (UIC-37, DD-437): the legacy
 * `models4insight-data-quality-list`, rebuilt dumb — one row per dimension
 * with the UIC-36 pie, the score as a percent to one decimal at most (the
 * legacy's `percent: '1.0-1'`), the dimension word, and the count. The legacy read the five `dqscore_<dimension>` /
 * `dqscorecnt_<dimension>` fields off the opened entity's App Search
 * document and skipped the dimensions it did not carry; the caller does
 * that selection and hands the rows over. An empty list shows the
 * placeholder the legacy's `notAvailable` branch showed
 * (`search.components.dataqualitylist.notAvailable`).
 */
@Component({
    selector: "aurelius-atlas-ui-quality-dimension-list",
    templateUrl: "./quality-dimension-list.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [PercentPipe, DataQualityPie],
    styles: `
        /* The legacy data-quality-list stylesheet: the row is a flex line,
           the icon beside the text keeps the legacy's margin. */
        .quality-dimension {
            display: flex;
            flex-direction: row;
            align-items: center;
        }

        .quality-dimension .icon {
            margin-right: 0.33rem;
        }
    `,
})
export class QualityDimensionList {
    /** The rows, in the caller's order (the legacy fixed the five, in order). */
    readonly dimensions = input<QualityDimensionRow[]>([]);

    /**
     * The text for the empty list — the catalogue's
     * `search.components.dataqualitylist.notAvailable`. The caller
     * localises it; an empty string renders no placeholder at all (the
     * legacy's `showPlaceholder` off).
     */
    readonly notAvailable = input("");

    /** The pie's 0..100 value for one 0..1 score (the legacy's `* 100`). */
    protected pieValue(row: QualityDimensionRow): number {
        return row.score * 100;
    }
}
