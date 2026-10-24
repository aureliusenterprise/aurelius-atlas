import { ChangeDetectionStrategy, Component, input, signal } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faBars, type IconDefinition } from "@fortawesome/free-solid-svg-icons";

/**
 * The Aurelius section navigation (`models4insight-details-navigation`):
 * the sticky up-dropdown (`dropdown.is-up.is-right`) around a Bulma
 * `menu`, so a details screen's section links stay reachable while
 * scrolling (UIC-18).
 *
 * The shell is presentational: the label arrives as an input (DD-136) and
 * the `li` items are projected content — their hrefs are the app's
 * anchors, and the Aurelius `DetailsNavigationItem` directive
 * (smooth-scroll, a third-party dep) stays app-side, wiring the items the
 * shell renders (DD-191). The toggle's open state is the component's:
 * Bulma's CSS does the rest.
 */
@Component({
    selector: "aurelius-atlas-ui-details-navigation",
    imports: [FontAwesomeModule],
    templateUrl: "./details-navigation.component.html",
    styleUrl: "./details-navigation.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DetailsNavigation {
    /**
     * The menu label. The Aurelius default, 'Details'
     * (`search.details.components.navigation.details`).
     */
    readonly label = input("Details");

    /**
     * The toggle's glyph — the legacy bars icon, chrome the component
     * owns, as the breadcrumbs own their warning icon (UIC-15).
     */
    readonly toggleIcon = input<IconDefinition>(faBars);

    /**
     * Accessible name of the toggle button. The Aurelius button carried
     * this literal.
     */
    readonly toggleLabel = input("navigation");

    /**
     * Whether the dropdown is open — toggled by the button, the Bulma
     * `is-active` class.
     */
    protected readonly isOpen = signal(false);

    /**
     * Toggle the dropdown and drop the button's focus, as the legacy
     * `toggleIsActive` blurred — the focus ring is not the open state.
     */
    protected onToggleClick(event: Event): void {
        this.isOpen.update((open) => !open);
        (event.currentTarget as HTMLButtonElement).blur();
    }
}
