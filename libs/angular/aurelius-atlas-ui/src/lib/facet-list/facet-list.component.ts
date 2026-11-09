import { ChangeDetectionStrategy, Component, input, output, signal } from "@angular/core";

/**
 * One facet value as {@link FacetList} renders it — the caller's mapping of
 * a server facet entry to its display row (UIC-33).
 */
export type FacetItem = {
    /** The wire value: echoed back on {@link FacetList.toggled}, never the label. */
    readonly value: string;
    /** The display label (the caller localises it — DD-136's rule). */
    readonly label: string;
    /** The count to show in parentheses; `undefined` renders none. */
    readonly count?: number;
    /** Whether the row is checked (the caller's selection, SDX-04). */
    readonly checked?: boolean;
};

/**
 * The search's filter menus (UIC-33..35, SDX-04/05): the legacy
 * `filter`/`facet`/`check-box` trio (`.scratch/aurelius`) as one dumb
 * component — the legacy split was one component per facet and one per
 * checkbox because each carried its own store service; here every row is
 * data the caller passes and the one event is {@link toggled} (WBP-02:
 * signals in, output out, no services).
 *
 * The markup is the legacy `facet.component.html`: a Bulma `menu` per facet
 * (`p.menu-label` + `ul.menu-list`), each row the value's label and its
 * count in parentheses (`check-box.component.html`'s text, minus its form
 * control). With {@link selectable} a row is a `label.checkbox` over a real
 * checkbox and a tick emits {@link toggled} with the item's wire `value`
 * (the legacy `updateFilterSelection` contract); without it the row is
 * plain text — the read-only facets of SDX-05 render through the same
 * component. Past five values the list carries the legacy show-more link
 * (`facet.component.ts`'s `slice: 0 : (showMore ? 1000 : 5)`); showing all
 * is this component's own state, like the legacy's.
 *
 * The title and the show-more labels are caller-supplied and localised
 * (DD-136, the UIC-21 rule); a facet with no items renders nothing, so the
 * caller passes only non-empty facets (SDX-03 — the legacy `FilterService`
 * dropped empty facets before this component ever saw them).
 */
@Component({
    imports: [],
    selector: "aurelius-atlas-ui-facet-list",
    templateUrl: "./facet-list.component.html",
    styleUrl: "./facet-list.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FacetList {
    /** The facet's title, rendered as the menu label (the caller's `@@search.components.filter.*`). */
    readonly title = input("");

    /** The facet's values, in the caller's order (UIC-33). */
    readonly items = input<readonly FacetItem[]>([]);

    /**
     * Whether the rows are checkboxes (the type facet, SDX-04). Off renders
     * read-only rows (SDX-05) — the same data, no affordance.
     */
    readonly selectable = input(false);

    /** The "Show more" link label (the caller localises it, UIC-34). */
    readonly showMoreLabel = input("Show more");

    /** The "Show less" link label (the caller localises it, UIC-34). */
    readonly showLessLabel = input("Show less");

    /**
     * A row was ticked or unticked: the item's wire `value` and the new
     * state (the legacy `updateFilterSelection(selectionState)` contract,
     * UIC-34). Selectable rows only.
     */
    readonly toggled = output<{ value: string; checked: boolean }>();

    /** The legacy `facet.component.ts`'s five-value slice. */
    protected readonly visibleCount = 5;

    /** The legacy `showMore` flag as a signal (WBP-02): showing every row is the component's own state. */
    protected readonly showAll = signal(false);

    /**
     * A checkbox changed (UIC-34): echo the wire value and the new state.
     * @param item the row's data
     * @param event the checkbox's change event
     */
    protected onToggle(item: FacetItem, event: Event): void {
        this.toggled.emit({ value: item.value, checked: (event.target as HTMLInputElement).checked });
    }

    /** Flip the legacy show-more link (UIC-34). */
    protected toggleShowMore(): void {
        this.showAll.update((shown) => !shown);
    }
}
