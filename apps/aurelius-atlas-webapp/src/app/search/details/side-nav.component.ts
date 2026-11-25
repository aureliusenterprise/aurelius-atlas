import { ChangeDetectionStrategy, Component, input } from "@angular/core";
import { RouterLink } from "@angular/router";
import { DetailsNavigation } from "aurelius-atlas-ui";

import type { NavDef } from "./sections/section.model";

/**
 * The side navigation of the details screen (DET-25): the 7.16 sticky circular
 * drop-up at the foot of the screen (UIC-18) holding the opened layout's anchors
 * as plain links, and the one `#properties-details` entry the default layout
 * takes when no entity has named a layout yet (DET-02). The legacy navigation
 * listed the rendered boxes in legacy order, and each entry is the `#href` path
 * the default layout takes — the anchor the box's own id answers (DD-381).
 *
 * A painter, not a store: the entries arrive from the screen (the layout row's
 * nav set), and `hasLayout` says whether a layout was named at all, which is
 * what picks the layout's set over the default's single entry. Each link is a
 * `routerLink` over the current route with the anchor as its fragment, so the
 * href stays a real address (the keyboard and middle-click path) while the
 * screen's own scroll effect does the scrolling (DD-191) — the part injects no
 * store, router, or client. It keeps the `.aurelius-details-nav` class the
 * tests and the e2e pin the menu through.
 */
@Component({
    imports: [DetailsNavigation, RouterLink],
    selector: "aurelius-atlas-webapp-details-side-nav",
    template: `
        <aurelius-atlas-ui-details-navigation class="aurelius-details-nav" [label]="label">
            <!-- The shell projects this list as-is (UIC-18), so the caller owns the
                 ul.menu-list container — the same shape the legacy pages wrote.
                 The layout's entries in legacy order (DET-25): the rendered box set
                 only, each entry the #href path the default layout takes. -->
            <ul class="menu-list">
                @if (hasLayout()) {
                    @for (entry of entries(); track entry.anchor) {
                        <li>
                            <a [routerLink]="[]" [fragment]="entry.anchor">{{ entry.label }}</a>
                        </li>
                    }
                } @else {
                    <li>
                        <a [routerLink]="[]" fragment="properties-details" i18n="@@search.details.default.properties"
                            >Properties</a
                        >
                    </li>
                }
            </ul>
        </aurelius-atlas-ui-details-navigation>
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DetailsSideNav {
    /** The layout's navigation entries, in legacy order (DET-25). */
    readonly entries = input.required<readonly NavDef[]>();

    /** Whether a layout was named (DET-02: with none, the default's one entry). */
    readonly hasLayout = input.required<boolean>();

    /** The dropdown's menu label, as the shell names it (UIC-18). */
    readonly label = $localize`:@@search.details.components.navigation.details:Details`;
}
