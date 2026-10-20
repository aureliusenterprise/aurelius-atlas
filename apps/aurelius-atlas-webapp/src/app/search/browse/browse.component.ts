import { ChangeDetectionStrategy, Component } from "@angular/core";

import { BusinessContext } from "./business-context/business-context.component";
import { GovernanceResponsibilities } from "./governance-responsibilities/governance-responsibilities.component";
import { TechnicalContext } from "./technical-context/technical-context.component";

/**
 * The Aurelius browse landing page — the default destination of the Aurelius
 * router (`'' -> /search/browse`, SHL-04): the hero block and the three
 * context cards (BRW-01), static content only (BRW-04).
 *
 * The Aurelius page issued no requests here either; its search fields and
 * explore buttons are search navigation deferred to the search slice
 * (BRW-06, DD-054), as is the Shell chrome.
 */
@Component({
    imports: [BusinessContext, GovernanceResponsibilities, TechnicalContext],
    selector: "aurelius-atlas-webapp-browse",
    templateUrl: "./browse.component.html",
    styleUrl: "./browse.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Browse {}
