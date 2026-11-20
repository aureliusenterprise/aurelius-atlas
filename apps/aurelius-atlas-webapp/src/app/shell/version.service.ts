import { inject, Injectable, signal } from "@angular/core";
import { AdminService } from "aurelius-atlas-data-access";

/**
 * The app version, read from the server once per page load (VER-01, DD-725).
 *
 * The value used to sit in `/config.json` next to the Keycloak and exporter
 * endpoints. It does not belong there: the release stamps one number into the
 * server package, the image tags and every chart's `appVersion` (DD-288,
 * DD-165), so the server's own answer of `GET /api/atlas/admin/version`
 * (ADM-01, DV-03) is the app version — a second copy in a file is a copy that
 * can only go stale.
 *
 * The read starts the first time anything injects the service, which is the
 * shell's first render behind the guard (APC-05), and one instance is shared
 * from then on: no reader ever causes a second request (VER-02). Until the
 * answer lands, readers get the empty string: the footer and the About section
 * print nothing, and the lineage PNG writer drops its `Software` chunk under
 * LDG-31's empty-field skip (VER-03). A failed read stays empty and makes no
 * noise — the same degrade the About section already accepted for the time
 * zones it fetches (SPL-07).
 */
@Injectable({ providedIn: "root" })
export class VersionService {
    private readonly admin = inject(AdminService);

    /** The answer's `Version` key, empty until it arrives or when it never does (VER-02). */
    private readonly _version = signal("");

    /**
     * The app version to print, `""` before the answer arrives (VER-02).
     * @returns the release number the server reports
     */
    readonly version = this._version.asReadonly();

    constructor() {
        this.admin.getVersion().subscribe({
            next: (answer) => this._version.set(answer.Version),
            // Silence is the contract (VER-03): a reader prints nothing rather
            // than an error, and the call already had 7.26's one resend.
            error: () => this._version.set(""),
        });
    }
}
