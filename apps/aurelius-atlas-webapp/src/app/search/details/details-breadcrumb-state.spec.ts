import type { Breadcrumb } from "aurelius-atlas-ui";

import { DetailsBreadcrumbState } from "./details-breadcrumb-state";

/**
 * The breadcrumb trail store (DET-12, DD-317): the app-side seam the API
 * join fills later — it reads empty, round-trips a set, and clears.
 */
describe("DetailsBreadcrumbState (DET-12, DD-317)", () => {
    const crumb = (guid: string): Breadcrumb => ({ guid, name: `name-${guid}`, typeName: "DataSet" });

    it("reads empty until something fills it (DET-12)", () => {
        const store = new DetailsBreadcrumbState();

        expect(store.trail()).toEqual([]);
    });

    it("round-trips a set trail, oldest first (DET-12)", () => {
        const store = new DetailsBreadcrumbState();

        store.setTrail([crumb("g1"), crumb("g2")]);

        expect(store.trail().map((item) => item.guid)).toEqual(["g1", "g2"]);
    });

    it("empties on clear (DET-12)", () => {
        const store = new DetailsBreadcrumbState();
        store.setTrail([crumb("g1")]);

        store.clear();

        expect(store.trail()).toEqual([]);
    });
});
