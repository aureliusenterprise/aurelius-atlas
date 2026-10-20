import { ChangeDetectionStrategy, Component, model } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCompass, faInfoCircle, faSearch } from "@fortawesome/free-solid-svg-icons";

import { GovernanceResponsibilitiesInfoModal } from "./governance-responsibilities-info-modal.component";

/**
 * The Aurelius governance-responsibilities card: title, info icon, and the
 * two explaining articles (searching and exploring).
 *
 * The Aurelius card also carried a `simple-search-input` (by name/e-mail)
 * and an "explore" button; both are search navigation and deferred to the
 * search slice (BRW-06, DD-054) — the card's search/exploring *text* stays,
 * as the landing copy the Aurelius screen shows before any search exists.
 */
@Component({
    imports: [FontAwesomeModule, GovernanceResponsibilitiesInfoModal],
    selector: "aurelius-atlas-webapp-governance-responsibilities",
    templateUrl: "./governance-responsibilities.component.html",
    styleUrl: "./governance-responsibilities.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GovernanceResponsibilities {
    /**
     * Open state of the card's info modal: the card owns it, the modal
     * closes itself through the two-way binding (BRW-05).
     */
    readonly infoModalActive = model(false);

    protected readonly faCompass = faCompass;
    protected readonly faInfoCircle = faInfoCircle;
    protected readonly faSearch = faSearch;

    /**
     * Accessible name of the info button — the modal's title, as the Aurelius
     * icon link had none (BRW-03).
     */
    protected readonly infoTitle = $localize`:@@search.browse.governanceContext.infoModal.title:Data governance organization`;
}
