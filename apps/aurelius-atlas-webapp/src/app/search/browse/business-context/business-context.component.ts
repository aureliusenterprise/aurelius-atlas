import { ChangeDetectionStrategy, Component, inject, model } from "@angular/core";
import { Router } from "@angular/router";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCompass, faInfoCircle, faProjectDiagram, faSearch } from "@fortawesome/free-solid-svg-icons";
import { SearchField } from "aurelius-atlas-ui";

import { SearchState } from "../../search-state";
import { BusinessContextInfoModal } from "./business-context-info-modal.component";

/**
 * The Aurelius business-context card: title, info icon, the two explaining
 * articles (searching and exploring), and the card's search field + explore
 * button (SRH-08, DD-143 superseding BRW-06): the field submits through
 * the layout's search store, the button explores the AtlasGlossary type —
 * the Atlas model's reading of the legacy's m4i data-domain filter (DV-84).
 */
@Component({
    imports: [BusinessContextInfoModal, FontAwesomeModule, SearchField],
    selector: "aurelius-atlas-webapp-business-context",
    templateUrl: "./business-context.component.html",
    styleUrl: "./business-context.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BusinessContext {
    private readonly router = inject(Router);

    private readonly search = inject(SearchState);

    /**
     * Open state of the card's info modal: the card owns it, the modal
     * closes itself through the two-way binding (BRW-05).
     */
    readonly infoModalActive = model(false);

    protected readonly faCompass = faCompass;
    protected readonly faInfoCircle = faInfoCircle;
    protected readonly faProjectDiagram = faProjectDiagram;
    protected readonly faSearch = faSearch;

    /**
     * Accessible name of the info button — the modal's title, as the Aurelius
     * icon link had none (BRW-03).
     */
    protected readonly infoTitle = $localize`:@@search.browse.businessContext.infoModal.title:Business context`;

    /** The card's field placeholder (SRH-08, `search.browse.businessContext`). */
    protected readonly searchPlaceholder = $localize`:@@search.browse.businessContext.searchPlaceholder:Search for keywords`;

    /** The explore button's label (SRH-08, the legacy `directToConceptual`). */
    protected readonly exploreLabel = $localize`:@@search.browse.businessContext.exploreButton:Start browsing data domains`;

    /**
     * The card's field submit (SRH-08, the legacy `onQuerySubmitted`): the
     * query rides the URL, the card's kind rides the session store.
     * @param query the submitted query, `null` for a cleared field
     */
    protected onQuerySubmitted(query: string | null): void {
        this.search.run(query);
        void this.router.navigate(["/search/results"], { queryParams: { query: query || null } });
    }

    /**
     * The explore button (SRH-08, DV-84): the empty query and the
     * AtlasGlossary type filter — the legacy's data domains are Atlas's
     * glossaries (the glossary model ships no plain `Glossary` type, so the
     * server would answer the explore `UNKNOWN_TYPENAME`, SRC-03).
     */
    protected explore(): void {
        this.search.explore("AtlasGlossary");
        void this.router.navigate(["/search/results"]);
    }
}
