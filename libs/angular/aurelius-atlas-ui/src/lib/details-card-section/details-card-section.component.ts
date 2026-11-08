import { ChangeDetectionStrategy, Component, computed, input, model, output } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faSort, faSortDown, faSortUp } from "@fortawesome/free-solid-svg-icons";

import { InfiniteScrollContainer } from "../infinite-scroll-container/infinite-scroll-container.component";
import { SearchField } from "../search-field/search-field.component";

/** One sort option of the section's select: its key and its label. */
export interface CardSortOption {
    /** The option's key — the caller's sort switch. */
    key: string;
    /** The option's label. The caller localises it. */
    label: string;
}

/**
 * The Aurelius card section (`models4insight-details-cards-list`, UIC-27,
 * DET-17..DET-22): the box title, the `N result(s)` count line — the
 * legacy's always-underlined reset link (DD-374), while filtered it shows
 * the filtered count — the sort select with its direction button,
 * the keyword input, and the paged card grid. Ported dumb (WBP-04): the
 * legacy read its App Search store and re-queried per interaction; here
 * every state is an input, every interaction an emit or a model, and the
 * app's store owns seed, resolve, filter, sort, and page.
 *
 * The chrome strings ride in as localised inputs (DD-136): the placeholder
 * and the "result(s)" word are Aurelius keys the caller carries; the sort
 * options and labels are the caller's set. The grid projects the caller's
 * cards — the section lays them out, the caller builds them.
 */
@Component({
    selector: "aurelius-atlas-ui-details-card-section",
    imports: [FontAwesomeModule, FormsModule, InfiniteScrollContainer, SearchField],
    templateUrl: "./details-card-section.component.html",
    styleUrl: "./details-card-section.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DetailsCardSection {
    /** The section's title. The caller localises it. */
    readonly title = input("");

    /** The section count — the seed length (DET-17), shown beside "result(s)". */
    readonly count = input(0);

    /** The sort options; the first is the default (Relevance, DET-21). */
    readonly sortOptions = input<CardSortOption[]>([]);

    /** The selected sort key. Two-way bindable; `null` is the default sort. */
    readonly sort = model<string | null>(null);

    /** Whether the sort direction is descending (the legacy toggle). */
    readonly sortDescending = input(false);

    /** The keyword input's model — the caller clears it on reset (DET-20). */
    readonly query = model<string | null>(null);

    /** The keyword input's placeholder. The caller localises it. */
    readonly placeholder = input("Search for keywords");

    /** Accessible name of the sort select. The caller localises it; the
     * Aurelius select carried none (DD-136's chrome rule, the search
     * field's submit/clear labels). */
    readonly sortLabel = input("Sort by");

    /** Accessible name of the direction button. The caller localises it;
     * the Aurelius button carried none (DD-136's chrome rule). */
    readonly directionLabel = input("Sort direction");

    /** The word beside the count — the Aurelius "result(s)"
     * (`search.details.components.detailsCardsList.results`). The caller
     * localises it. */
    readonly resultWord = input("result(s)");

    /** Whether a keyword filter is applied: the count line shows the filtered count. */
    readonly filtered = input(false);

    /** The count shown while filtered — the matched cards (DET-20). */
    readonly filteredCount = input(0);

    /** A page is in flight — the scroll container's spinner (UIC-22). */
    readonly loading = input(false);

    /** Whether the paged set is exhausted — the scroll container's stop (DET-22). */
    readonly allLoaded = input(true);

    /** The scroll container's load label. The caller localises it. */
    readonly loadLabel = input("Load next page...");

    /** Emits on a count-line click: reset filter and sort (DET-20, the legacy's unconditional reset). */
    readonly resetRequested = output<void>();

    /** Emits when the direction button toggles (DET-21). */
    readonly sortDirectionToggled = output<void>();

    /** Emits on a keyword submit or clear (the UIC-21 contract, DET-20). */
    readonly querySubmitted = output<string | null>();

    /** Emits when the sentinel or the button asks for the next page (DET-22). */
    readonly nextPage = output<void>();

    /** The select's glyph — the legacy sorting component's `faSort`. */
    protected readonly faSort = faSort;

    /** The direction button's glyph: down while descending, up otherwise. */
    protected readonly directionIcon = computed(() => (this.sortDescending() ? faSortDown : faSortUp));

    /**
     * Handle a direction-button click — the legacy `toggleSortDirection`,
     * turned into an emit. The button is a real `button` so the keyboard
     * path is native.
     */
    protected onDirectionClick(): void {
        this.sortDirectionToggled.emit();
    }

    /**
     * Handle a count-line activation — the legacy reset link
     * (`reset-search`), clickable in every state; an unfiltered reset is a
     * no-op. The href="#" is the keyboard path; the click cancels it and
     * emits.
     * @param event The click event.
     */
    protected onCountClick(event: Event): void {
        event.preventDefault();
        this.resetRequested.emit();
    }
}
