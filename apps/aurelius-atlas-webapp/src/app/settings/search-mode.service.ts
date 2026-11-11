import { Injectable, Signal } from "@angular/core";
import { Observable, Subject } from "rxjs";

import { persisted, Persisted, SEARCH_MODE_KEY } from "./user-preference";

/**
 * How the search field searches (SBX-01, DD-473): by the query's words, a
 * quick search; by its meaning; or by both, the hybrid search by meaning.
 */
export type SearchMode = "words" | "semantic" | "hybrid";

/** The modes the settings panel offers, in its order: Words, the default, Meaning, Both. */
export const SEARCH_MODES: readonly SearchMode[] = ["words", "semantic", "hybrid"];

/**
 * The search mode's owner (SBX-01, DD-473): a stored setting, as the page
 * size is, that the settings panel writes and the search results read. A
 * corrupt store falls back to Words. `changed` tells a results screen that
 * is open to search again (SBX-02).
 */
@Injectable({ providedIn: "root" })
export class SearchModeService {
    private readonly pref: Persisted<SearchMode> = persisted<SearchMode>(
        SEARCH_MODE_KEY,
        "words",
        (value): value is SearchMode => SEARCH_MODES.includes(value as SearchMode),
    );

    private readonly changes = new Subject<SearchMode>();

    /** The stored search mode. */
    readonly mode: Signal<SearchMode> = this.pref.value;

    /** Each new mode, as it is stored. */
    readonly changed: Observable<SearchMode> = this.changes.asObservable();

    /**
     * Store the search mode; an unchanged one is no change.
     * @param mode words, meaning or both
     */
    set(mode: SearchMode): void {
        if (mode === this.mode()) {
            return;
        }
        this.pref.set(mode);
        this.changes.next(mode);
    }
}
