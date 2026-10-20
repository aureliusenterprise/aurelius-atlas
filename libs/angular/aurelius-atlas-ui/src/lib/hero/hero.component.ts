import { ChangeDetectionStrategy, Component, input } from "@angular/core";

/**
 * The Aurelius page hero: a primary-coloured band with a title, optional
 * subtitle, and action slots, plus a boxed tab strip in the foot — the
 * chrome every search/browse screen sits under.
 *
 * Ported as a section and slots only (DD-045): the Aurelius hero embedded a
 * `router-outlet` with an animated scroll-to-nav on navigation and needed
 * `ngx-page-scroll-core`; a dumb component has no route to activate, so the
 * routing host and the scroll move to the app shell with its routes (7.4+).
 *
 * Title, subtitle, and slot content are caller-supplied (DD-047) — the
 * Aurelius app passed the product name and translated its tab labels.
 */
@Component({
    selector: "aurelius-atlas-ui-hero",
    imports: [],
    templateUrl: "./hero.component.html",
    styleUrl: "./hero.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Hero {
    /**
     * The hero's title (the Aurelius app passed the product name). The
     * caller localises it.
     */
    readonly title = input<string>();

    /**
     * The hero's subtitle, shown under the title. The caller localises it.
     */
    readonly subtitle = input<string>();

    /**
     * Stretch the hero to the viewport, the Aurelius fullheight behaviour
     * when a page's routed content was empty.
     */
    readonly fullHeight = input(false);
}
