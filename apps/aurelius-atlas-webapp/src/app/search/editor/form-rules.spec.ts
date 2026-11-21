/**
 * WFE-05: the form rules `form-fields.ts` copies from the server hold against
 * a fixture the server's own tests produce (DD-805). The Python producer is
 * `apps/aurelius-atlas-server/tests/test__form_rule_vocabulary.py`: it derives
 * the vocabulary from the server's constants and the AVS-03 card rule, and byte-pins
 * the fixture. This spec is the client half of that guard — a rule here that drifts
 * from the fixture fails, and the fixture drifting from the server fails over there,
 * so a server change can never leave the client copy behind quietly.
 */
import type { AtlasAttributeDef, AtlasRelationshipAttributeDef, Cardinality } from "aurelius-atlas-data-access";
import { describe, expect, it } from "vitest";

import formRulesJson from "../../../../tests/fixtures/form-rules.json";
import { DESCRIPTION_KEYS, NUMERIC_TYPES, buildFields, buildRelationshipFields } from "./form-fields";

/** The server-produced vocabulary (WFE-05, DD-805). */
const RULES = formRulesJson as {
    arrayPrefix: string;
    arraySuffix: string;
    booleanType: string;
    cardinalityMulti: string[];
    cardinalitySingle: string;
    constraintGroupParam: string;
    constraintType: string;
    dateType: string;
    descriptionKeys: string[];
    numericTypes: string[];
    textType: string;
};

/** An attribute definition with defaults the shipped store's carry. */
function attr(overrides: Partial<AtlasAttributeDef> & { name: string }): AtlasAttributeDef {
    return {
        typeName: RULES.textType,
        isOptional: false,
        cardinality: RULES.cardinalitySingle as Cardinality,
        ...overrides,
    };
}

/** A relationship attribute with the shipped defaults. */
function ra(overrides: Partial<AtlasRelationshipAttributeDef> & { name: string }): AtlasRelationshipAttributeDef {
    return {
        typeName: "Process",
        isOptional: true,
        cardinality: RULES.cardinalityMulti[0] as Cardinality,
        ...overrides,
    };
}

/** An entity definition carrying attributes and relationship attributes. */
function entityDef(
    name: string,
    attributeDefs: AtlasAttributeDef[],
    relationshipAttributeDefs: AtlasRelationshipAttributeDef[] = [],
): { name: string; attributeDefs: AtlasAttributeDef[]; relationshipAttributeDefs: AtlasRelationshipAttributeDef[] } {
    return { name, attributeDefs, relationshipAttributeDefs };
}

/** The kind `buildFields` gives one lone attribute (its parent def is itself). */
function kindFor(overrides: Partial<AtlasAttributeDef> & { name: string }): string | null {
    const def = entityDef("E", [attr(overrides)]);
    const fields = buildFields(def, new Map([["E", def]]), new Map());

    return fields.length === 0 ? null : fields[0].kind;
}

/** The constraint the server's 18.3 parent choice names (PME-01). */
function parentConstraint(group: string): { type: string; params: Record<string, string> } {
    return { type: RULES.constraintType, params: { [RULES.constraintGroupParam]: group } };
}

describe("the form-rule vocabulary (WFE-05, DD-805)", () => {
    it("keeps the fixture's rule names exactly (WFE-05)", () => {
        // The guard keys the fixture copies must equal the vocabulary's names —
        // drop one here and the guard would go quiet on a renamed rule.
        expect(Object.keys(RULES).sort()).toEqual([
            "arrayPrefix",
            "arraySuffix",
            "booleanType",
            "cardinalityMulti",
            "cardinalitySingle",
            "constraintGroupParam",
            "constraintType",
            "dateType",
            "descriptionKeys",
            "numericTypes",
            "textType",
        ]);
    });

    it("renders a number input for every numeric type the server has, and none it lacks (WFE-05)", () => {
        expect([...NUMERIC_TYPES].sort()).toEqual([...RULES.numericTypes].sort());

        for (const typeName of RULES.numericTypes) {
            expect(kindFor({ name: `n_${typeName}`, typeName })).toBe("number");
        }
        // `bigint` was once here and is not an Atlas type (DD-805's founding drift).
        expect(kindFor({ name: "big_int", typeName: "bigint" })).toBeNull();
    });

    it("splits text, boolean and date on the fixture's type names (WFE-05)", () => {
        expect(kindFor({ name: "s", typeName: RULES.textType })).toBe("text");
        expect(kindFor({ name: "b", typeName: RULES.booleanType })).toBe("boolean");
        expect(kindFor({ name: "d", typeName: RULES.dateType })).toBe("date");
    });

    it("routes exactly the fixture's description keys to markdown (WFE-05, EDT-20)", () => {
        expect([...DESCRIPTION_KEYS].sort()).toEqual([...RULES.descriptionKeys].sort());

        for (const name of RULES.descriptionKeys) {
            expect(kindFor({ name })).toBe("markdown");
        }
        expect(kindFor({ name: "summary" })).toBe("text");
    });

    it("repeats a multi field on the fixture's cardinalities alone (WFE-05, EDT-13)", () => {
        const arrayType = `${RULES.arrayPrefix}${RULES.textType}${RULES.arraySuffix}`;
        const defs = entityDef(
            "M",
            RULES.cardinalityMulti.map((cardinality, index) =>
                attr({ name: `list${index}`, typeName: arrayType, cardinality: cardinality as Cardinality }),
            ),
        );

        const kinds = Object.fromEntries(
            buildFields(defs, new Map([["M", defs]]), new Map()).map((field) => [field.name, field.kind]),
        );

        expect(Object.values(kinds)).toEqual(RULES.cardinalityMulti.map(() => "multi"));
        // A value of a cardinality outside the fixture (the single one) is a plain field.
        expect(
            kindFor({ name: "one", typeName: arrayType, cardinality: RULES.cardinalitySingle as Cardinality }),
        ).toBeNull();
    });

    it("sees the 18.3 parent group under the fixture's constraint names (WFE-05, PME-01, PME-03)", () => {
        const group = "parent_choice";
        const def = entityDef(
            "E",
            [],
            [
                ra({
                    name: "a",
                    cardinality: RULES.cardinalitySingle as Cardinality,
                    constraints: [parentConstraint(group)],
                }),
                ra({
                    name: "b",
                    cardinality: RULES.cardinalitySingle as Cardinality,
                    constraints: [parentConstraint(group)],
                }),
            ],
        );

        const parentGroups = Object.fromEntries(
            buildRelationshipFields(def, new Map([["E", def]]), {}, []).map((field) => [field.name, field.parentGroup]),
        );

        expect(parentGroups).toEqual({ a: group, b: group });
    });
});
