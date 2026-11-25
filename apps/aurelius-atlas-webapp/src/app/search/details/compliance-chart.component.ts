import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { DataQualityPie } from "aurelius-atlas-ui";

import { type ComplianceChartDef } from "./sections/section.model";

/** The Compliance Chart box's def plus DET-51's score (the layout strings and
 * the rule page's live percentage, or nothing on every other layout). */
export type ComplianceChart = ComplianceChartDef & { score: number };

/**
 * The Compliance Chart box of the rule page (DET-54, DD-849): the score pie of
 * the opened rule between the stats bar and its first card box, with the two-
 * row legend beside it — non-compliant first with its red swatch, compliant
 * second with the green. The pie is UIC-36 at size 8; the score is DET-51's.
 *
 * A painter, not a store: the title and legend strings come from the type's
 * layout row and the score from the verdicts store (the screen reads both and
 * hands the pair in as one input). The box is null on every layout that has no
 * chart, so the guard that drops the whole region (`@if (…; as chart)`) lives
 * with the screen, not here — this part paints a chart it is handed and nothing
 * else. It injects no store, router, or client.
 */
@Component({
    imports: [DataQualityPie],
    selector: "aurelius-atlas-webapp-compliance-chart",
    styleUrl: "./compliance-chart.component.scss",
    template: `
        <!-- The Compliance Chart box of the rule page (DET-54, DD-849): the
             legacy place between the stats bar and the Non-compliant box. The
             pie is UIC-36 at size 8, the score DET-51's; the legend is the
             legacy's two rows — non-compliant first — its colours verbatim. -->
        <div class="box aurelius-details-compliance-chart">
            <h2 class="title is-3">{{ chart().title }}</h2>
            <div class="block">
                <div class="columns">
                    <div class="column is-6">
                        <div class="aurelius-details-legend-row">
                            <span
                                class="aurelius-details-legend-swatch aurelius-details-legend-non-compliant"
                                aria-hidden="true"
                            ></span>
                            <span>{{ chart().nonCompliant }}</span>
                        </div>
                        <div class="aurelius-details-legend-row">
                            <span
                                class="aurelius-details-legend-swatch aurelius-details-legend-compliant"
                                aria-hidden="true"
                            ></span>
                            <span>{{ chart().compliant }}</span>
                        </div>
                    </div>
                    <div class="column is-6">
                        <div class="aurelius-details-score-pie">
                            <aurelius-atlas-ui-data-quality-pie [value]="chart().score" [size]="8" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ComplianceChartBox {
    /** The box's title, legend labels, and the rule's score (DET-54, DD-849). */
    readonly chart = input.required<ComplianceChart>();
}
