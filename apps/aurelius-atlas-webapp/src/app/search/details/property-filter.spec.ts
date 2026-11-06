import type { AtlasEntity } from "aurelius-atlas-data-access";

import { detailProperties, LEGACY_PROPERTY_BLACKLIST } from "./property-filter";

/** An entity carrying only what a test needs (DET-11). */
function entityOf(attributes: Record<string, unknown>, relationshipAttributes?: Record<string, unknown>): AtlasEntity {
    return { attributes, ...(relationshipAttributes ? { relationshipAttributes } : {}) };
}

describe("detailProperties (DET-11)", () => {
    it("drops the blacklisted keys, ported from the legacy set (DET-11)", () => {
        const rows = detailProperties(
            entityOf({
                name: "orders",
                qualifiedName: "s1.t.orders",
                definition: "the orders table",
                tableName: "orders",
            }),
        );

        expect(rows).toEqual([{ key: "tableName", value: "orders" }]);
        expect(LEGACY_PROPERTY_BLACKLIST.has("name")).toBe(true);
        expect(LEGACY_PROPERTY_BLACKLIST.has("qualifiedName")).toBe(true);
        expect(LEGACY_PROPERTY_BLACKLIST.has("definition")).toBe(true);
    });

    it("drops the key the description box shows (DET-11, DD-320)", () => {
        const entity = entityOf({ description: "shown text", tableName: "orders" });

        // The box shows `description` (no `definition`), so the table drops
        // it; the same drop covers `definition` when the box shows that.
        expect(detailProperties(entity, "description")).toEqual([{ key: "tableName", value: "orders" }]);
        expect(detailProperties(entity, "definition")).toEqual([
            { key: "description", value: "shown text" },
            { key: "tableName", value: "orders" },
        ]);
        // No box key (no entity read yet): the row rides as any other.
        expect(detailProperties(entity)).toEqual([
            { key: "description", value: "shown text" },
            { key: "tableName", value: "orders" },
        ]);
    });

    it("merges the attributes with the relationship attributes, the latter winning a clash (DET-11)", () => {
        const rows = detailProperties(
            entityOf({ owner: "alice", createTime: "own" }, { owner: "bob", dataOwner: "carol" }),
        );

        expect(rows).toEqual([
            { key: "createTime", value: "own" },
            { key: "dataOwner", value: "carol" },
            { key: "owner", value: "bob" },
        ]);
    });

    it("drops nil values and keeps false and the empty string (DET-11)", () => {
        const rows = detailProperties(entityOf({ nothing: null, missing: undefined, off: false, blank: "", zero: 0 }));

        expect(rows).toEqual([
            { key: "blank", value: "" },
            { key: "off", value: false },
            { key: "zero", value: 0 },
        ]);
    });

    it("keeps scalars and drops shapes the renderer cannot show (DET-11)", () => {
        const rows = detailProperties(
            entityOf({ text: "a", count: 3, flag: true, nested: { a: 1 }, mixed: [1, 2], empty: [] }),
        );

        expect(rows).toEqual([
            { key: "count", value: 3 },
            { key: "flag", value: true },
            { key: "text", value: "a" },
        ]);
    });

    it("maps a guid-bearing array to the link shape with the displayText/name/guid fallbacks (DET-11)", () => {
        const rows = detailProperties(
            entityOf(
                {},
                {
                    processes: [
                        { guid: "g1", displayText: "etl.one" },
                        { guid: "g2", name: "etl.two" },
                        { guid: "g3" },
                    ],
                },
            ),
        );

        expect(rows).toEqual([
            {
                key: "processes",
                value: [
                    { guid: "g1", displayText: "etl.one" },
                    { guid: "g2", displayText: "etl.two" },
                    { guid: "g3", displayText: "g3" },
                ],
            },
        ]);
    });

    it("treats an array without a string guid on every entry as unrenderable (DET-11)", () => {
        const rows = detailProperties(entityOf({ tags: [{ displayText: "no guid" }], plain: [{ guid: 42 }] }));

        expect(rows).toEqual([]);
    });

    it("sorts the rows by key (DET-11)", () => {
        const rows = detailProperties(entityOf({ zeta: "z", Alpha: "a", mid: "m" }));

        expect(rows.map((row) => row.key)).toEqual(["Alpha", "mid", "zeta"]);
    });

    it("answers no rows for an entity with no attributes (DET-11)", () => {
        expect(detailProperties({})).toEqual([]);
    });
});
