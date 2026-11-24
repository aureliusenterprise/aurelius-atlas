import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCheckCircle, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";

/** One non-compliant governance rule of the card's quality column (UIC-38). */
export interface GovQualityRow {
    /** The rule's non-compliant message, the dropdown row's only text. */
    message: string;
}

/**
 * The card's governance-quality column (UIC-38, DD-447): the legacy
 * `models4insight-governance-quality-list`, rebuilt dumb. A warning icon
 * with the non-compliant count and a hover dropdown of the rows, each row
 * its one message at reading weight; no rows, the green check; the caller
 * still fetching, the spinner tag. The legacy's infinite-scroll container is
 * not ported — the caller hands over the rows it holds, and the dropdown
 * lists them (DD-447's plain data).
 */
@Component({
    selector: "aurelius-atlas-ui-gov-quality-list",
    templateUrl: "./gov-quality-list.component.html",
    styles: [
        `
            /* The row is a sentence, so the box is as wide as a sentence
               (DD-839): Bulma gives the menu 12rem, which wraps every message
               into a stack of fragments inside the card's narrow quality
               column. The floor holds a full message on one line, the ceiling
               keeps the popup on screen. */
            .dropdown-menu {
                min-width: 22rem;
                max-width: 28rem;
            }

            /* The legacy's cap (DD-839): a card may carry the cap's 100 rows
               (AVS-11), so the box scrolls at the legacy's height instead of
               running off the screen. */
            .dropdown-content {
                max-height: 15rem;
                overflow: auto;
            }

            /* The rows sit close (DD-839): Bulma 1 renamed the divider class,
               so the legacy's own separator is unstyled and would stand as a
               2px line with 1.5rem of margin on each side. The legacy's rule
               is the thin line and the small margin below. */
            .content,
            .media-content,
            .media,
            .title {
                margin-bottom: 0;
            }

            .dropdown-separator {
                background-color: var(--bulma-border-weak);
                height: 1px;
                margin: 0.33rem;
            }

            /* The row reads at body weight (DD-839): the h6 carries Bulma's
               title weight and the content rule bolds a heading, so both are
               set down here. The size stays the title's (is-6), which the two
               rules leave alone. */
            .title,
            .content h6 {
                font-weight: 400;
            }
        `,
    ],
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
