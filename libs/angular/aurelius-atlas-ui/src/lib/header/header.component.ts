import { CommonModule } from "@angular/common";
import { booleanAttribute, ChangeDetectionStrategy, Component, input, model } from "@angular/core";

@Component({
    selector: "aurelius-atlas-ui-header",
    imports: [CommonModule],
    templateUrl: "./header.component.html",
    styleUrl: "./header.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Header {
    /**
     * Whether the header menu is expanded or not.
     */
    readonly expanded = model(false);

    /**
     * The logo to display in the header.
     */
    readonly logo = input<string>();

    /**
     * The CSS class on the logo image. The Aurelius chrome sizes its brand
     * mark through the `.logo` rule in this component's styles (max-width
     * 150px, max-height 50px — the legacy navbar anatomy, SHM-02);
     * consumers style logos their own way by passing a different class.
     */
    readonly logoCssClass = input<string>("logo");

    /**
     * Pin the navbar to the top of the viewport (`is-fixed-top`). The
     * legacy chrome is pinned; pair it with `has-navbar-fixed-top` on the
     * body so content starts below the bar (SHM-05).
     */
    readonly fixed = input(false, { transform: booleanAttribute });

    /**
     * The name of the application to display in the header.
     */
    readonly name = input<string>();

    /**
     * Close the header menu.
     */
    close(): void {
        this.expanded.set(false);
    }

    /**
     * Open the header menu.
     */
    open(): void {
        this.expanded.set(true);
    }

    /**
     * Open or close the header menu based on its current state.
     */
    toggle(): void {
        this.expanded.update((expanded) => !expanded);
    }
}
