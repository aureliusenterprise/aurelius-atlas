import type {
    AtlasAttributeDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasRelationshipAttributeDef,
} from "aurelius-atlas-data-access";

import {
    buildFields,
    buildRelationshipFields,
    mergeOntoEntity,
    mergeRelationshipsOntoEntity,
    relationshipEntry,
    seedRelationshipValues,
    toFormValues,
} from "./form-fields";

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

    it("drops the struct/map/entity-array attributes and lists of entities (7.7c)", () => {
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
        // "plain" before "shown"), each with its own label source. The
        // catalogue's baked-in star is dropped — the template paints the
        // red one (DD-356).
        expect(fields.map((f) => f.label)).toEqual(["Name", "plain", "Shown attr"]);
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

/** A relationship-attribute definition with the shipped store's defaults. */
function ra(overrides: Partial<AtlasRelationshipAttributeDef> & { name: string }): AtlasRelationshipAttributeDef {
    return {
        typeName: "Process",
        isOptional: true,
        cardinality: "SET",
        ...overrides,
    };
}

/** A DataSet-style def carrying relationship attributes (7.7c's shape). */
function raDef(
    name: string,
    relationshipAttributeDefs: AtlasRelationshipAttributeDef[],
    superTypes: string[] = [],
): AtlasEntityDef {
    return { name, attributeDefs: [], relationshipAttributeDefs, superTypes };
}

describe("buildRelationshipFields (EDT-13, DD-338)", () => {
    const DATASET = raDef(
        "DataSet",
        [
            ra({
                name: "inputToProcesses",
                typeName: "array<Process>",
                relationshipTypeName: "dataset_process_inputs",
            }),
            ra({
                name: "model",
                typeName: "spark_ml_model",
                cardinality: "SINGLE",
                relationshipTypeName: "model_pipeline",
            }),
            ra({
                name: "meanings",
                typeName: "array<AtlasGlossaryTerm>",
                relationshipTypeName: "AtlasGlossarySemanticAssignment",
            }),
        ],
        ["Asset"],
    );
    const ASSET = raDef("Asset", [ra({ name: "terms", typeName: "array<AtlasGlossaryTerm>" })], ["Referenceable"]);
    const defs = new Map<string, AtlasEntityDef>([
        ["DataSet", DATASET],
        ["Asset", ASSET],
    ]);

    it("walks the supertype chain for relationship attributes", () => {
        const names = buildRelationshipFields(DATASET, defs).map((f) => f.name);

        expect(names).toEqual(["inputToProcesses", "meanings", "model", "terms"]);
    });

    it("unwraps array<X> to X and reads SINGLE/SET cardinality", () => {
        const fields = Object.fromEntries(buildRelationshipFields(DATASET, defs).map((f) => [f.name, f]));

        expect(fields["inputToProcesses"].targetType).toBe("Process");
        expect(fields["inputToProcesses"].single).toBe(false);
        expect(fields["model"].targetType).toBe("spark_ml_model");
        expect(fields["model"].single).toBe(true);
    });

    it("labels the field name plus the target type in brackets", () => {
        const fields = Object.fromEntries(buildRelationshipFields(DATASET, defs).map((f) => [f.name, f]));

        expect(fields["inputToProcesses"].label).toBe("inputToProcesses (Process)");
    });

    it("marks a non-optional definition required (EDT-17)", () => {
        const forced = raDef("E", [
            ra({ name: "pseudoDirectory", typeName: "aws_s3_bucket", cardinality: "SINGLE", isOptional: false }),
        ]);

        expect(buildRelationshipFields(forced, new Map([["E", forced]]))[0].required).toBe(true);
    });

    it("merges a name two defs carry to the first def's relationshipTypeName (DD-338)", () => {
        const column = raDef(
            "hive_column",
            [ra({ name: "table", typeName: "hive_table", relationshipTypeName: "hive_table_columns" })],
            ["hive_table_partitionkeys"],
        );
        const partitionKeys = raDef("hive_table_partitionkeys", [
            ra({ name: "table", typeName: "hive_table", relationshipTypeName: "hive_table_partitionkeys" }),
        ]);
        const merged = new Map([
            ["hive_column", column],
            ["hive_table_partitionkeys", partitionKeys],
        ]);

        const fields = buildRelationshipFields(column, merged);

        expect(fields).toHaveLength(1);
        expect(fields[0].relationshipTypeName).toBe("hive_table_columns");
    });

    it("keeps the relationshipTypeName off a def that carries none", () => {
        const fields = Object.fromEntries(buildRelationshipFields(DATASET, defs).map((f) => [f.name, f]));

        expect(fields["terms"].relationshipTypeName).toBeUndefined();
    });

    it("a type with no relationship attributes gets no fields", () => {
        expect(buildRelationshipFields(entityDef("Bare", []), new Map())).toEqual([]);
    });
});

describe("seedRelationshipValues (EDT-15)", () => {
    const fields = buildRelationshipFields(
        raDef("DataSet", [
            ra({ name: "inputToProcesses", typeName: "array<Process>" }),
            ra({ name: "model", typeName: "spark_ml_model", cardinality: "SINGLE" }),
        ]),
        new Map(),
    );

    it("seeds a SET from the ACTIVE entries only (DELETED never shows)", () => {
        const entity = {
            relationshipAttributes: {
                inputToProcesses: [
                    { guid: "p1", typeName: "Process", displayText: "load", relationshipStatus: "ACTIVE" },
                    { guid: "p2", typeName: "Process", displayText: "gone", relationshipStatus: "DELETED" },
                ],
            },
        };

        expect(seedRelationshipValues(entity, fields)["inputToProcesses"]).toEqual([
            { guid: "p1", typeName: "Process", displayText: "load" },
        ]);
    });

    it("seeds a SINGLE from its first ACTIVE entry (the read's bare object)", () => {
        const entity = {
            relationshipAttributes: {
                model: { guid: "m1", typeName: "spark_ml_model", displayText: "m", relationshipStatus: "ACTIVE" },
            },
        };

        expect(seedRelationshipValues(entity, fields)["model"]).toEqual([
            { guid: "m1", typeName: "spark_ml_model", displayText: "m" },
        ]);
    });

    it("seeds a cleared SINGLE (null) as nothing", () => {
        expect(seedRelationshipValues({ relationshipAttributes: { model: null } }, fields)["model"]).toEqual([]);
    });

    it("create mode (no relationshipAttributes) seeds nothing", () => {
        const seeded = seedRelationshipValues({}, fields);

        expect(seeded["inputToProcesses"]).toEqual([]);
        expect(seeded["model"]).toEqual([]);
    });

    it("falls back to qualifiedName then guid for the label fields", () => {
        const entity = { relationshipAttributes: { inputToProcesses: [{ guid: "p1", qualifiedName: "qn@x" }] } };

        expect(seedRelationshipValues(entity, fields)["inputToProcesses"][0].qualifiedName).toBe("qn@x");
    });
});

describe("mergeRelationshipsOntoEntity (EDT-16, DD-340)", () => {
    const fields = buildRelationshipFields(
        raDef("DataSet", [
            ra({
                name: "inputToProcesses",
                typeName: "array<Process>",
                relationshipTypeName: "dataset_process_inputs",
            }),
            ra({
                name: "model",
                typeName: "spark_ml_model",
                cardinality: "SINGLE",
                relationshipTypeName: "spark_ml_model_pipeline",
            }),
        ]),
        new Map(),
    );

    it("writes the full entry list with the EDT-16 shape", () => {
        const merged = mergeRelationshipsOntoEntity(
            { attributes: {}, relationshipAttributes: {} },
            fields,
            new Map([
                ["inputToProcesses", [{ guid: "p1", typeName: "Process", displayText: "load" }]],
                ["model", []],
            ]),
        );

        expect(merged.relationshipAttributes?.["inputToProcesses"]).toEqual([
            {
                guid: "p1",
                typeName: "Process",
                displayText: "load",
                relationshipType: "dataset_process_inputs",
                relationshipStatus: "ACTIVE",
            },
        ]);
    });

    it("an emptied multi picker sends [] and an emptied SINGLE sends null", () => {
        const merged = mergeRelationshipsOntoEntity(
            { attributes: {}, relationshipAttributes: { inputToProcesses: [], model: null } },
            fields,
            new Map([
                ["inputToProcesses", []],
                ["model", []],
            ]),
        );

        expect(merged.relationshipAttributes?.["inputToProcesses"]).toEqual([]);
        expect(merged.relationshipAttributes?.["model"]).toBeNull();
    });

    it("a SINGLE picker sends the one object, not a list", () => {
        const merged = mergeRelationshipsOntoEntity(
            { attributes: {}, relationshipAttributes: {} },
            fields,
            new Map([
                ["inputToProcesses", []],
                ["model", [{ guid: "m1", typeName: "spark_ml_model" }]],
            ]),
        );

        expect(merged.relationshipAttributes?.["model"]).toEqual({
            guid: "m1",
            typeName: "spark_ml_model",
            relationshipType: "spark_ml_model_pipeline",
            relationshipStatus: "ACTIVE",
        });
    });

    it("drops each rendered key from attributes (the picker owns it, DD-340)", () => {
        const merged = mergeRelationshipsOntoEntity(
            { attributes: { inputToProcesses: [{ guid: "stale" }], owner: "me" }, relationshipAttributes: {} },
            fields,
            new Map([
                ["inputToProcesses", []],
                ["model", []],
            ]),
        );

        expect(merged.attributes).toEqual({ owner: "me" });
    });

    it("a key no picker rendered passes through untouched", () => {
        const onlyInputs = buildRelationshipFields(
            raDef("DataSet", [ra({ name: "inputToProcesses", typeName: "array<Process>" })]),
            new Map(),
        );
        const merged = mergeRelationshipsOntoEntity(
            {
                attributes: { otherRef: [{ guid: "keep" }] },
                relationshipAttributes: { otherRef: [{ guid: "keep", relationshipStatus: "ACTIVE" }] },
            },
            onlyInputs,
            new Map([["inputToProcesses", []]]),
        );

        expect(merged.relationshipAttributes?.["otherRef"]).toEqual([{ guid: "keep", relationshipStatus: "ACTIVE" }]);
    });

    it("a DELETED seed never echoes (the seed never holds one, EDT-15)", () => {
        const entity = {
            attributes: {},
            relationshipAttributes: { inputToProcesses: [{ guid: "gone", relationshipStatus: "DELETED" }] },
        };
        const seeded = seedRelationshipValues(entity, fields);

        const merged = mergeRelationshipsOntoEntity(
            mergeOntoEntity(entity, [], {}),
            fields,
            new Map(Object.entries(seeded)),
        );

        expect(merged.relationshipAttributes?.["inputToProcesses"]).toEqual([]);
    });
});

describe("relationshipEntry (EDT-14's pick path)", () => {
    it("maps a search header to a pick", () => {
        expect(relationshipEntry({ guid: "g", typeName: "Process", displayText: "load" })).toEqual({
            guid: "g",
            typeName: "Process",
            displayText: "load",
        });
    });

    it("refuses a header with no guid to attach", () => {
        expect(relationshipEntry({ typeName: "Process", displayText: "load" })).toBeNull();
    });
});
