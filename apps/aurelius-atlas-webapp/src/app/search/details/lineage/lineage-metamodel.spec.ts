import { describe, expect, it } from "vitest";

import { humanReadableType, relationVerb } from "./lineage-metamodel";

/**
 * LDG-20/LDG-37 (DD-418): the metamodel names and the relation verbs, the
 * legacy `metamodel.ts` tables and `parse-relation.ts` `humanReadableTypes`
 * ported whole. The lineage rows keep their 7.22b/7.22c pins; the archimate
 * rows are what a drawer over an archimate document now reads.
 */
describe("lineage-metamodel (LDG-20/LDG-37)", () => {
    it("LDG-37: an archimate type answers the legacy metamodel's name", () => {
        expect(humanReadableType("ar3_Goal")).toBe("Goal");
        expect(humanReadableType("ar3_BusinessActor")).toBe("Business Actor");
        expect(humanReadableType("ar3_AndJunction")).toBe("And Junction");
        expect(humanReadableType("ar3_CourseOfAction")).toBe("Course of Action");
        // The unknown type answers the legacy's placeholder verbatim.
        expect(humanReadableType("ar3_Unknown")).toBe("-- Please select a type --");
        // The lineage rows the shipped chain produces are unchanged.
        expect(humanReadableType("lineage_dataset")).toBe("Dataset");
        expect(humanReadableType("lineage_relation")).toBe("Data Lineage");
        expect(humanReadableType("ar3_View")).toBe("View");
    });

    it("LDG-37: a bare element or junction carries no name, as in the legacy", () => {
        expect(humanReadableType("ar3_Element")).toBe("");
        expect(humanReadableType("ar3_Junction")).toBe("");
        expect(humanReadableType("")).toBe("");
    });

    it("LDG-37/DD-411: each archimate relation answers its legacy verb phrase", () => {
        expect(relationVerb("ar3_Access")).toBe("Accesses");
        expect(relationVerb("ar3_Aggregation")).toBe("Aggregates");
        expect(relationVerb("ar3_Assignment")).toBe("Assigned to");
        expect(relationVerb("ar3_Association")).toBe("Associated with");
        expect(relationVerb("ar3_Composition")).toBe("Composes");
        expect(relationVerb("ar3_Flow")).toBe("Flows into");
        expect(relationVerb("ar3_Influence")).toBe("Influences");
        expect(relationVerb("ar3_Realization")).toBe("Realizes");
        expect(relationVerb("ar3_Serving")).toBe("Serves");
        expect(relationVerb("ar3_Specialization")).toBe("Specializes");
        expect(relationVerb("ar3_Triggering")).toBe("Triggers");
        // The lineage edge keeps its verb; an unknown type answers empty.
        expect(relationVerb("lineage_relation")).toBe("Flows into");
        expect(relationVerb("ar3_Relationship")).toBe("");
    });
});
