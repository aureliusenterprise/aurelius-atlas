import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faBook, faGear } from "@fortawesome/free-solid-svg-icons";
import { Header } from "aurelius-atlas-ui";
import Keycloak from "keycloak-js";

import { SettingsPanel } from "../settings/settings-panel.component";
import { APP_CONFIG } from "../tokens";
import { Session } from "./session.service";

/** The Aurelius Atlas documentation site, the legacy header's Documentation link. */
const DOCUMENTATION_URL = "https://aureliusenterprise.github.io/aurelius-atlas-documentation/";

/**
 * The Aurelius shell header (SHC-02, SHC-03, SHC-05, SPL-01): the 7.2
 * ui-lib header with the app name brand, and on the right the Documentation
 * link, the settings gear, and the account dropdown.
 *
 * The navbar is search-free by design (DD-056): the global search bar and
 * nav buttons join 7.4. The login button the legacy navbar shows when signed
 * out is not ported — the root guard (APC-05) makes that state unreachable
 * (SHC-05). The language dropdown (SHC-04) moved into the settings panel
 * (SPL-01, SPL-06): switching language stays a full-page navigation into the
 * locale tree, since the locale builds are separate bundles (DD-039).
 */
@Component({
    imports: [FontAwesomeModule, Header, SettingsPanel],
    selector: "aurelius-atlas-webapp-header",
    templateUrl: "./header.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellHeader {
    private readonly config = inject(APP_CONFIG);

    protected readonly appName = this.config.appName;

    /** The Aurelius Atlas brand mark (SHM-02): the legacy navbar logo, served from public/. */
    protected readonly appLogo = "assets/aurelius-atlas-logo.png";

    protected readonly session = inject(Session);

    protected readonly faBook = faBook;

    protected readonly faGear = faGear;

    protected readonly documentationUrl = DOCUMENTATION_URL;

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
