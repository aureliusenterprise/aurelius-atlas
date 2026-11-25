import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCheckCircle, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";

import { type GovernanceVerdict } from "aurelius-atlas-data-access";

/**
 * The governance banner lines under one control (EDT-24 as amended by 12.7,
 * DD-446/DD-498): the verdicts that measure the control it sits under, one
 * line each, at the legacy's small size — the icon by the boolean `compliant`
 * (the warning triangle or the success circle, the legacy's pair) and the
 * verdict's message. No verdict, no lines; the answer's `unreadRules` renders
 * none (VEV-03).
 *
 * The drawer picks which verdicts belong to the control (a verdict rides its
 * `attribute` and every `anyOf` alternative, VEV-09, so one rule can name
 * several controls) and hands this component exactly those. The lines render
 * and say nothing else: no request, no store, no navigation — the draft's
 * validate round and its quiet swallow stay the drawer's (EDT-23).
 */
@Component({
    imports: [FontAwesomeModule],
    selector: "aurelius-atlas-webapp-governance-lines",
    template: `
        @for (verdict of verdicts(); track verdict.ruleGuid) {
            <p class="is-size-7 aurelius-editor-gov-line" data-gov-line>
                <span class="icon-text">
                    <span
                        class="icon"
                        [class.has-text-warning]="!verdict.compliant"
                        [class.has-text-success]="verdict.compliant"
                    >
                        @if (!verdict.compliant) {
                            <fa-icon [icon]="faExclamationTriangle"></fa-icon>
                        }
                        @if (verdict.compliant) {
                            <fa-icon [icon]="faCheckCircle"></fa-icon>
                        }
                    </span>
                    <span>{{ verdict.message }}</span>
                </span>
            </p>
        }
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GovernanceLines {
    /** The verdicts that measure the control these lines sit under (EDT-24). */
    readonly verdicts = input<readonly GovernanceVerdict[]>([]);

    /** The banner line's verdict icons (EDT-24, the legacy's pair). */
    protected readonly faCheckCircle = faCheckCircle;

    /** The banner line's warning icon (EDT-24). */
    protected readonly faExclamationTriangle = faExclamationTriangle;
}
