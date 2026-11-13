import { ChangeDetectionStrategy, Component, input } from "@angular/core";

/**
 * The Aurelius page hero: a primary-coloured band with a title, optional
 * subtitle, and action slots, plus a boxed tab strip in the foot — the
 * chrome every search/browse screen sits under.
 *
 * Ported as a section and slots only (DD-134): the Aurelius hero embedded a
 * `router-outlet` with an animated scroll-to-nav on navigation and needed
 * `ngx-page-scroll-core`; a dumb component has no route to activate, so the
 * routing host and the scroll move to the app shell with its routes (7.4+).
 *
 * Title, subtitle, and slot content are caller-supplied (DD-136) — the
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

    /**
     * The heading level of the title (HEADING-001): a host whose routed
     * child renders its own h1 (the details screen's entity title) passes
     * 2 so the page keeps one h1 — the chrome band steps down, the Bulma
     * classes keep the pixels. Default 1, the page-title screen.
     */
    readonly titleLevel = input<1 | 2>(1);

    /**
     * The foot tab strip's accessible name (the unnamed-nav minor): the
     * caller localises it, like the tab labels themselves (DD-136).
     */
    readonly navigationLabel = input<string>();
}
