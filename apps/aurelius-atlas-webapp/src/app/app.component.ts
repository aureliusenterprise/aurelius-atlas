import { ChangeDetectionStrategy, Component, computed, inject } from "@angular/core";
import { RouterOutlet } from "@angular/router";

import { AlertsService } from "./alerts/alerts.service";
import { ShellFooter } from "./shell/footer.component";
import { ShellHeader } from "./shell/header.component";
import { NavLoadingBar } from "./shell/nav-loading-bar.component";

/**
 * The application root: the shell chrome around the router outlet (SHC-01).
 *
 * The Aurelius root renders `<models4insight-shell>`, which wraps its
 * `router-outlet` in the header, the loading/pipeline sticky block, and the
 * footer; the loading half of that block returns with 7.4a (SRH-09, the
 * DD-145 deferral it closes), the pipeline half stays deferred with the
 * validation slice. The frame here is the header, the sticky loading bar,
 * the outlet, and the footer — SHL-03's "bare outlet" reading of the
 * Aurelius root component lands as this chrome.
 */
@Component({
    imports: [RouterOutlet, NavLoadingBar, ShellFooter, ShellHeader],
    selector: "aurelius-atlas-webapp-root",
    templateUrl: "./app.component.html",
    styleUrl: "./app.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
    protected readonly alerts = inject(AlertsService);

    /**
     * The alert announcer's text (LR-003, WCAG 4.1.3): every alert enters
     * the store — the HTTP interceptor, the error handler, a failed search
     * — and while the drawer is closed the bell dot (aria-hidden) was the
     * only change, so a screen-reader user never heard an error. The
     * persistent status in the template reads this; it follows the
     * arrivals counter, so a burst (ALR-03 merges) announces once, and
     * only a new arrival re-announces. Polite, never assertive.
     */
    protected readonly alertAnnouncement = computed(() => {
        this.alerts.newGroups();
        const newest = this.alerts.alerts()[0];
        if (!newest) {
            return "";
        }
        return $localize`:@@shell.alerts.announcement:New ${newest.severity}:severity: alert - ${newest.message}:message:`;
    });
}
