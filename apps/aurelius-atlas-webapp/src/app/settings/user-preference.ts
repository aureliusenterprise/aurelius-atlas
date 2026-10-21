import { signal, Signal, WritableSignal } from "@angular/core";

/**
 * The persistence seam (DD-072): the only code in the app that reads or
 * writes `localStorage` for settings. An owner service creates its
 * preference here; a server-backed store replaces this module's internals
 * (GET/PUT behind the same signal API) without touching owners, facade, or
 * panel. The keys are browser-scoped (DD-073) — see each owner for what it
 * stores.
 */

/** The theme's key — `DarkModeService`'s existing one, kept (SPL-04). */
export const THEME_KEY = "data-theme";

/** The time zone id SPL-07 stores. */
export const TIMEZONE_KEY = "aurelius-atlas.settings.timezone";

/** The default table page size SPL-08 stores. */
export const PAGE_SIZE_KEY = "aurelius-atlas.settings.pageSize";

/** The telemetry switch SPL-11 stores. */
export const TELEMETRY_KEY = "aurelius-atlas.settings.telemetry";

/**
 * Read a stored preference. The bootstrap gate (telemetry, `DATE_PIPE_DEFAULT_TIMEZONE`)
 * reads through this before any service exists — `localStorage` is
 * synchronous, so a provider can branch on a setting (SPL-07, SPL-11).
 * @param key the storage key
 * @param initial the value when nothing is stored, stored is unparseable,
 *   or the browser denies storage access (private mode)
 * @param validate narrows the parsed value; return `false` to fall back to
 *   `initial`
 * @returns the stored value, narrowed and validated
 */
export function readPreference<T>(key: string, initial: T, validate?: (value: unknown) => boolean): T {
    let raw: string | null;
    try {
        raw = localStorage.getItem(key);
    } catch {
        return initial;
    }
    if (raw === null) {
        return initial;
    }
    let value: unknown;
    try {
        value = JSON.parse(raw) as unknown;
    } catch {
        return initial;
    }
    return validate && !validate(value) ? initial : (value as T);
}

/**
 * Persist a value. A write the browser denies (private mode) is swallowed —
 * the setting keeps working for the session.
 * @param key the storage key
 * @param value the value to store
 */
export function writePreference(key: string, value: unknown): void {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch {
        // Private mode: the session keeps its value, nothing persists.
    }
}

/** A signal with a setter: reads its storage key, writes through on set. */
export interface Persisted<T> {
    /** The current value, as a signal. */
    readonly value: Signal<T>;
    /** Set the value and persist it. */
    set(value: T): void;
}

/**
 * A preference signal (SPL-09): the stored value at construction — read
 * synchronously, so bootstrap can act on it — written back on every set.
 * @param key the storage key
 * @param initial the value when nothing is stored
 * @param validate narrows the stored value; `false` falls back to `initial`
 * @returns a signal-like with a persisting setter
 */
export function persisted<T>(key: string, initial: T, validate?: (value: unknown) => boolean): Persisted<T> {
    const state: WritableSignal<T> = signal(readPreference(key, initial, validate));

    return {
        value: state.asReadonly(),
        set(value: T): void {
            state.set(value);
            writePreference(key, value);
        },
    };
}
