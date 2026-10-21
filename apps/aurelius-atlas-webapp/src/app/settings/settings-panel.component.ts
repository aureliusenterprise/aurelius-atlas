import { ChangeDetectionStrategy, Component, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { AdminService } from "aurelius-atlas-data-access";
import { Drawer, Mode } from "aurelius-atlas-ui";

import { APP_CONFIG } from "../tokens";
import { PAGE_SIZES } from "./page-size.service";
import { SettingsService } from "./settings.service";

/**
 * The settings panel (SPL-01, SPL-06..SPL-12): a ui-lib drawer opened from
 * the header gear, carrying Appearance (theme), Language, Time zone, Table
 * page size, Telemetry, and an About section. Everything flows through the
 * {@link SettingsService} facade (SPL-10); the panel itself stores nothing.
 *
 * Language is a full-page navigation, not a stored setting (SPL-06,
 * DD-039): the locale builds are separate bundles, so the section carries
 * links, and the panel closes with the navigation.
 */
@Component({
    imports: [Drawer, FormsModule],
    selector: "aurelius-atlas-webapp-settings-panel",
    templateUrl: "./settings-panel.component.html",
    styleUrl: "./settings-panel.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPanel {
    protected readonly settings = inject(SettingsService);

    protected readonly config = inject(APP_CONFIG);

    private readonly admin = inject(AdminService);

    protected readonly pageSizes = PAGE_SIZES;

    /** The drawer's open state, two-way bound to the ui-lib drawer. */
    readonly active = signal(false);

    /** The zone ids the server publishes (ADM-05); empty until it answers. */
    protected readonly timezones = signal<readonly string[]>([]);

    /** The server's name and version (ADM-01, SPL-12); null until it answers. */
    protected readonly serverVersion = signal<string | null>(null);

    /** The drawer's accessible title (SPL-02). Strings bound live in TypeScript use `$localize` (BRW-02). */
    protected readonly title = $localize`:@@shell.settings.title:Settings`;

    /** Accessible name of the drawer's close control (the Modal's ariaLabel pattern). */
    protected readonly closeLabel = $localize`:@@shell.settings.close:Close`;

    /** The About section's stand-in while the server version is unknown (SPL-12). */
    protected readonly serverUnavailable = $localize`:@@shell.settings.serverUnavailable:Server version unavailable`;

    /** The theme choices: the service's modes, Auto first (SPL-03). */
    protected readonly themes: readonly { mode: Mode; label: string }[] = [
        { mode: null, label: $localize`:@@shell.settings.theme.auto:Auto` },
        { mode: "light", label: $localize`:@@shell.settings.theme.light:Light` },
        { mode: "dark", label: $localize`:@@shell.settings.theme.dark:Dark` },
    ];

    /** Open the panel — the header gear's action (SPL-01). */
    open(): void {
        this.active.set(true);
        // The session/timezones and version load lazily, the first time the
        // panel opens — chrome data, not route data. Failures stay quiet:
        // the sections degrade to the browser default / no version line.
        if (this.timezones().length === 0) {
            this.admin.getSession().subscribe({
                next: (session) => this.timezones.set(session.timezones),
                error: () => this.timezones.set([]),
            });
        }
        if (this.serverVersion() === null) {
            this.admin.getVersion().subscribe({
                next: (version) => this.serverVersion.set(`${version.Name} ${version.Version}`),
                error: () => this.serverVersion.set(null),
            });
        }
    }

    /**
     * The zone the picker shows: the stored choice, falling back to the
     * browser's — the value a "Browser default" selection means.
     * @returns the zone id for the select
     */
    protected get timezoneValue(): string {
        return this.settings.timezone() ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
    }

    /**
     * Store the picker's choice (`null` = "Browser default") — the select's
     * change path (SPL-07).
     * @param timezone the chosen zone id, or null
     */
    protected setTimezone(timezone: string | null): void {
        this.settings.setTimezone(timezone);
    }
}
