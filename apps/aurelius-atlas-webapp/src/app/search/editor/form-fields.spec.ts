import type { AtlasAttributeDef, AtlasEntityDef, AtlasEnumDef } from "aurelius-atlas-data-access";

import { buildFields, mergeOntoEntity, toFormValues } from "./form-fields";

/** An attribute definition with defaults the shipped store's carry. */
function attr(overrides: Partial<AtlasAttributeDef> & { name: string }): AtlasAttributeDef {
    return {
        typeName: "string",
        isOptional: false,
        cardinality: "SINGLE",
        ...overrides,
    };
}

/** An entity definition carrying its own attributes and supertype links. */
function entityDef(name: string, attributeDefs: AtlasAttributeDef[], superTypes: string[] = []): AtlasEntityDef {
    return { name, attributeDefs, superTypes };
}

const DATASET = entityDef("DataSet", [], ["Asset"]);
const ASSET = entityDef(
    "Asset",
    [
        attr({ name: "name" }),
        attr({ name: "description", isOptional: true }),
        attr({ name: "owner", isOptional: true }),
    ],
    ["Referenceable"],
);
const REFERENCEABLE = entityDef("Referenceable", [
    attr({ name: "qualifiedName", isUnique: true }),
    attr({ name: "displayName", isOptional: true }),
]);

const SHIPPED = new Map<string, AtlasEntityDef>([
    ["DataSet", DATASET],
    ["Asset", ASSET],
    ["Referenceable", REFERENCEABLE],
]);

describe("buildFields (EDT-03)", () => {
    it("walks the supertype chain (DataSet carries only none of its own)", () => {
        const fields = buildFields(DATASET, SHIPPED, new Map());

        expect(fields.map((field) => field.name)).toEqual(["name", "description", "displayName", "owner"]);
        expect(fields.every((field) => field.name !== "qualifiedName")).toBe(true);
    });

    it("dedupes by name, the definition's own first (the walk is first-wins)", () => {
        const child = entityDef("Child", [attr({ name: "name", displayName: "Child name" })], ["Asset"]);
        const defs = new Map([...SHIPPED, ["Child", child]]);

        const fields = buildFields(child, defs, new Map());

        expect(fields.find((field) => field.name === "name")?.label).toBe("Child name");
    });

    it("maps the kinds by typeName and cardinality", () => {
        const defs = new Map<string, AtlasEntityDef>([
            [
                "Wide",
                entityDef("Wide", [
                    attr({ name: "textAttr" }),
                    attr({ name: "count", typeName: "int" }),
                    attr({ name: "flag", typeName: "boolean" }),
                    attr({ name: "when", typeName: "date" }),
                    attr({ name: "aliases", typeName: "array<string>", cardinality: "SET" }),
                    attr({ name: "queries", typeName: "array<string>", cardinality: "LIST" }),
                ]),
            ],
        ]);

        const kinds = Object.fromEntries(buildFields(defs.get("Wide")!, defs, new Map()).map((f) => [f.name, f.kind]));

        expect(kinds).toEqual({
            count: "number",
            flag: "boolean",
            aliases: "multi",
            queries: "multi",
            textAttr: "text",
            when: "date",
        });
    });

    it("renders definition/description as the textarea, name required", () => {
        const defs = new Map<string, AtlasEntityDef>([
            ["E", entityDef("E", [attr({ name: "name" }), attr({ name: "definition", isOptional: true })])],
        ]);

        const fields = buildFields(defs.get("E")!, defs, new Map());

        expect(fields.map((f) => [f.name, f.kind, f.required])).toEqual([
            ["name", "text", true],
            ["definition", "textarea", false],
        ]);
    });

    it("drops the struct/map/entity-array attributes and lists of entities (7.7b)", () => {
        const defs = new Map<string, AtlasEntityDef>([
            [
                "E",
                entityDef("E", [
                    attr({ name: "name" }),
                    attr({ name: "awsTags", typeName: "array<aws_tag>", cardinality: "SINGLE" }),
                    attr({ name: "inputToProcesses", typeName: "array<Process>", cardinality: "SET" }),
                ]),
            ],
        ]);

        expect(buildFields(defs.get("E")!, defs, new Map()).map((f) => f.name)).toEqual(["name"]);
    });

    it("disables a unique attribute other than name (it locates the entity)", () => {
        const defs = new Map<string, AtlasEntityDef>([
            [
                "E",
                entityDef("E", [
                    attr({ name: "name", isUnique: true }),
                    attr({ name: "qualifiedName", isUnique: true }),
                    attr({ name: "code", isUnique: true }),
                ]),
            ],
        ]);

        const fields = buildFields(defs.get("E")!, defs, new Map());

        expect(fields.map((f) => [f.name, f.disabled])).toEqual([
            ["name", false],
            ["code", true],
        ]);
    });

    it("orders name, then the description key, then the rest by name", () => {
        const defs = new Map<string, AtlasEntityDef>([
            [
                "E",
                entityDef("E", [
                    attr({ name: "zeta" }),
                    attr({ name: "definition", isOptional: true }),
                    attr({ name: "name" }),
                    attr({ name: "alpha", isOptional: true }),
                ]),
            ],
        ]);

        expect(buildFields(defs.get("E")!, defs, new Map()).map((f) => f.name)).toEqual([
            "name",
            "definition",
            "alpha",
            "zeta",
        ]);
    });

    it("labels an enum from its elementDefs, by ordinal", () => {
        const enums = new Map<string, AtlasEnumDef>([
            [
                "tier",
                {
                    name: "tier",
                    elementDefs: [
                        { value: "gold", ordinal: 2 },
                        { value: "bronze", ordinal: 0 },
                        { value: "silver", ordinal: 1 },
                    ],
                },
            ],
        ]);
        const defs = new Map<string, AtlasEntityDef>([
            ["E", entityDef("E", [attr({ name: "tier", typeName: "tier" })])],
        ]);

        const [tier] = buildFields(defs.get("E")!, defs, enums);

        expect(tier.kind).toBe("enum");
        expect(tier.enumValues).toEqual(["bronze", "silver", "gold"]);
    });

    it("uses the passed labels, then displayName, then the name (EDT-11/EDT-03)", () => {
        const defs = new Map<string, AtlasEntityDef>([
            [
                "E",
                entityDef("E", [
                    attr({ name: "name" }),
                    attr({ name: "shown", displayName: "Shown attr" }),
                    attr({ name: "plain" }),
                ]),
            ],
        ]);

        const fields = buildFields(defs.get("E")!, defs, new Map(), { name: "Name*" });

        // The fields ride EDT-03's order (name, then by attribute name:
        // "plain" before "shown"), each with its own label source.
        expect(fields.map((f) => f.label)).toEqual(["Name*", "plain", "Shown attr"]);
    });
});

