import { ChangeDetectionStrategy, Component, inject, model } from "@angular/core";
import { Router } from "@angular/router";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCompass, faInfoCircle, faSearch, faUser } from "@fortawesome/free-solid-svg-icons";
import { SearchField } from "aurelius-atlas-ui";

import { SearchState } from "../../search-state";
import { Session } from "../../../shell/session.service";
import { GovernanceResponsibilitiesInfoModal } from "./governance-responsibilities-info-modal.component";

/**
 * The Aurelius governance-responsibilities card: title, info icon, the two
 * explaining articles, and the card's search field + explore button
 * (SRH-08, DD-143). The field submits a plain query — Atlas has no Person
 * type for the legacy's `m4i_person` filter to ride (DV-84) — and the
 * button is the legacy `directToUser`: the signed-in user's e-mail from the
 * Keycloak token, searched as the query term.
 */
@Component({
    imports: [FontAwesomeModule, GovernanceResponsibilitiesInfoModal, SearchField],
    selector: "aurelius-atlas-webapp-governance-responsibilities",
    templateUrl: "./governance-responsibilities.component.html",
    styleUrl: "./governance-responsibilities.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GovernanceResponsibilities {
    private readonly router = inject(Router);

    private readonly search = inject(SearchState);

    private readonly session = inject(Session);

    /**
     * Open state of the card's info modal: the card owns it, the modal
     * closes itself through the two-way binding (BRW-05).
     */
    readonly infoModalActive = model(false);

    protected readonly faCompass = faCompass;
    protected readonly faInfoCircle = faInfoCircle;
    protected readonly faSearch = faSearch;
    protected readonly faUser = faUser;

    /**
     * Accessible name of the info button — the modal's title, as the Aurelius
     * icon link had none (BRW-03).
     */
    protected readonly infoTitle = $localize`:@@search.browse.governanceContext.infoModal.title:Data governance organization`;

    /** The card's field placeholder (SRH-08, `search.browse.governanceContext`). */
    protected readonly searchPlaceholder = $localize`:@@search.browse.governanceContext.searchPlaceholder:Search for keywords`;

    /** The explore button's label (SRH-08, the legacy `directToUser`). */
    protected readonly exploreLabel = $localize`:@@search.browse.governanceContext.exploreButton:Start browsing people`;

    /**
     * The card's field submit (SRH-08): a plain query — DV-84 drops the
     * legacy's Person-type filter, the e-mail/name term is what Atlas can
     * match.
     * @param query the submitted query, `null` for a cleared field
     */
    protected onQuerySubmitted(query: string | null): void {
        this.search.run(query);
        void this.router.navigate(["/search/results"], { queryParams: { query: query || null } });
    }

    /**
     * The explore button — the legacy `directToUser` (SRH-08, DV-84): the
     * signed-in user's e-mail is the query, carried in the URL, the way the
     * legacy navigated it.
     */
    protected explore(): void {
        const email = this.session.email();
        this.search.run(email || null);
        void this.router.navigate(["/search/results"], { queryParams: { query: email || null } });
    }
}
