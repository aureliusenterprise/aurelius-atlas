/**
 * The search mode's owner (SBX-01, SBX-02, DD-473): a stored setting the
 * settings panel writes and the search results read. A corrupt store falls
 * back to Words; `changed` fires once per new mode, so an open results
 * screen searches again only when the mode really changed.
 */
import { TestBed } from "@angular/core/testing";

import { SEARCH_MODES, SearchMode, SearchModeService } from "./search-mode.service";
import { SEARCH_MODE_KEY } from "./user-preference";

describe("SearchModeService (SBX-01, SBX-02)", () => {
    beforeEach(() => localStorage.clear());
    afterEach(() => localStorage.clear());

    const service = () => TestBed.inject(SearchModeService);

    it("defaults to Words and offers Words, Meaning and Both (SBX-01)", () => {
        expect(SEARCH_MODES).toEqual(["words", "semantic", "hybrid"]);
        expect(service().mode()).toBe("words");
    });

    it("stores the chosen mode under the browser-scoped key (SBX-01)", () => {
        const svc = service();

        svc.set("semantic");

        expect(svc.mode()).toBe("semantic");
        expect(localStorage.getItem(SEARCH_MODE_KEY)).toBe(JSON.stringify("semantic"));
    });

    it("reads the stored mode at construction, and falls back to Words for a corrupt store (SBX-01)", () => {
        localStorage.setItem(SEARCH_MODE_KEY, JSON.stringify("hybrid"));
        expect(service().mode()).toBe("hybrid");

        for (const stored of ["meaning", 3, null, true]) {
            localStorage.setItem(SEARCH_MODE_KEY, JSON.stringify(stored));
            TestBed.resetTestingModule();

            expect(service().mode()).toBe("words");
        }
    });

    it("announces each new mode once, and an unchanged one not at all (SBX-02)", () => {
        const svc = service();
        const seen: SearchMode[] = [];
        svc.changed.subscribe((mode) => seen.push(mode));

        svc.set("hybrid");
        svc.set("hybrid");
        svc.set("words");

        expect(seen).toEqual(["hybrid", "words"]);
    });
});
