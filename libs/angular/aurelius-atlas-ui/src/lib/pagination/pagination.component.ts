/// <reference types="@angular/localize" />
import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, computed, input, model } from "@angular/core";

/** Instance counter for the range line's id (TABLE-004): two bars on one page must not share it. */
let paginationInstances = 0;

@Component({
    selector: "aurelius-atlas-ui-pagination",
    imports: [CommonModule],
    templateUrl: "./pagination.component.html",
    styleUrls: ["./pagination.component.scss"],
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Pagination {
    /**
     * TABLE-004: per-instance id of the "Showing X to Y of Z" line, so a
     * page with two bars still has unique ids.
     */
    readonly rangeId = `aurelius-pagination-range-${(paginationInstances += 1)}`;

    /**
     * The index of the current page (0-based).
     */
    readonly pageIndex = model(0);

    /**
     * The number of items to display per page.
     */
    readonly pageSize = input(10);

    /**
     * The total number of items across all pages.
     */
    readonly totalItems = input(0);

    /**
     * The total number of pages based on the length of the items and the page size.
     */
    readonly totalPages = computed(() => {
        return Math.ceil(this.totalItems() / this.pageSize());
    });

    /**
     * The current page number (1-based) for display purposes.
     */
    readonly currentPageDisplay = computed(() => {
        const totalPages = this.totalPages();
        if (totalPages === 0) {
            return 0;
        }
        return Math.min(this.pageIndex() + 1, totalPages);
    });

    /**
     * The first item of the current page, 1-based — the start of the
     * "Showing X to Y of Z" line (TABLE-004, WCAG 1.3.1). With no items the
     * line is hidden, so the empty range is never shown.
     */
    readonly rangeStart = computed(() => (this.currentPageDisplay() - 1) * this.pageSize() + 1);

    /**
     * The last item of the current page, 1-based, clamped to the total.
     */
    readonly rangeEnd = computed(() => Math.min(this.currentPageDisplay() * this.pageSize(), this.totalItems()));

    /**
     * The visible range line's text (TABLE-004): localised here, with named
     * placeholders, so the dictionary's `{{start}}`-style markers match.
     */
    readonly rangeText = computed(
        () =>
            $localize`:@@components.pagination.range:Showing ${this.rangeStart()}:start: to ${this.rangeEnd()}:end: of ${this.totalItems()}:total: results`,
    );

    /**
     * TABLE-004 (WCAG 4.1.3): the persistent live region's text — the page
     * position. Empty while there are no items; a page change swaps the
     * text, which is what a live region announces. The region itself never
     * leaves the DOM.
     */
    readonly pageAnnouncement = computed(() =>
        this.totalPages() === 0
            ? ""
            : $localize`:@@components.pagination.pageOf:Page ${this.currentPageDisplay()}:page: of ${this.totalPages()}:total:`,
    );

    /**
     * The accessible name of the current page's button (TABLE-004's i18n
     * marker — the expression was a bare concat before).
     * @param token The 1-based page token.
     * @returns The localised label.
     */
    pageLabel(token: number): string {
        return $localize`:@@components.pagination.page:Page ${token}:page:`;
    }

    /**
     * The accessible name of a non-current page's button.
     * @param token The 1-based page token.
     * @returns The localised label.
     */
    goToPageLabel(token: number): string {
        return $localize`:@@components.pagination.goToPage:Go to page ${token}:page:`;
    }

    /**
     * An array of page tokens to display in the pagination controls.
     * This includes page numbers and ellipses for skipped pages.
     */
    readonly pageTokens = computed(() => {
        return this.totalPages() <= 7 ? this.generateShortFormPageTokens() : this.generateLongFormPageTokens();
    });

    /**
     * Whether there is a previous page available.
     */
    readonly hasPreviousPage = computed(() => {
        return this.pageIndex() > 0;
    });

    /**
     * Whether there is a next page available.
     */
    readonly hasNextPage = computed(() => {
        return this.pageIndex() < this.totalPages() - 1;
    });

    /**
     * Navigate to a specific page by its index (0-based).
     * @param index The index of the page to navigate to.
     */
    goToPage(index: number) {
        if (index < 0 || index >= this.totalPages()) {
            return;
        }
        this.pageIndex.set(index);
    }

    /**
     * Navigate to the next page.
     */
    nextPage() {
        this.goToPage(this.pageIndex() + 1);
    }

    /**
     * Navigate to the previous page.
     */
    previousPage() {
        this.goToPage(this.pageIndex() - 1);
    }

    /**
     * Generate page tokens for the pagination controls when the total number of pages is small.
     */
    private generateShortFormPageTokens(): Array<number> {
        return Array.from({ length: this.totalPages() }, (_, index) => index + 1);
    }

    /**
     * Generate page tokens for the pagination controls when the total number of pages is large, including ellipses for skipped pages.
     */
    private generateLongFormPageTokens(): Array<number | "ellipsis"> {
        const totalPages = this.totalPages();
        const currentPage = this.currentPageDisplay();

        // Always include the first page
        const tokens: Array<number | "ellipsis"> = [1];

        // Determine the range of page numbers to display around the current page
        const middleStart = Math.max(2, currentPage - 1);
        const middleEnd = Math.min(totalPages - 1, currentPage + 1);

        // Add an ellipsis if there is a gap between the first page and the start of the middle range
        if (middleStart > 2) {
            tokens.push("ellipsis");
        }

        // Add the page numbers in the middle range
        for (let page = middleStart; page <= middleEnd; page += 1) {
            tokens.push(page);
        }

        // Add an ellipsis if there is a gap between the end of the middle range and the last page
        if (middleEnd < totalPages - 1) {
            tokens.push("ellipsis");
        }

        // Always include the last page
        tokens.push(totalPages);

        return tokens;
    }
}
