import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCopyright } from "@fortawesome/free-regular-svg-icons";

import { APP_CONFIG } from "../tokens";

/**
 * The application footer, ported from the Aurelius `FooterComponent` (SHC-06).
 *
 * The legacy reads its three values from `ShellConfigService` and
 * `VersionService`; both collapse into {@link APP_CONFIG} here (DD-145): the
 * copyright year, the application name, and the version string shipped in the
 * runtime config payload.
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

    protected readonly copyright = inject(APP_CONFIG).appCopyright;

    protected readonly version = inject(APP_CONFIG).appVersion;

    protected readonly faCopyright = faCopyright;
}
