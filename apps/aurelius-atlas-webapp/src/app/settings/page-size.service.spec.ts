/**
 * The page-size owner (SPL-08, SPL-10): the default pagination size the
 * 7.6 tables will read. The positive-integer guard is the rule — a
 * corrupt store (a string, zero, a fraction) falls back to the shipped
 * default, 10.
 */
import { TestBed } from "@angular/core/testing";

import { DEFAULT_PAGE_SIZE, PAGE_SIZES, PageSizeService } from "./page-size.service";
import { PAGE_SIZE_KEY } from "./user-preference";

describe("PageSizeService (SPL-08)", () => {
    beforeEach(() => localStorage.clear());
    afterEach(() => localStorage.clear());

    const service = () => TestBed.inject(PageSizeService);

    it("defaults to 10, the legacy table's page size (SPL-08)", () => {
        expect(DEFAULT_PAGE_SIZE).toBe(10);
        expect(service().pageSize()).toBe(10);
    });

    it("offers the panel's choices, 10 among them (SPL-08)", () => {
        expect(PAGE_SIZES).toEqual([5, 10, 20, 50]);
        expect(PAGE_SIZES).toContain(DEFAULT_PAGE_SIZE);
    });

    it("stores the chosen size under the browser-scoped key (SPL-08, SPL-09)", () => {
        const svc = service();

        svc.set(20);

        expect(svc.pageSize()).toBe(20);
        expect(localStorage.getItem(PAGE_SIZE_KEY)).toBe(JSON.stringify(20));
    });

    it("falls back to the default for a corrupt store (SPL-08)", () => {
        for (const stored of ["twelve", 0, -5, 2.5, "10", null, true]) {
            localStorage.setItem(PAGE_SIZE_KEY, JSON.stringify(stored));
            TestBed.resetTestingModule();

            expect(service().pageSize()).toBe(10);
        }
    });

    it("reads the stored size at construction", () => {
        localStorage.setItem(PAGE_SIZE_KEY, JSON.stringify(50));

        expect(service().pageSize()).toBe(50);
    });
});
