import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCopyright } from "@fortawesome/free-regular-svg-icons";

import { APP_CONFIG } from "../tokens";
import { VersionService } from "./version.service";

/**
 * The application footer, ported from the Aurelius `FooterComponent` (SHC-06).
 *
 * The legacy reads its three values from `ShellConfigService` and
 * `VersionService` (DD-145). Two of them no longer come from the runtime config
 * (7.34): the copyright year is the browser's current year (VER-04, DD-726) and
 * the version is the server's answer through {@link VersionService} (VER-01,
 * VER-03, DD-725). The app name stays in `/config.json` (SHL-10).
 *
 * i18n ids are the legacy dictionary paths, read by the XLIFF bridge (DD-128,
 * extended to @@shell.* by SHC-07). Translation descriptions are comments,
 * never `id|description` suffixes — the suffix joins the extracted id and the
 * key-keyed bridge can never match it (DD-144).
 */
@Component({
    imports: [FontAwesomeModule],
    selector: "aurelius-atlas-webapp-footer",
    templateUrl: "./footer.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellFooter {
    protected readonly appName = inject(APP_CONFIG).appName;

    /** The year of this page load (VER-04): OnPush and one instance per load. */
    protected readonly copyright = new Date().getFullYear();

    /** Empty until the server answers; the slot prints nothing (VER-03). */
    protected readonly version = inject(VersionService).version;

    protected readonly faCopyright = faCopyright;
}
