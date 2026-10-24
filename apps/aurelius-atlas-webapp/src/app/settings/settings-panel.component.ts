import { ChangeDetectionStrategy, Component, inject, signal } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router } from "@angular/router";
import { AdminService } from "aurelius-atlas-data-access";
import { Drawer, Mode, Select } from "aurelius-atlas-ui";

import { APP_CONFIG } from "../tokens";
import { PAGE_SIZES } from "./page-size.service";
import { SettingsService } from "./settings.service";

/** A row of the Appearance select — the ui-lib Select's row shape (DD-164). */
type ThemeRow = { mode: Mode; label: string };

/**
 * The settings panel (SPL-01, SPL-03..SPL-14): the drawer the header gear
 * opens, carrying Appearance (theme), Language, Time zone, Table page
 * size, Telemetry, and an About section. Everything flows through the
 * {@link SettingsService} facade (SPL-10); the panel itself stores nothing.
 *
 * The panel is a routed component in the `drawer` aux outlet (SPL-14,
 * DD-166): the gear navigates to it, dismissal navigates away, and the
 * outlet segment rides the URL — so the language switch's full-page
 * navigation (SPL-06, DD-128) reloads the same locale page with the
 * panel open.
 */
@Component({
    imports: [Drawer, FormsModule, Select],
    selector: "aurelius-atlas-webapp-settings-panel",
    templateUrl: "./settings-panel.component.html",
    styleUrl: "./settings-panel.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPanel {
    protected readonly settings = inject(SettingsService);

    protected readonly config = inject(APP_CONFIG);

    private readonly admin = inject(AdminService);

    private readonly router = inject(Router);

    protected readonly pageSizes = PAGE_SIZES;

    /**
     * The drawer's open state, two-way bound to the ui-lib drawer. True
     * for the component's whole life: the routed panel exists only while
     * open (SPL-14), and dismissal flips it before navigating away.
     */
    readonly active = signal(true);

    /** The zone ids the server publishes (ADM-05); empty until it answers. */
    protected readonly timezones = signal<readonly string[]>([]);

    /** The drawer's accessible title (SPL-02). Strings bound live in TypeScript use `$localize` (BRW-02). */
    protected readonly title = $localize`:@@shell.settings.title:Settings`;

    /** Accessible name of the drawer's close control (the Modal's ariaLabel pattern). */
    protected readonly closeLabel = $localize`:@@shell.settings.close:Close`;

    /** The Appearance select's label (SPL-03, DD-164) — the section heading is the control's label. */
    protected readonly appearanceLabel = $localize`:@@shell.settings.appearance:Appearance`;

    /** The theme choices for the select: Auto first (SPL-03). Mutable
     *  because the ui-lib Select's `options` input is a plain array. */
    protected readonly themes: ThemeRow[] = [
        { mode: null, label: $localize`:@@shell.settings.theme.auto:Auto` },
        { mode: "light", label: $localize`:@@shell.settings.theme.light:Light` },
        { mode: "dark", label: $localize`:@@shell.settings.theme.dark:Dark` },
    ];

    constructor() {
        // The panel exists only while open, so the session/timezones load
        // at construction — the routed replacement of the lazy open() fetch
        // (SPL-14). Chrome data, not route data; failures stay quiet: the
        // section degrades to the browser default (SPL-07).
        this.admin.getSession().subscribe({
            next: (session) => this.timezones.set(session.timezones),
            error: () => this.timezones.set([]),
        });
    }

    /**
     * The Appearance select's row: the theme choice, Auto when unset
     * (SPL-03).
     * @returns the selected row
     */
    protected get themeRow(): ThemeRow {
        return this.themes.find((theme) => theme.mode === this.settings.theme()) ?? this.themes[0];
    }

    /**
     * Store the select's choice (SPL-03, DD-164) — the valueChange path.
     * @param row the chosen row; null (the placeholder) changes nothing
     */
    protected setTheme(row: ThemeRow | null): void {
        if (row) {
            this.settings.setTheme(row.mode);
        }
    }

    /**
     * The drawer's dismissal (SPL-14, DD-166): navigate the `drawer`
     * outlet away. The panel is destroyed with the route, so the exit
     * animation is not awaited — the accepted cost of the URL owning
     * the open state.
     */
    protected close(): void {
        this.active.set(false);
        this.router.navigate([{ outlets: { drawer: null } }]);
    }

    /**
     * The zone the picker shows: the stored choice, or `null` when
     * nothing is stored — which selects the "Browser default" option
     * (SPL-07, DD-167). Resolving the browser's own zone here instead
     * would leave the select blank whenever that zone is not among the
     * server's ids; the effective zone of a "Browser default" selection
     * is the browser's, applied at the date pipe (ADM-05).
     * @returns the zone id for the select, or null
     */
    protected get timezoneValue(): string | null {
        return this.settings.timezone();
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
