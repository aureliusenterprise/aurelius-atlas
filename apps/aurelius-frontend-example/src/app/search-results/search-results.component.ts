import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faEdit } from "@fortawesome/free-solid-svg-icons";
import { Card, Pagination } from "aurelius-atlas-ui";
import { EntityService } from "../services/entity.service";
import { SearchService } from "../services/search.service";

@Component({
    imports: [Card, FontAwesomeModule, Pagination],
    selector: "aurelius-frontend-example-search-results",
    templateUrl: "./search-results.component.html",
    styleUrl: "./search-results.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchResults {
    /**
     * The entity service is used to control the current entity being edited.
     */
    protected readonly entityService = inject(EntityService);

    /**
     * The search service is used to access the current search results.
     */
    protected readonly searchService = inject(SearchService);

    /**
     * FontAwesome icons used in the component.
     */
    protected readonly faEdit = faEdit;
}
