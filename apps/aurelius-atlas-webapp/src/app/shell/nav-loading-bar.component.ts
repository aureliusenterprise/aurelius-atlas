import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { NavigationCancel, NavigationEnd, NavigationError, NavigationStart, Router } from "@angular/router";
import { map } from "rxjs";

/**
 * The sticky navigation loading bar (SRH-09, DD-145): the legacy
 * `sticky-loading-bar` — a Bulma `progress.is-link` fixed under the pinned
 * navbar, visible while the router is navigating.
 *
 * Router navigation only, not HTTP (the legacy `isNavigating`, fed by
 * router events, not by an HTTP interceptor): the bar tracks the address
 * changes between search screens, the legacy's `top: 4.25rem` sitting it
 * at the pinned navbar's foot.
 */
@Component({
    selector: "aurelius-atlas-webapp-nav-loading-bar",
    templateUrl: "./nav-loading-bar.component.html",
    styleUrl: "./nav-loading-bar.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NavLoadingBar {
    /**
     * The legacy `isNavigating`: on from `NavigationStart`, off from
     * `NavigationEnd`, `NavigationError`, or `NavigationCancel` (a
     * guard's redirect ends navigation the same way).
     */
    protected readonly isNavigating = toSignal(
        inject(Router).events.pipe(
            map((event) =>
                event instanceof NavigationStart
                    ? true
                    : event instanceof NavigationEnd ||
                        event instanceof NavigationError ||
                        event instanceof NavigationCancel
                      ? false
                      : undefined,
            ),
        ),
        { initialValue: false },
    );
}
