import { ChangeDetectionStrategy, Component, inject, model } from "@angular/core";
import { Router } from "@angular/router";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCompass, faInfoCircle, faSearch, faServer } from "@fortawesome/free-solid-svg-icons";
import { SearchField } from "aurelius-atlas-ui";

import { SearchState } from "../../search-state";
import { TechnicalContextInfoModal } from "./technical-context-info-modal.component";

/**
 * The Aurelius technical-context card: title, info icon, the two explaining
 * articles, and the card's search field + explore button (SRH-08, DD-143):
 * the field submits through the layout's search store, the button explores
 * the Infrastructure type — the Atlas base-model reading of the legacy's
 * m4i system filter (DV-84).
 */
@Component({
    imports: [FontAwesomeModule, SearchField, TechnicalContextInfoModal],
    selector: "aurelius-atlas-webapp-technical-context",
    templateUrl: "./technical-context.component.html",
    styleUrl: "./technical-context.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TechnicalContext {
    private readonly router = inject(Router);

    private readonly search = inject(SearchState);

    /**
     * Open state of the card's info modal: the card owns it, the modal
     * closes itself through the two-way binding (BRW-05).
     */
    readonly infoModalActive = model(false);

    protected readonly faCompass = faCompass;
    protected readonly faInfoCircle = faInfoCircle;
    protected readonly faSearch = faSearch;
    protected readonly faServer = faServer;

    /**
     * Accessible name of the info button — the modal's title, as the Aurelius
     * icon link had none (BRW-03).
     */
    protected readonly infoTitle = $localize`:@@search.browse.technicalContext.infoModal.title:Technical context`;

    /** The card's field placeholder (SRH-08, `search.browse.technicalContext`). */
    protected readonly searchPlaceholder = $localize`:@@search.browse.technicalContext.searchPlaceholder:Search for keywords`;

    /** The explore button's label (SRH-08, the legacy `directToTechnical`). */
    protected readonly exploreLabel = $localize`:@@search.browse.technicalContext.exploreButton:Start browsing systems`;

    /**
     * The card's field submit (SRH-08, the legacy `onQuerySubmitted`).
     * @param query the submitted query, `null` for a cleared field
     */
    protected onQuerySubmitted(query: string | null): void {
        this.search.run(query);
        void this.router.navigate(["/search/results"], { queryParams: { query: query || null } });
    }

    /**
     * The explore button (SRH-08, DV-84): the empty query and the
     * Infrastructure type filter — the legacy's systems are Atlas's
     * infrastructure entities.
     */
    protected explore(): void {
        this.search.explore("Infrastructure");
        void this.router.navigate(["/search/results"]);
    }
}
