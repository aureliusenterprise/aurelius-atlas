import { Injectable, Signal } from "@angular/core";

import { PAGE_SIZE_KEY, persisted, Persisted } from "./user-preference";

/** The page size the app ships with — the 7.2 table's legacy default. */
export const DEFAULT_PAGE_SIZE = 10;

/** The sizes the panel offers. */
export const PAGE_SIZES = [5, 10, 20, 50] as const;

/**
 * The page-size owner (SPL-08, DD-160): the default pagination size the
 * 7.6/7.7 tables read. Positive integers only — a corrupt store falls back
 * to the default.
 */
@Injectable({ providedIn: "root" })
export class PageSizeService {
    private readonly pref: Persisted<number> = persisted<number>(
        PAGE_SIZE_KEY,
        DEFAULT_PAGE_SIZE,
        (value): value is number => typeof value === "number" && Number.isInteger(value) && value > 0,
    );

    /** The default page size. */
    readonly pageSize: Signal<number> = this.pref.value;

    /**
     * Store the default page size.
     * @param pageSize a positive integer
     */
    set(pageSize: number): void {
        this.pref.set(pageSize);
    }
}
