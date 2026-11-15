import {
    ChangeDetectionStrategy,
    Component,
    computed,
    ElementRef,
    HostListener,
    input,
    model,
    output,
    signal,
    viewChild,
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faFilter, faSort, faSortAlphaDown, faSortAlphaUp } from "@fortawesome/free-solid-svg-icons";

import { InfiniteScrollContainer } from "../infinite-scroll-container/infinite-scroll-container.component";
import { FacetItem, FacetList } from "../facet-list/facet-list.component";
import { nextInstanceId } from "../next-instance-id";
import { SearchField } from "../search-field/search-field.component";

/** One sort option of the section's select: its key and its label. */
export interface CardSortOption {
    /** The option's key — the caller's sort switch. */
    key: string;
    /** The option's label. The caller localises it. */
    label: string;
}

/**
 * One facet group of the section's filter popover (UIC-42, VCF-08):
 * the caller's group key, its localised title, and its rows. The part
 * renders every group through {@link FacetList} and echoes a tick with
 * the group key; the rows' values, counts, and ticks are the store's
 * (VCF-09..VCF-12 live with the caller).
 */
export interface CardFacetGroup {
    /** The group's key — echoed on {@link DetailsCardSection.facetToggled}. */
    readonly key: string;
    /** The menu label. The caller localises it. */
    readonly title: string;
    /** The group's rows, in the caller's order (UIC-33's item shape). */
    readonly items: readonly FacetItem[];
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
    imports: [FacetList, FontAwesomeModule, FormsModule, InfiniteScrollContainer, SearchField],
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

    /**
     * The popover's facet groups (VCF-08, DD-618). An empty set renders
     * the popover's "No filters available." line (SDX-03's empty state,
     * VCF-10) — the funnel still opens, as the legacy's did.
     */
    readonly facets = input<readonly CardFacetGroup[]>([]);

    /** Accessible name of the funnel button — the "Filter"
     * (`search.details.components.detailsCardsList.filter`). The caller
     * localises it. */
    readonly filterLabel = input("Filter");

    /** The popover's line when it has no groups — the catalogue's
     * "No filters available." (`search.components.filter.notAvailable`).
     * The caller localises it. */
    readonly notAvailableLabel = input("No filters available.");

    /** The facet menu's show-more label (UIC-34). The caller localises it. */
    readonly showMoreLabel = input("Show more");

    /** The facet menu's show-less label (UIC-34). The caller localises it. */
    readonly showLessLabel = input("Show less");

    /**
     * Whether the funnel marks the icon active (the legacy `is-primary`,
     * the demo's primary-tinted glyph): the caller's keyword, facet
     * selection, sort key, or sort direction differs from its default
     * (VCF-08 — the legacy `isEqual`-on-the-query-object test).
     */
    readonly filterActive = input(false);

    /** A page is in flight — the scroll container's spinner (UIC-22). */
    readonly loading = input(false);

    /** Whether the paged set is exhausted — the scroll container's stop (DET-22). */
    readonly allLoaded = input(true);

    /** The scroll container's load label. The caller localises it. */
    readonly loadLabel = input("Load next page...");

    /** Emits on a count-line click: reset filter and sort (DET-20, the legacy's unconditional reset). */
    readonly resetRequested = output<void>();

    /** Emits when a popover row is ticked or unticked: the group's key
     * with the {@link FacetList.toggled} payload (VCF-11). */
    readonly facetToggled = output<{ group: string; value: string; checked: boolean }>();

    /** Emits when the direction button toggles (DET-21). */
    readonly sortDirectionToggled = output<void>();

    /** Emits on a keyword submit or clear (the UIC-21 contract, DET-20). */
    readonly querySubmitted = output<string | null>();

    /** Emits when the sentinel or the button asks for the next page (DET-22). */
    readonly nextPage = output<void>();

    /** The select's glyph — the legacy sorting component's `faSort`. */
    protected readonly faSort = faSort;

    /** The funnel button's glyph — the legacy dropdown's `faFilter`. */
    protected readonly faFilter = faFilter;

    /** The direction button's glyph (DET-21): the legacy sorting
     * component's alphabetical pair, in the legacy's pairing — ascending
     * carries `faSortAlphaDown` and descending `faSortAlphaUp`
     * (`sortDirection.value ? faSortDown : faSortUp` over its form, whose
     * value is `direction === "asc"`). The names read backwards to us:
     * FontAwesome's glyph is named for the direction of the alphabet it
     * lists — ascending is A-to-Z, "alpha down" — so the swap is the
     * demo's, not a bug. (The plain faSortUp/faSortDown arrows were the
     * first cut's guess; the demo's button carries the A-with-arrow
     * glyph, measured on the live page.) */
    protected readonly directionIcon = computed(() => (this.sortDescending() ? faSortAlphaUp : faSortAlphaDown));

    /** Whether the facet popover is open — this part's own state (DD-618:
     * the part owns only the opening). */
    protected readonly facetsOpen = signal(false);

    /** The dropdown's id — unique per instance, the `aria-controls` pair. */
    protected readonly dropdownId = `aurelius-card-section-filter-${nextInstanceId()}`;

    /** The funnel button element — focus returns here when a click outside closes. */
    private readonly funnel = viewChild<ElementRef<HTMLButtonElement>>("funnel");

    /** A click outside the open dropdown closes it (the popover's contract). */
    @HostListener("document:click", ["$event"])
    protected onDocumentClick(event: MouseEvent): void {
        if (!this.facetsOpen()) {
            return;
        }
        const box = this.funnel()?.nativeElement.closest(".dropdown");
        if (box instanceof HTMLElement && !box.contains(event.target as Node)) {
            this.facetsOpen.set(false);
        }
    }

    /** Escape closes the open popover and returns focus to the funnel (the dropdown keyboard path). */
    @HostListener("document:keydown.escape")
    protected onEscape(): void {
        if (!this.facetsOpen()) {
            return;
        }
        this.facetsOpen.set(false);
        this.funnel()?.nativeElement.focus();
    }

    /** The funnel button's activation: open and close the popover.
     * Bulma's `.is-hoverable` opens on hover through CSS; the button
     * carries the click and keyboard path (DV-169's note) and marks
     * `aria-expanded`.
     */
    protected toggleFacets(): void {
        this.facetsOpen.update((open) => !open);
    }

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
