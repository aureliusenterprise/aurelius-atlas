import type { EntityView } from "aurelius-atlas-data-access";

import { LEGACY_PROPERTY_BLACKLIST, viewProperties } from "./property-filter";

/** A view carrying only what a test needs: attributes, and sections as the read door answers them (DET-11, VDR-04). */
function viewOf(
    attributes: Record<string, unknown>,
    sections?: { attribute: string; entities: { guid: string; name?: string | null }[] }[],
): EntityView {
    return {
        guid: "g",
        typeName: "asset",
        displayText: "G",
        status: "ACTIVE",
        stale: false,
        attributes,
        ...(sections ? { sections } : {}),
    };
}

/** One relationship section of ends, each a guid and maybe a name (the door's VDR-02 answer). */
function ends(
    attribute: string,
    ...named: [string, string?][]
): { attribute: string; entities: { guid: string; name?: string | null }[] } {
    return { attribute, entities: named.map(([guid, name]) => ({ guid, ...(name === undefined ? {} : { name }) })) };
}

describe("viewProperties (DET-11, VDR-04)", () => {
    it("drops the blacklisted keys, ported from the legacy set (DET-11)", () => {
        const rows = viewProperties(
            viewOf({
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
        const view = viewOf({ description: "shown text", tableName: "orders" });

        // The box shows `description` (no `definition`), so the table drops
        // it; the same drop covers `definition` when the box shows that.
        expect(viewProperties(view, "description")).toEqual([{ key: "tableName", value: "orders" }]);
        expect(viewProperties(view, "definition")).toEqual([
            { key: "description", value: "shown text" },
            { key: "tableName", value: "orders" },
        ]);
        // No box key (no entity read yet): the row rides as any other.
        expect(viewProperties(view)).toEqual([
            { key: "description", value: "shown text" },
            { key: "tableName", value: "orders" },
        ]);
    });

    it("merges the attributes with the sections, the latter winning a clash (DET-11, VDR-04)", () => {
        const rows = viewProperties(
            viewOf({ owner: "alice", createTime: "own" }, [
                ends("dataOwner", ["g1", "carol"]),
                ends("owner", ["g2", "bob"]),
            ]),
        );

        // A section answers a link array (VDR-04), and wins the key clash as
        // the legacy's relationship spread did.
        expect(rows).toEqual([
            { key: "createTime", value: "own" },
            { key: "dataOwner", value: [{ guid: "g1", displayText: "carol" }] },
            { key: "owner", value: [{ guid: "g2", displayText: "bob" }] },
        ]);
    });

    it("drops nil values and keeps false and the empty string (DET-11)", () => {
        const rows = viewProperties(viewOf({ nothing: null, missing: undefined, off: false, blank: "", zero: 0 }));

        expect(rows).toEqual([
            { key: "blank", value: "" },
            { key: "off", value: false },
            { key: "zero", value: 0 },
        ]);
    });

    it("keeps scalars and drops shapes the renderer cannot show (DET-11)", () => {
        const rows = viewProperties(
            viewOf({ text: "a", count: 3, flag: true, nested: { a: 1 }, mixed: [1, 2], empty: [] }),
        );

        expect(rows).toEqual([
            { key: "count", value: 3 },
            { key: "flag", value: true },
            { key: "text", value: "a" },
        ]);
    });

    it("maps a section's ends to the link shape, the name first and the guid last (DET-11, VDR-04)", () => {
        const rows = viewProperties(viewOf({}, [ends("processes", ["g1", "etl.one"], ["g2", "etl.two"], ["g3"])]));

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

    it("answers no row for a stored empty array or a section with no ends (VDR-04)", () => {
        const rows = viewProperties(viewOf({ processes: [] }, [ends("systems")]));

        expect(rows).toEqual([]); // neither shape is a link array (DET-02's no-fake-data rule)
    });

    it("treats an attribute array without a string guid on every entry as unrenderable (DET-11)", () => {
        const rows = viewProperties(viewOf({ tags: [{ displayText: "no guid" }], plain: [{ guid: 42 }] }));

        expect(rows).toEqual([]);
    });

    it("sorts the rows by key (DET-11)", () => {
        const rows = viewProperties(viewOf({ zeta: "z", Alpha: "a", mid: "m" }));

        expect(rows.map((row) => row.key)).toEqual(["Alpha", "mid", "zeta"]);
    });

    it("answers no rows for a view with no attributes (DET-11)", () => {
        expect(viewProperties(viewOf({}))).toEqual([]);
    });
});
