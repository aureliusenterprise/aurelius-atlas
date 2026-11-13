import { inject, Injectable } from "@angular/core";
import { Title } from "@angular/platform-browser";
import { TitleStrategy, RouterStateSnapshot, ActivatedRouteSnapshot } from "@angular/router";

import { APP_CONFIG } from "./tokens";

/**
 * The document title strategy (TITLE-001, WCAG 2.4.2): the page title
 * follows the route instead of staying the static index.html string, so
 * each screen answers "where am I" in the tab and screen-reader context.
 *
 * The title is the deepest primary route that carries `data.title`
 * (declared in `routes.ts` / `search.routes.ts`) joined to the app name
 * from the runtime config. Aux (drawer) routes carry no title and are not
 * the primary route, so opening the settings panel or the editor keeps
 * the page underneath its own title. A route without a title — the
 * guarded root before its redirect settles — falls back to the bare app
 * name, the string index.html ships.
 *
 * A screen whose name comes from data (the details entity, DET-09) sets
 * the title itself through Angular's Title service once the data lands;
 * the strategy owns the navigation moment, the component the data moment.
 */
@Injectable({ providedIn: "root" })
export class AtlasTitleStrategy extends TitleStrategy {
    private readonly title = inject(Title);

    private readonly config = inject(APP_CONFIG);

    /**
     * Apply the route's title to the document (TITLE-001). The deepest
     * primary route with a title wins; without one, the bare app name.
     * @param state the router state snapshot
     */
    override updateTitle(state: RouterStateSnapshot): void {
        const named = deepestTitle(state.root);
        // The details screen re-titles with the entity name once its data
        // lands (details.component.ts); the strategy owns the navigation
        // moment, the component the data moment.
        this.title.setTitle(named ? `${named} - ${this.config.appName}` : this.config.appName);
    }
}

/**
 * The deepest primary child's route title, or undefined when the primary
 * chain carries none. Only the primary outlet names the page (TITLE-001:
 * a drawer left open must not rename the tab).
 * @param route the snapshot route to walk
 * @returns the deepest `data.title` on the primary chain
 */
function deepestTitle(route: ActivatedRouteSnapshot): string | undefined {
    const child = route.firstChild;
    if (child?.outlet === "primary") {
        return deepestTitle(child) ?? (route.data["title"] as string | undefined);
    }
    return route.data["title"] as string | undefined;
}
