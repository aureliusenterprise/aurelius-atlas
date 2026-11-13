import { ChangeDetectionStrategy, Component, ElementRef, input, signal, viewChild } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faBars, type IconDefinition } from "@fortawesome/free-solid-svg-icons";

/**
 * The Aurelius section navigation (`models4insight-details-navigation`):
 * the sticky up-dropdown (`dropdown.is-up.is-right`) around a Bulma
 * `menu`, so a details screen's section links stay reachable while
 * scrolling (UIC-18).
 *
 * The shell is presentational: the label arrives as an input (DD-136) and
 * the `li` items are projected content — the caller owns their links, and
 * the screen wires their behaviour (DD-191): the legacy
 * `DetailsNavigationItem` directive's scroll arrived as routerLink
 * anchors, the router scrolling to the fragment (DD-380, delivered by
 * DD-381). The toggle's open state is the component's: Bulma's CSS does
 * the rest.
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

    /** The toggle button — Escape hands the focus back to it (2.4.7). */
    protected readonly trigger = viewChild.required<ElementRef<HTMLButtonElement>>("trigger");

    /**
     * Toggle the dropdown, keeping the button's focus (DETAILS-NAV-FOCUS):
     * the legacy `toggleIsActive` blurred, which dropped keyboard readers
     * on the floor between clicks; the focus stays on the trigger, whose
     * `aria-expanded` is the state the reader announces.
     */
    protected onToggleClick(): void {
        this.isOpen.update((open) => !open);
    }

    /**
     * Escape closes an open dropdown and returns the focus to the trigger
     * (DETAILS-NAV-FOCUS, 2.4.7) — the menu's links are projected content,
     * so the keydown is caught on the dropdown wrapper, wherever it began.
     */
    protected onEscape(): void {
        if (this.isOpen()) {
            this.isOpen.set(false);
            this.trigger().nativeElement.focus();
        }
    }
}
