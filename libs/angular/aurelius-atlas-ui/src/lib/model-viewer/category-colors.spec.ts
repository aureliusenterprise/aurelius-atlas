import { describe, expect, it } from "vitest";

import { CATEGORY_PALETTE, categoryColor, deriveCategoryLegend } from "./category-colors";

/**
 * The colour-view join (UIC-30/UIC-31, DD-420): the pure function behind the
 * canvas's fills and the drawer's legend table. The fixtures are the plain
 * records the caller (a heatmap producer, the picker) hands the canvas.
 */

describe("deriveCategoryLegend (UIC-30)", () => {
    it("UIC-30: no categories answer an empty legend", () => {
        expect(deriveCategoryLegend(null, null)).toEqual({});
        expect(deriveCategoryLegend({}, { anything: "#ff0000" })).toEqual({});
    });

    it("UIC-30: distinct categories take palette colours in first-seen order", () => {
        const legend = deriveCategoryLegend({ a: "gold", b: "silver", c: "gold", d: "bronze" }, null);
        expect(legend).toEqual({
            gold: CATEGORY_PALETTE[0],
            silver: CATEGORY_PALETTE[1],
            bronze: CATEGORY_PALETTE[2],
        });
    });

    it("UIC-31: an override wins over the palette, per category", () => {
        const legend = deriveCategoryLegend({ a: "gold", b: "silver" }, { silver: "#abcdef" });
        expect(legend).toEqual({ gold: CATEGORY_PALETTE[0], silver: "#abcdef" });
    });

    it("UIC-30: the empty category names nothing and takes no colour", () => {
        expect(deriveCategoryLegend({ a: "", b: "gold" }, null)).toEqual({ gold: CATEGORY_PALETTE[0] });
    });

    it("UIC-30: a thirteenth distinct category wraps to the first palette colour", () => {
        const categories: Record<string, string> = {};
        for (let index = 0; index <= CATEGORY_PALETTE.length; index += 1) {
            categories[`c${index}`] = `cat-${index}`;
        }
        const legend = deriveCategoryLegend(categories, null);
        expect(Object.keys(legend)).toHaveLength(CATEGORY_PALETTE.length + 1);
        expect(legend[`cat-${CATEGORY_PALETTE.length}`]).toBe(CATEGORY_PALETTE[0]);
    });
});

describe("categoryColor (UIC-30)", () => {
    const categories = { "v-1": "gold", "e-9": "silver" };
    const legend = deriveCategoryLegend(categories, null);

    it("UIC-30: the view id answers first, the concept second (the legacy's chain)", () => {
        expect(categoryColor(legend, categories, "v-1", "e-1")).toBe(CATEGORY_PALETTE[0]);
        expect(categoryColor(legend, categories, "v-unknown", "e-9")).toBe(CATEGORY_PALETTE[1]);
    });

    it("UIC-30: an untabled element or a null colour view paints nothing", () => {
        expect(categoryColor(legend, categories, "v-x", "e-x")).toBeNull();
        expect(categoryColor(legend, null, "v-1", "e-1")).toBeNull();
    });

    it("UIC-30: a category missing from the legend paints nothing", () => {
        expect(categoryColor({}, categories, "v-1", "e-1")).toBeNull();
    });
});
