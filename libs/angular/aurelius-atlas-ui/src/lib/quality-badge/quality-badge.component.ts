import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { PercentPipe } from "@angular/common";

import { DataQualityPie } from "../data-quality-pie/data-quality-pie.component";

/**
 * The card's data-quality badge (UIC-39, DD-437): the legacy rule card's
 * `dqscore` line — the UIC-36 pie beside the score as a percent to one
 * decimal at most (the legacy's `percent: '1.0-1'`). It is the quality-column content: `entity-card`'s
 * `[card-quality]` projection slot (7.13's `showQuality`) holds it once a
 * later slice turns the column on (7.25). Until then it ships dumb with a
 * story (DD-437).
 *
 * The score is the 0..1 raw, as the legacy read `dqscore.raw`: the pipe
 * prints it and the pie gets the legacy's `* 100`.
 */
@Component({
    selector: "aurelius-atlas-ui-quality-badge",
    templateUrl: "./quality-badge.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [PercentPipe, DataQualityPie],
    styles: `
        /* The legacy data-quality card's row: the pie on the line beside
           the score text, the icon's margin the legacy's. */
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
export class QualityBadge {
    /** The score, 0..1 (the legacy `dqscore.raw`). */
    readonly score = input(0);

    /** The pie's 0..100 value for one 0..1 score (the legacy's `* 100`). */
    protected get pieValue(): number {
        return this.score() * 100;
    }
}
