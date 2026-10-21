import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, computed, input, output } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { type IconDefinition } from "@fortawesome/free-solid-svg-icons";

/**
 * The Bulma card behind every Aurelius details screen (`models4insight-details-card`),
 * ported as a pure shell (DD-066): the legacy card pulled the entity from a
 * details service, chose a per-type body via `cardsByType`/`ngComponentOutlet`,
 * and navigated on a title click. Here the title, badge, body and quality
 * column are inputs and content projection, and a title click emits
 * `entityClicked` — routing is the app's (7.6).
 *
 * The type-name badge is inlined (the legacy `entity-type-name` → `type-name`
 * chain, minus its service): icon, `typeAlias ?? typeName`, and the optional
 * base-type suffix.
 */
@Component({
    selector: "aurelius-atlas-ui-entity-card",
    imports: [CommonModule, FontAwesomeModule],
    templateUrl: "./entity-card.component.html",
    styleUrl: "./entity-card.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityCard {
    /**
     * The entity's unique id — the payload of `entityClicked`.
     */
    readonly guid = input<string | undefined>(undefined);

    /**
     * The entity name shown as the card title.
     */
    readonly name = input<string | undefined>(undefined);

    /**
     * The entity type name, shown in the badge when no alias is given.
     */
    readonly typeName = input<string | undefined>(undefined);

    /**
     * The type alias: the display name overriding the type name, as the
     * legacy `typeAlias` attribute did.
     */
    readonly typeAlias = input<string | undefined>(undefined);

    /**
     * The badge's icon. The legacy card resolved it from `iconsByType` —
     * application metadata, so it arrives as an input (UIC-15).
     */
    readonly typeIcon = input<IconDefinition | undefined>(undefined);

    /**
     * The colour class of the badge's icon: business, technical, technical-process, meta.
     */
    readonly typeIconClass = input<string | undefined>(undefined);

    /**
     * Whether to display the base type in parentheses when an alias is given.
     */
    readonly showBaseTypeName = input(false);

    /**
     * Whether to display the badge's icon.
     */
    readonly showIcon = input(true);

    /**
     * Whether to display the badge's type name.
     */
    readonly showTypeName = input(true);

    /**
     * Whether to render the (empty) quality column, as the legacy
     * `SHOW_GOV_QUALITY` injection did. It projects `[card-quality]`.
     */
    readonly showQuality = input(true);

    /**
     * Swap the body for the loading row — the legacy card's
     * `isRetrievingDetails$` state.
     */
    readonly loading = input(false);

    /**
     * The loading row's label. The caller localises it; the Aurelius
     * string was 'Loading {name}...', interpolated here when a name is set.
     */
    readonly loadingLabel = input("Loading");

    /**
     * The loading row's label with the name interpolated — the legacy
     * `search.details.loading` ('Loading {{name}}...'), rendered as
     * '<label> <name>...' when a name is set, and the bare label when not.
     */
    protected readonly loadingText = computed(() => {
        const label = this.loadingLabel();
        const name = this.name();
        return name ? `${label} ${name}...` : label;
    });

    /**
     * Emits the guid when the title is activated. The app routes; the lib does not (DD-066).
     */
    readonly entityClicked = output<string>();

    /**
     * Handle a title activation — the legacy `onEntityClick`, turned into an
     * emit (the anchor's `href` is the keyboard path, so the default
     * navigation is cancelled).
     * @param event The click event.
     */
    protected onEntityClick(event: Event): void {
        event.preventDefault();
        const guid = this.guid();
        if (guid !== undefined) {
            this.entityClicked.emit(guid);
        }
    }
}
