import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCheckCircle, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";

/** One non-compliant governance rule of the card's quality column (UIC-38). */
export interface GovQualityRow {
    /** The rule's non-compliant message, the dropdown row's heading. */
    message: string;
    /** The evaluated value's text, the dropdown row's line. */
    detail: string;
}

/**
 * The card's governance-quality column (UIC-38, DD-447): the legacy
 * `models4insight-governance-quality-list`, rebuilt dumb. A warning icon
 * with the non-compliant count and a hover dropdown of the rows (the
 * message as the heading, the evaluated value as the line); no rows, the
 * green check; the caller still fetching, the spinner tag. The legacy's
 * infinite-scroll container is not ported — the caller hands over the
 * rows it holds, and the dropdown lists them (DD-447's plain data).
 */
@Component({
    selector: "aurelius-atlas-ui-gov-quality-list",
    templateUrl: "./gov-quality-list.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [FontAwesomeModule],
})
export class GovQualityList {
    /** The non-compliant rows, the caller's page. Empty with no fetch is success. */
    readonly nonCompliant = input<GovQualityRow[]>([]);

    /** Whether the caller is still fetching — the spinner tag. */
    readonly loading = input(false);

    protected readonly faCheckCircle = faCheckCircle;
    protected readonly faExclamationTriangle = faExclamationTriangle;
}
