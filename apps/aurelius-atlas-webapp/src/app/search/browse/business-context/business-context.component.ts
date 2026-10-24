import { ChangeDetectionStrategy, Component, model } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCompass, faInfoCircle, faSearch } from "@fortawesome/free-solid-svg-icons";

import { BusinessContextInfoModal } from "./business-context-info-modal.component";

/**
 * The Aurelius business-context card: title, info icon, and the two
 * explaining articles (searching and exploring).
 *
 * The Aurelius card also carried a `simple-search-input` and an "explore"
 * button; both are search navigation and deferred to the search slice
 * (BRW-06, DD-143) — the card's search/exploring *text* stays, as the
 * landing copy the Aurelius screen shows before any search exists.
 */
@Component({
    imports: [BusinessContextInfoModal, FontAwesomeModule],
    selector: "aurelius-atlas-webapp-business-context",
    templateUrl: "./business-context.component.html",
    styleUrl: "./business-context.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BusinessContext {
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
    protected readonly infoTitle = $localize`:@@search.browse.businessContext.infoModal.title:Business context`;
}
