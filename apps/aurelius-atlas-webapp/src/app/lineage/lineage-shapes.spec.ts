import { describe, expect, it } from "vitest";

import { LINEAGE_BADGE_ICONS, lineageBadgeClass } from "./lineage-shapes";

/**
 * DD-405 (amended, DD-419): the card-badge seam the details page keeps after
 * the drawing moved to `aurelius-atlas-ui`. The badge family lives here, in
 * the app — the canvas knows shapes, the card knows badge colours.
 */
describe("lineage-shapes (DD-405, DD-419)", () => {
    it("DD-405: only the lineage glyphs get a card badge", () => {
        expect(lineageBadgeClass("dataset")).toBe("technical");
        expect(lineageBadgeClass("process")).toBe("technical-process");
        // No archimate type has a badge (the legacy's iconsByType, DD-378),
        // and a glyph-less type answers none either.
        expect(lineageBadgeClass("motivation")).toBeUndefined();
        expect(lineageBadgeClass(null)).toBeUndefined();
    });

    it("DD-405: the badge icons are the canvas's own glyph paths", () => {
        // The badge inks the same two paths the diagram nodes carry — one
        // source of truth, shaped for FontAwesome here.
        expect(LINEAGE_BADGE_ICONS.dataset.icon[4]).toContain("M 14.492 1");
        expect(LINEAGE_BADGE_ICONS.process.icon[4]).toContain("M 15.4545 10.0102");
        expect(LINEAGE_BADGE_ICONS.dataset.icon[0]).toBe(16);
    });
});
