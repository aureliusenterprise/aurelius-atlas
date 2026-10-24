import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, input, model } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";

@Component({
    selector: "aurelius-atlas-ui-accordion",
    imports: [CommonModule, FontAwesomeModule],
    templateUrl: "./accordion.component.html",
    styleUrl: "./accordion.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Accordion {
    /**
     * Whether the accordion is expanded or not.
     */
    readonly expanded = model(false);

    /**
     * Accessible name of the toggle button. The legacy Aurelius component
     * read this from the `components.accordion.toggleContent` dictionary key;
     * the template's `i18n` unit is the same id (DD-136), and a caller with a
     * more specific name (a per-screen label) overrides it here.
     */
    readonly ariaLabel = input("Toggle content");

    /**
     * The FontAwesome icons used in the accordion.
     */
    protected readonly faChevronDown = faChevronDown;
    protected readonly faChevronUp = faChevronUp;

    /**
     * Set the accordion to a collapsed state.
     */
    collapse() {
        this.expanded.set(false);
    }

    /**
     * Set the accordion to an expanded state.
     */
    expand() {
        this.expanded.set(true);
    }

    /**
     * Toggle the accordion state. If it is expanded, it will collapse; if it is collapsed, it will expand.
     */
    toggle() {
        this.expanded.update((expanded) => !expanded);
    }
}