describe("toFormValues (EDT-02)", () => {
    it("reads a date as a datetime-local string, a multi as a list", () => {
        const defs = new Map<string, AtlasEntityDef>([
            [
                "E",
                entityDef("E", [
                    attr({ name: "when", typeName: "date" }),
                    attr({ name: "aliases", typeName: "array<string>", cardinality: "SET" }),
                ]),
            ],
        ]);
        const eFields = buildFields(defs.get("E")!, defs, new Map());
        const values = toFormValues(
            { attributes: { when: Date.UTC(2026, 0, 15, 9, 30), aliases: ["a", "b"] } },
            eFields,
        );

        expect(values["aliases"]).toEqual(["a", "b"]);
        expect(String(values["when"])).toMatch(/2026-01-15T/);
    });

    it("defaults missing values to '' and booleans to false", () => {
        const defs = new Map<string, AtlasEntityDef>([
            ["E", entityDef("E", [attr({ name: "flag", typeName: "boolean" })])],
        ]);

        expect(toFormValues({ attributes: {} }, buildFields(defs.get("E")!, defs, new Map()))["flag"]).toBe(false);
    });
});

describe("mergeOntoEntity (EDT-06)", () => {
    const defs = new Map<string, AtlasEntityDef>([
        [
            "E",
            entityDef("E", [
                attr({ name: "name" }),
                attr({ name: "count", typeName: "int", isOptional: true }),
                attr({ name: "when", typeName: "date", isOptional: true }),
                attr({ name: "aliases", typeName: "array<string>", cardinality: "SET", isOptional: true }),
            ]),
        ],
    ]);
    const fields = buildFields(defs.get("E")!, defs, new Map());

    it("writes the fields and passes relationshipAttributes through", () => {
        const entity = {
            guid: "g1",
            typeName: "E",
            attributes: { name: "old", hidden: 1 },
            relationshipAttributes: { inputToProcesses: [{ guid: "p" }] },
        };

        const merged = mergeOntoEntity(entity, fields, { name: "new", count: "12", when: "", aliases: [] });

        expect(merged.attributes).toEqual({ name: "new", hidden: 1, count: 12 });
        expect(merged.relationshipAttributes).toEqual(entity.relationshipAttributes);
        expect(merged.guid).toBe("g1");
    });

    it("parses a date to epoch ms, a multi to a trimmed list, drops empties", () => {
        const merged = mergeOntoEntity({ attributes: {} }, fields, {
            name: "n",
            count: "",
            when: "2026-01-15T09:30",
            aliases: [" a ", "", "b"],
        });

        expect(merged.attributes).toEqual({
            name: "n",
            when: new Date("2026-01-15T09:30").getTime(),
            aliases: ["a", "b"],
        });
    });
});
