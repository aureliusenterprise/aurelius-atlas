import type {
    AtlasAttributeDef,
    AtlasEntityDef,
    AtlasEnumDef,
    AtlasRelationshipAttributeDef,
    AtlasRelationshipDef,
    EntityCard,
} from "aurelius-atlas-data-access";

import {
    blockedRelationshipNames,
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

    it("renders definition/description as the markdown field, name required (EDT-20)", () => {
        const defs = new Map<string, AtlasEntityDef>([
            ["E", entityDef("E", [attr({ name: "name" }), attr({ name: "definition", isOptional: true })])],
        ]);

        const fields = buildFields(defs.get("E")!, defs, new Map());

        // The kind flips from the 7.7a textarea on purpose (EDT-20, DD-352):
        // the description keys ride the ui library's markdown field now.
        expect(fields.map((f) => [f.name, f.kind, f.required])).toEqual([
            ["name", "text", true],
            ["definition", "markdown", false],
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

    it("orders name, then the description key, then the rest by label (EDT-03, DD-727)", () => {
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

        // No catalogue key, so each label falls back to the name and the
        // reader sees name order — the fallback keeps today's behaviour.
        expect(buildFields(defs.get("E")!, defs, new Map()).map((f) => f.name)).toEqual([
            "name",
            "definition",
            "alpha",
            "zeta",
        ]);
    });

    it("orders the rest by the label a reader sees, not the raw name (EDT-03, DD-727)", () => {
        // The shipped metamodel's people attributes: `steward` sorts after
        // `source` by name, but its catalogue word "Business Data Steward"
        // belongs beside "Business Data Owner" — the label is what the reader
        // scans, so it is what sorts (7.33's labels made the mismatch visible).
        const defs = new Map<string, AtlasEntityDef>([
            [
                "E",
                entityDef("E", [
                    attr({ name: "steward", isOptional: true }),
                    attr({ name: "source", isOptional: true }),
                    attr({ name: "businessOwner", isOptional: true }),
                    attr({ name: "name" }),
                ]),
            ],
        ]);
        const labels = {
            steward: "Business Data Steward",
            source: "Source",
            businessOwner: "Business Data Owner",
        };

        const fields = buildFields(defs.get("E")!, defs, new Map(), labels);

        expect(fields.map((f) => f.name)).toEqual(["name", "businessOwner", "steward", "source"]);
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

        // The fields ride EDT-03's order (name, then by label: "plain" before
        // "Shown attr"), each with its own label source. The catalogue's
        // baked-in star is dropped — the template paints the red one (DD-356).
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
            [
                "E",
                entityDef("E", [
                    attr({ name: "flag", typeName: "boolean" }),
                    attr({ name: "name" }),
                    attr({ name: "aliases", typeName: "array<string>", cardinality: "SET" }),
                ]),
            ],
        ]);
        const fields = buildFields(defs.get("E")!, defs, new Map());

        expect(toFormValues({ attributes: {} }, fields)["flag"]).toBe(false);
        expect(toFormValues({ attributes: { name: { nested: true }, aliases: [{ nested: true }] } }, fields)).toEqual({
            flag: false,
            name: "",
            aliases: [""],
        });
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

    it("orders the pickers by label, the name only as tie-break (EDT-13, DD-727)", () => {
        // The people pair from the shipped store: raw names put `steward`
        // after `source`, the labels keep the two people pickers together.
        const people = raDef("People", [
            ra({ name: "steward", typeName: "Person" }),
            ra({ name: "source", typeName: "Person" }),
            ra({ name: "businessOwner", typeName: "Person" }),
        ]);
        const labels = {
            steward: "Business Data Steward",
            source: "Source",
            businessOwner: "Business Data Owner",
        };

        expect(buildRelationshipFields(people, new Map([["People", people]]), labels).map((f) => f.name)).toEqual([
            "businessOwner",
            "steward",
            "source",
        ]);
    });

    it("labels the attribute name alone, with no target-type bracket (EDT-34, DD-724)", () => {
        const fields = Object.fromEntries(buildRelationshipFields(DATASET, defs).map((f) => [f.name, f]));

        expect(fields["inputToProcesses"].label).toBe("inputToProcesses");
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

describe("a hierarchy child picker (HCA-06, 18.2)", () => {
    const DATASET = raDef(
        "m4i_dataset",
        [
            ra({
                name: "parentDataset",
                typeName: "m4i_dataset",
                cardinality: "SINGLE",
                relationshipTypeName: "m4i_dataset_parent_assignment",
            }),
            ra({
                name: "badgeOf",
                typeName: "m4i_data_domain",
                cardinality: "SET",
                relationshipTypeName: "m4i_data_entity_assignment",
            }),
        ],
        ["Asset"],
    );
    const fields = buildRelationshipFields(DATASET, new Map([["m4i_dataset", DATASET]]));

    it("a SINGLE child end renders the one picker", () => {
        const parent = fields.find((field) => field.name === "parentDataset");

        expect(parent?.single).toBe(true);
        expect(parent?.targetType).toBe("m4i_dataset");
    });

    it("a read of the old shape still seeds the one chip", () => {
        const entity = {
            relationshipAttributes: {
                parentDataset: [
                    { guid: "p1", typeName: "m4i_dataset", relationshipStatus: "ACTIVE" },
                    { guid: "p2", typeName: "m4i_dataset", relationshipStatus: "ACTIVE" },
                ],
            },
        };

        expect(seedRelationshipValues(entity, fields)["parentDataset"]).toEqual([
            { guid: "p1", typeName: "m4i_dataset" },
        ]);
    });

    it("the save answers the one parent object, or null when cleared", () => {
        const named = mergeRelationshipsOntoEntity(
            { attributes: {}, relationshipAttributes: {} },
            fields,
            new Map([
                [
                    "parentDataset",
                    [
                        { guid: "p1", typeName: "m4i_dataset" },
                        { guid: "p2", typeName: "m4i_dataset" },
                    ],
                ],
            ]),
        );
        const cleared = mergeRelationshipsOntoEntity(
            { attributes: {}, relationshipAttributes: {} },
            fields,
            new Map([["parentDataset", []]]),
        );

        expect(named.relationshipAttributes?.["parentDataset"]).toEqual({
            guid: "p1",
            typeName: "m4i_dataset",
            relationshipType: "m4i_dataset_parent_assignment",
            relationshipStatus: "ACTIVE",
        });
        expect(cleared.relationshipAttributes?.["parentDataset"]).toBeNull();
    });
});

describe("a parent group's pickers (PME-10, 18.3)", () => {
    const GROUP = [{ type: "mutuallyExclusive", params: { group: "m4i_data_entity_parent" } }];
    const ENTITY = raDef("m4i_data_entity", [
        ra({
            name: "dataDomain",
            typeName: "m4i_data_domain",
            cardinality: "SINGLE",
            relationshipTypeName: "m4i_data_entity_assignment",
            constraints: GROUP,
        }),
        ra({
            name: "parentEntity",
            typeName: "m4i_data_entity",
            cardinality: "SINGLE",
            relationshipTypeName: "m4i_parent_entity_assignment",
            constraints: GROUP,
        }),
        ra({ name: "steward", typeName: "m4i_person" }),
    ]);
    const byName = Object.fromEntries(
        buildRelationshipFields(ENTITY, new Map([["m4i_data_entity", ENTITY]])).map((f) => [f.name, f]),
    );

    it("reads the mutuallyExclusive group off the derived attribute (PME-01, PME-02, PME-05)", () => {
        expect(byName["dataDomain"].parentGroup).toBe("m4i_data_entity_parent");
        expect(byName["parentEntity"].parentGroup).toBe("m4i_data_entity_parent");
    });

    it("leaves an attribute that carries no constraint ungrouped", () => {
        expect(byName["steward"].parentGroup).toBeUndefined();
    });

    it("ignores a constraint that is not a mutual exclusion", () => {
        const owned = raDef("E", [
            ra({ name: "children", typeName: "array<E>", constraints: [{ type: "ownedRef" }] }),
            ra({ name: "parent", typeName: "E", cardinality: "SINGLE", constraints: [{ type: "ownedRef" }] }),
        ]);

        expect(
            buildRelationshipFields(owned, new Map([["E", owned]])).every((field) => field.parentGroup === undefined),
        ).toBe(true);
    });

    it("leaves a group with one member on the type unenforced (PME-03)", () => {
        // A lone member enforces nothing server-side, so the form must not
        // disable anything over it either.
        const lone = raDef("E", [
            ra({ name: "dataDomain", typeName: "m4i_data_domain", cardinality: "SINGLE", constraints: GROUP }),
            ra({ name: "steward", typeName: "m4i_person" }),
        ]);
        const loneFields = Object.fromEntries(
            buildRelationshipFields(lone, new Map([["E", lone]])).map((f) => [f.name, f]),
        );

        expect(loneFields["dataDomain"].parentGroup).toBeUndefined();
    });

    it("ignores a mutual exclusion whose group is not a usable name", () => {
        const blank = raDef("E", [
            ra({ name: "a", typeName: "E", constraints: [{ type: "mutuallyExclusive", params: { group: "" } }] }),
            ra({ name: "b", typeName: "E", constraints: [{ type: "mutuallyExclusive", params: {} }] }),
        ]);

        expect(
            buildRelationshipFields(blank, new Map([["E", blank]])).every((field) => field.parentGroup === undefined),
        ).toBe(true);
    });

    // The blocked-pickers rule (WFE-04, DD-806), decided on the fields and the
    // current picks — no component, no DOM. The group's members above:
    // dataDomain and parentEntity share the group; steward has none.
    const FIELDS = buildRelationshipFields(ENTITY, new Map([["m4i_data_entity", ENTITY]]));
    const pick = (guid: string) => [{ guid, typeName: "x", relationshipType: "y", relationshipStatus: "ACTIVE" }];
    const picks = (entries: Record<string, readonly unknown[]>): ReadonlyMap<string, readonly unknown[]> =>
        new Map(Object.entries(entries));

    it("blocks nothing while the group holds no value (PME-10)", () => {
        const blocked = blockedRelationshipNames(FIELDS, picks({ dataDomain: [], parentEntity: [] }));

        expect([...blocked]).toEqual([]);
    });

    it("a filled member blocks its empty sibling, and holds itself live (PME-10)", () => {
        // Filling dataDomain makes parentEntity unfillable (the PME-07 rule the
        // server applies on save), but dataDomain itself stays live so the
        // choice can be deleted and switched.
        const blocked = blockedRelationshipNames(FIELDS, picks({ dataDomain: pick("d1") }));

        expect([...blocked]).toEqual(["parentEntity"]);
        expect(blocked.has("dataDomain")).toBe(false);
    });

    it("a filled member blocks the other way too (PME-10, PME-08)", () => {
        const blocked = blockedRelationshipNames(FIELDS, picks({ parentEntity: pick("p1") }));

        expect([...blocked]).toEqual(["dataDomain"]);
    });

    it("nothing is blocked when both members hold a value (PME-10)", () => {
        // Both hold, so neither is an empty sibling — a stale double-pick
        // disables nothing; the server's save rejects it.
        const blocked = blockedRelationshipNames(FIELDS, picks({ dataDomain: pick("d1"), parentEntity: pick("p1") }));

        expect([...blocked]).toEqual([]);
    });

    it("a field with no parent group is never blocked (PME-10)", () => {
        // steward shares no group: filling it must not block the parents, and
        // a held parent must not block it.
        const blocked = blockedRelationshipNames(FIELDS, picks({ steward: pick("s1"), dataDomain: pick("d1") }));

        expect(blocked.has("steward")).toBe(false);
        expect([...blocked]).toEqual(["parentEntity"]);
    });
});

describe("a parent-side picker (RPS-07, 18.4)", () => {
    /** The data dictionary's hierarchy relationship: a `SINGLE` child end and a
     * `SET` parent end (HCA-01), plus a plain association both ends of which
     * are `SINGLE` — the shape the picker must not confuse with a hierarchy. */
    const RELATIONSHIPS: AtlasRelationshipDef[] = [
        {
            name: "m4i_dataset_parent_assignment",
            endDef1: { type: "m4i_dataset", name: "parentDataset", cardinality: "SINGLE" },
            endDef2: { type: "m4i_dataset", name: "childDataset", cardinality: "SET" },
        },
        {
            name: "m4i_dataset_assignment",
            endDef1: { type: "m4i_dataset", name: "collections", cardinality: "SINGLE" },
            endDef2: { type: "m4i_collection", name: "datasets", cardinality: "SET" },
        },
        {
            name: "m4i_field_assignment",
            endDef1: { type: "m4i_field", name: "datasets", cardinality: "SINGLE" },
            endDef2: { type: "m4i_dataset", name: "fields", cardinality: "SET" },
        },
        {
            name: "m4i_referenceable_source_assignment",
            endDef1: { type: "m4i_dataset", name: "source", cardinality: "SET" },
            endDef2: { type: "m4i_source", name: "assets", cardinality: "SET" },
        },
    ];
    const DATASET = raDef(
        "m4i_dataset",
        [
            ra({
                name: "parentDataset",
                typeName: "m4i_dataset",
                cardinality: "SINGLE",
                relationshipTypeName: "m4i_dataset_parent_assignment",
            }),
            ra({
                name: "collections",
                typeName: "m4i_collection",
                cardinality: "SINGLE",
                relationshipTypeName: "m4i_dataset_assignment",
            }),
            ra({
                name: "childDataset",
                typeName: "array<m4i_dataset>",
                cardinality: "SET",
                relationshipTypeName: "m4i_dataset_parent_assignment",
            }),
            ra({
                name: "fields",
                typeName: "array<m4i_field>",
                cardinality: "SET",
                relationshipTypeName: "m4i_field_assignment",
            }),
            ra({
                name: "source",
                typeName: "array<m4i_source>",
                cardinality: "SET",
                relationshipTypeName: "m4i_referenceable_source_assignment",
            }),
        ],
        ["Asset"],
    );
    const fields = Object.fromEntries(
        buildRelationshipFields(DATASET, new Map([["m4i_dataset", DATASET]]), {}, RELATIONSHIPS).map((f) => [
            f.name,
            f,
        ]),
    );

    it("the SET end of a hierarchy is recognised as parent-side (RPS-07)", () => {
        expect(fields["childDataset"].parentSide).toBe(true);
        expect(fields["fields"].parentSide).toBe(true);
    });

    it("the SINGLE child end and a SET-to-SET association are not (RPS-07, DD-759)", () => {
        // The child side must still offer every candidate: choosing a held one
        // there is the legitimate move of the edited entity itself (DD-759).
        expect(fields["parentDataset"].parentSide).toBeUndefined();
        expect(fields["collections"].parentSide).toBeUndefined();
        expect(fields["source"].parentSide).toBeUndefined();
    });

    it("the collection's datasets picker filters its search (DCP-06, RPS-07)", () => {
        // 18.5's dictionary shape: the collection holds the SET end of the same
        // hierarchy, so its picker is parent-side and the dataset's SINGLE
        // collections end is not.
        const COLLECTION = raDef("m4i_collection", [
            ra({
                name: "datasets",
                typeName: "array<m4i_dataset>",
                cardinality: "SET",
                relationshipTypeName: "m4i_dataset_assignment",
            }),
        ]);
        const collectionFields = Object.fromEntries(
            buildRelationshipFields(COLLECTION, new Map([["m4i_collection", COLLECTION]]), {}, RELATIONSHIPS).map(
                (f) => [f.name, f],
            ),
        );

        expect(collectionFields["datasets"].parentSide).toBe(true);
    });

    it("without the relationship defs no picker filters (RPS-07)", () => {
        const plain = Object.fromEntries(
            buildRelationshipFields(DATASET, new Map([["m4i_dataset", DATASET]])).map((f) => [f.name, f]),
        );

        expect(plain["childDataset"].parentSide).toBeUndefined();
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

    it("maps a view-family card to a pick (EDT-33)", () => {
        // The picker's rows come from the view door now (DD-711); a card fits
        // the structural source and its qualified name rides the value. Only
        // the pick's fields leave — the card's trail and status do not.
        const found: EntityCard = {
            guid: "g",
            typeName: "Process",
            displayText: "load",
            qualifiedName: "domain--load",
            status: "ACTIVE",
            stale: false,
            breadcrumb: [{ guid: "d", name: "Domain" }],
        };
        expect(relationshipEntry(found)).toEqual({
            guid: "g",
            typeName: "Process",
            displayText: "load",
            qualifiedName: "domain--load",
        });
    });

    it("refuses a header with no guid to attach", () => {
        expect(relationshipEntry({ typeName: "Process", displayText: "load" })).toBeNull();
    });
});
