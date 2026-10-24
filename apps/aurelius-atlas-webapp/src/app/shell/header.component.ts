import { ChangeDetectionStrategy, Component, ElementRef, effect, inject, viewChild } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faBell, faBook, faGear } from "@fortawesome/free-solid-svg-icons";
import { RouterLink, RouterLinkActive } from "@angular/router";
import { Badge, Header } from "aurelius-atlas-ui";
import Keycloak from "keycloak-js";

import { AlertsService } from "../alerts/alerts.service";
import { APP_CONFIG } from "../tokens";
import { Session } from "./session.service";

/** The Aurelius Atlas documentation site, the legacy header's Documentation link. */
const DOCUMENTATION_URL = "https://aureliusenterprise.github.io/aurelius-atlas-documentation/";

/**
 * The bell's ring (ALR-02a): a pendulum swing from the handle, decaying
 * over five half-swings. Keyframes, not an angle — Web Animations
 * interpolates the transform lists.
 */
const BELL_SWING: Keyframe[] = [
    { transform: "rotate(0deg)" },
    { transform: "rotate(14deg)" },
    { transform: "rotate(-12deg)" },
    { transform: "rotate(9deg)" },
    { transform: "rotate(-5deg)" },
    { transform: "rotate(0deg)" },
];

/**
 * The Aurelius Atlas navbar chrome (SHC-02, SHC-03, SHC-05, SPL-01): the 7.2
 * ui-lib header with the app name brand, and on the right the Documentation
 * link, the settings gear, and the account dropdown.
 *
 * The navbar is search-free by design (DD-145): the global search bar and
 * nav buttons join 7.4. The login button the legacy navbar shows when signed
 * out is not ported — the root guard (APC-05) makes that state unreachable
 * (SHC-05). The language dropdown (SHC-04) moved into the settings panel
 * (SPL-01, SPL-06): switching language stays a full-page navigation into the
 * locale tree, since the locale builds are separate bundles (DD-128).
 *
 * The gear opens the settings panel by navigating the `drawer` aux outlet
 * (SPL-01, SPL-14, DD-166) — the open state lives in the URL, so a locale
 * switch's full-page reload keeps the panel open on the same page.
 */
@Component({
    imports: [Badge, FontAwesomeModule, Header, RouterLink, RouterLinkActive],
    selector: "aurelius-atlas-webapp-header",
    templateUrl: "./header.component.html",
    styleUrl: "./header.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellHeader {
    private readonly config = inject(APP_CONFIG);

    protected readonly appName = this.config.appName;

    /** The Aurelius Atlas brand mark (SHM-02): the legacy navbar logo, served from public/. */
    protected readonly appLogo = "assets/aurelius-atlas-logo.png";

    protected readonly session = inject(Session);

    /** The alerts store, behind the bell's badge and ring (ALR-02, ALR-02a). */
    protected readonly alerts = inject(AlertsService);

    protected readonly faBook = faBook;

    protected readonly faGear = faGear;

    protected readonly faBell = faBell;

    protected readonly documentationUrl = DOCUMENTATION_URL;

    /** The bell's icon element, the ring animation's target (ALR-02a). */
    private readonly bellIcon = viewChild<ElementRef<HTMLElement>>("bellIcon");

    constructor() {
        // A new alert group rings the bell once (ALR-02a). The effect
        // watches the arrival counter — merges (ALR-03) do not move it,
        // so a burst rings once. The first pass records the starting
        // count without ringing; reduced motion skips the animation
        // (the store is unchanged). Web Animations, not a CSS class:
        // `animate` restarts cleanly mid-swing, where a class toggle
        // needs a reflow hack to re-trigger. The optional call is for
        // jsdom, which ships no WAAPI.
        let seen = this.alerts.newGroups();
        effect(() => {
            const arrivals = this.alerts.newGroups();
            if (arrivals === seen) {
                return;
            }
            seen = arrivals;
            if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
                return;
            }
            this.bellIcon()?.nativeElement.animate?.(BELL_SWING, { duration: 650, easing: "ease-in-out" });
        });
    }

    private readonly keycloak = inject(Keycloak);

    /**
     * Keycloak's account console for the configured realm — the legacy
     * `accountManagement()` (keycloak-js dropped its `accountManager`, so the
     * port composes the URL from the runtime config, SHC-05).
     */
    protected get accountUrl(): string {
        const { url, realm } = this.config.keycloak;

        return new URL(`realms/${realm}/account`, url).href;
    }

    /** End the Keycloak session (SHC-05), returning to the sign-in page. */
    protected logout(): void {
        // The navigation starts immediately; the promise resolves on the
        // sign-in page, where this context is gone — nothing left to await.
        void this.keycloak.logout();
    }
}
