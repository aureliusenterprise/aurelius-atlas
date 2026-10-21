import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, computed, input, output } from "@angular/core";

/**
 * One link of a link-array property value — the legacy
 * `{ guid, displayText }` shape the details properties table carried.
 */
export interface PropertiesItemLink {
    /** The unique id of the linked entity. */
    guid: string;
    /** The link's display text. */
    displayText: string;
}

/**
 * The legacy details property-value renderer (`models4insight-properties-item`):
 * a string/number/boolean title-cased, an array of `{ guid, displayText }`
 * links as anchors, an empty array as the N/A label, and anything else as
 * nothing — the legacy component's three-way `defineTypes` split.
 *
 * The legacy anchors navigated to `search/details/{guid}`; these emit
 * `itemClicked` and the app routes (DD-066, same reasoning as the card).
 */
@Component({
    selector: "aurelius-atlas-ui-properties-item",
    imports: [CommonModule],
    templateUrl: "./properties-item.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PropertiesItem {
    /**
     * The property value: a string, number, boolean, array of links, or (renders
     * nothing) any other object.
     */
    readonly value = input<string | number | boolean | PropertiesItemLink[] | null | undefined>(undefined);

    /**
     * The label for an empty link array. The Aurelius component rendered the
     * literal 'N/A'; the caller localises.
     */
    readonly emptyLabel = input("N/A");

    /**
     * Emits the guid of a clicked link. The app routes; the lib does not.
     */
    readonly itemClicked = output<string>();

    /**
     * The value as a string-like, as the legacy `isStringLike`: a string
     * passes through, a number/boolean stringifies, anything else is `null`.
     */
    protected readonly isStringLike = computed<string | null>(() => {
        const value = this.value();
        if (typeof value === "string") {
            return value;
        }
        if (typeof value === "number" || typeof value === "boolean") {
            return String(value);
        }
        return null;
    });

    /**
     * The value as a link array, as the legacy `isObjectLike`: an array
     * passes through, anything else is `null`.
     */
    protected readonly isLinkArray = computed<PropertiesItemLink[] | null>(() =>
        Array.isArray(this.value()) ? (this.value() as PropertiesItemLink[]) : null,
    );

    /**
     * Handle a link activation — the legacy `openDetails`, turned into an
     * emit (the anchor's `href` is the keyboard path, so the default
     * navigation is cancelled).
     * @param event The click event.
     * @param link The link activated.
     */
    protected onItemClick(event: Event, link: PropertiesItemLink): void {
        event.preventDefault();
        this.itemClicked.emit(link.guid);
    }
}
