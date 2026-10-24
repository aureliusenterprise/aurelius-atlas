import { DOCUMENT, effect, inject, Injectable, signal } from "@angular/core";

/**
 * The modes available for the dark mode service.
 */
const MODES = ["dark", "light", null] as const;

/**
 * The type representing the modes available in the dark mode service.
 * Exported for the settings facade (SPL-03): the panel's theme radio
 * chooses one and hands it to {@link DarkModeService.setMode}.
 */
export type Mode = (typeof MODES)[number];

@Injectable({
    providedIn: "root",
})
export class DarkModeService {
    /**
     * The current mode of the application, which can be "light", "dark", or null.
     */
    readonly mode = signal<Mode>(null);

    /**
     * The document object is injected to manipulate the HTML document.
     */
    private readonly document = inject(DOCUMENT);

    /**
     * Initialize the DarkModeService and create an effect to update the theme whenever the mode changes.
     */
    constructor() {
        effect(() => {
            this.updateDataThemeAttribute(this.mode());
        });

        effect(() => {
            this.updateLocalStorage(this.mode());
        });

        this.mode.set(this.initialize());
    }

    /**
     * Toggles the current mode to the next one.
     */
    next(): void {
        this.mode.update((current) => {
            return MODES[(MODES.indexOf(current) + 1) % MODES.length];
        });
    }

    /**
     * Choose the mode explicitly (the settings panel's radio): `"light"`,
     * `"dark"`, or `null` for Auto — follow the operating system. The same
     * persistence path as {@link next}: the root attribute (SPL-03) and the
     * stored choice (SPL-04) both follow.
     * @param mode the mode to switch to
     */
    setMode(mode: Mode): void {
        this.mode.set(mode);
    }

    /**
     * @returns The initial mode based on the current HTML document's data-theme attribute.
     */
    private initialize(): Mode {
        const stored = localStorage.getItem("data-theme");
        const attribute = this.document.documentElement.getAttribute("data-theme");
        let dataTheme = (attribute || stored) as Mode;

        if (!MODES.includes(dataTheme)) {
            dataTheme = null;
        }

        return dataTheme;
    }

    /**
     * Updates the HTML document's data-theme attribute based on the current
     * mode. Auto removes the attribute: the empty string would keep Bulma's
     * `:root:not([data-theme])` OS path from applying (DD-159).
     * @param mode The current mode of the application.
     */
    private updateDataThemeAttribute(mode: Mode): void {
        const htmlElement = this.document.documentElement;
        if (mode === null) {
            htmlElement.removeAttribute("data-theme");
        } else {
            htmlElement.setAttribute("data-theme", mode);
        }
    }

    /**
     * Updates the local storage with the current mode.
     * If the mode is null, it removes the "data-theme" item from local storage.
     * @param mode The current mode of the application.
     */
    private updateLocalStorage(mode: Mode): void {
        if (mode === null) {
            localStorage.removeItem("data-theme");
        } else {
            localStorage.setItem("data-theme", mode);
        }
    }
}
