/**
 * The view/Atlas bridge (VDE-01, VDE-03..VDE-05, VDE-07, DD-608, DD-612): the
 * adapter that answers the editor's Atlas-shaped helpers from a view, the
 * door body built from the rendered pickers, and the three conflict re-seed
 * helpers. Pure functions — no TestBed.
 */
import type { EntityView, ViewSaveRequest } from "aurelius-atlas-data-access";

import type { EditorField, RelationshipField, RelationshipPick } from "./form-fields";
import { entityFromView } from "../shared/entity-from-view";
import { bodyFromEdits, picksAfterConflict, tagsAfterConflict, valuesAfterConflict } from "./view-as-entity";

/** A text field the way buildFields answers it. */
function textField(name: string, required = false): EditorField {
    return { name, kind: "text", label: name, required, disabled: false };
}

/** A SET picker the way buildRelationshipFields answers it. */
function setPicker(name: string): RelationshipField {
    return { name, label: name, targetType: "Process", single: false, required: false };
}

/** The DataSet view the drawer read: its own values, one tag, one end. */
const VIEW: EntityView = {
    guid: "7a1b",
    typeName: "DataSet",
    qualifiedName: "genomic_variants@cluster",
    displayText: "genomic_variants",
    status: "ACTIVE",
    createTime: 1_700_000_000_000,
    updateTime: 1_700_000_021_000,
    createdBy: "analyst-3",
    updatedBy: "analyst-3",
    classificationNames: ["PII"],
    stale: false,
    attributes: { name: "genomic_variants", owner: "analyst-3" },
    sections: [
        {
            attribute: "inputToProcesses",
            entities: [
                { guid: "p1", name: "load_events", typeName: "Process", status: "ACTIVE" },
                { guid: "p9", typeName: "Process", status: "DELETE_PENDING" },
            ],
        },
    ],
};

const FIELDS = [textField("name", true), textField("owner")];
const PICKER = [setPicker("inputToProcesses")];

describe("entityFromView (VDE-01, VDE-03, VDE-04, DD-608)", () => {
    it("folds the card, the values, the own tags, and the sections into the draft", () => {
        const entity = entityFromView(VIEW);

        expect(entity.guid).toBe("7a1b");
        expect(entity.typeName).toBe("DataSet");
        expect(entity.updateTime).toBe(1_700_000_021_000);
        // The unique qualifiedName rides the card; the draft keeps it inside
        // `attributes` so the form helpers find it as before (VDE-01).
        expect(entity.attributes).toEqual({
            name: "genomic_variants",
            owner: "analyst-3",
            qualifiedName: "genomic_variants@cluster",
        });
        // The view's own names become classifications (VDR-05 — already its
        // own tags, so the client's propagated filter stays retired, VDE-03).
        expect(entity.classifications).toEqual([{ typeName: "PII", entityGuid: "7a1b" }]);
        // Each section rides relationshipAttributes under its attribute name
        // (VDE-04); the flat list keeps the EDT-15 ACTIVE filter working.
        expect(entity.relationshipAttributes).toEqual({
            inputToProcesses: [
                { guid: "p1", typeName: "Process", displayText: "load_events", relationshipStatus: "ACTIVE" },
                { guid: "p9", typeName: "Process", displayText: "", relationshipStatus: "DELETE_PENDING" },
            ],
        });
    });

    it("answers empty lists where the view carries none", () => {
        const entity = entityFromView({ ...VIEW, classificationNames: undefined, sections: undefined });

        expect(entity.classifications).toEqual([]);
        expect(entity.relationshipAttributes).toEqual({});
    });
});

describe("bodyFromEdits (VDE-03..VDE-05, DD-592, DD-609, DD-612)", () => {
    /** The save's parts, overridable one by one. */
    function options(
        overrides: Partial<Parameters<typeof bodyFromEdits>[0]> = {},
    ): Parameters<typeof bodyFromEdits>[0] {
        return {
            base: VIEW,
            entity: entityFromView(VIEW),
            typeName: "DataSet",
            fields: FIELDS,
            values: { name: "renamed_variants", owner: "analyst-3" },
            relationshipFields: PICKER,
            relationshipValues: new Map<string, readonly RelationshipPick[]>([
                ["inputToProcesses", [{ guid: "p1", typeName: "Process" }]],
            ]),
            classifications: ["PII"],
            ...overrides,
        };
    }

    it("posts one update body: the base's version, the merged map, the tags, the ends", () => {
        const body = bodyFromEdits(options());

        // The update names the edited view's version (AVW-04, VDE-05).
        expect(body.guid).toBe("7a1b");
        expect(body.updateTime).toBe(1_700_000_021_000);
        expect(body.typeName).toBe("DataSet");
        expect(body.attributes["name"]).toBe("renamed_variants");
        expect(body.attributes["qualifiedName"]).toBe("genomic_variants@cluster"); // passthrough
        // The tag box's names ride as the full desired set (VDE-03).
        expect(body.classifications).toEqual(["PII"]);
        // One entry per rendered picker, complete desired sets (VDE-04).
        expect(body.sections).toEqual([{ attribute: "inputToProcesses", entities: ["p1"] }]);
    });

    it("a cleared field rides null, so the door drops the stored value", () => {
        const body = bodyFromEdits(options({ values: { name: "renamed_variants", owner: "" } }));

        // The merge removes an empty text key; the door's merge keeps an
        // omitted key (AVW-05) — so a cleared control must ride null
        // (EWR-10: a null optional primitive stores nothing). `owner` is one
        // of the three hidden base attributes, and a control the form does
        // render keeps its write (EDT-37).
        expect(body.attributes["owner"]).toBeNull();
    });

    it("the body names none of the three hidden base attributes (EDT-37)", () => {
        // EDT-37: the editor builds no control for `owner`, `displayName` or
        // `userDescription`, so no key of theirs rides a body — the read
        // carries them, the body builder drops them, and the door's merge
        // leaves the stored values exactly as stored (AVW-05).
        const view: EntityView = {
            ...VIEW,
            attributes: {
                name: "genomic_variants",
                owner: "analyst-3",
                displayName: "Genomic variants",
                userDescription: "a free-text note",
            },
        };
        const body = bodyFromEdits(
            options({
                base: view,
                entity: entityFromView(view),
                fields: [textField("name", true)],
                values: { name: "renamed_variants" },
            }),
        );

        for (const hidden of ["owner", "displayName", "userDescription"]) {
            expect(hidden in body.attributes).toBe(false);
        }
        expect(body.attributes["name"]).toBe("renamed_variants");
        expect(body.attributes["qualifiedName"]).toBe("genomic_variants@cluster");
    });

    it("a picker the form did not render is left out — its set stays unchanged", () => {
        const body = bodyFromEdits(options({ relationshipValues: new Map() }));

        // AVW-05: an omitted set is left alone; only rendered pickers post.
        expect(body.sections).toEqual([]);
    });

    it("the body never carries the door's meanings key (EDT-36, DD-828)", () => {
        const body = bodyFromEdits(
            options({
                relationshipFields: [setPicker("meanings")],
                relationshipValues: new Map<string, readonly RelationshipPick[]>([
                    ["meanings", [{ guid: "t1", typeName: "string" }]],
                ]),
            }),
        );

        // The editor builds no meanings picker (EDT-36), so the bridge has no
        // reason to answer the door's term-assignment key (DD-612 stays the
        // glossary callers' road). The stored assignments ride no key at all,
        // which leaves them unchanged (AVW-05).
        expect(body.meanings).toBeUndefined();
    });

    it("a create names no guid and carries the draft's qualified name (DD-592)", () => {
        const body = bodyFromEdits(
            options({
                base: null,
                entity: { typeName: "DataSet", attributes: { qualifiedName: "uuid-1" } },
                values: { name: "fresh_table", owner: "" },
                relationshipFields: [],
                relationshipValues: new Map(),
                classifications: [],
            }),
        );

        // The server assigns the guid (AVW-06); the client seeded the name.
        expect("guid" in body).toBe(false);
        expect("updateTime" in body).toBe(false);
        expect(body.attributes["qualifiedName"]).toBe("uuid-1");
        expect(body.attributes["name"]).toBe("fresh_table");
        // No picker rendered at all: the door is asked to touch no set — the
        // sections key stays out entirely (AVW-05).
        expect("sections" in body).toBe(false);
        expect(body.classifications).toEqual([]);
    });

    it("the quality branch's full attribute map replaces the field merge (EDT-27)", () => {
        const body = bodyFromEdits(
            options({
                attributes: { name: "total_not_null", dqcheckkind: "COLUMN_NOT_NULL_RATIO" },
                relationshipFields: [setPicker("fields")],
                relationshipValues: new Map<string, readonly RelationshipPick[]>([
                    ["fields", [{ guid: "f1", typeName: "m4i_field" }]],
                ]),
            }),
        );

        // The minimal rule body (no foreign leftovers) rides, unmerged.
        expect(body.attributes).toEqual({ name: "total_not_null", dqcheckkind: "COLUMN_NOT_NULL_RATIO" });
        expect(body.sections).toEqual([{ attribute: "fields", entities: ["f1"] }]);
    });

    it("the body round-trips the door's shape (ViewSaveRequest, VDE-05)", () => {
        const body: ViewSaveRequest = bodyFromEdits(options());

        // A save body is a view the store may write: guid, typeName,
        // attributes — plus the three set keys the editor owns.
        expect(Object.keys(body).sort()).toEqual([
            "attributes",
            "classifications",
            "guid",
            "sections",
            "typeName",
            "updateTime",
        ]);
    });
});

describe("valuesAfterConflict (VDE-07, DD-610)", () => {
    const stored: EntityView = {
        ...VIEW,
        updateTime: 2_000_000_000_000,
        attributes: { name: "stored_variants", owner: "ops-9" },
    };

    it("an untouched control answers the stored value; a touched one keeps the person's", () => {
        const next = valuesAfterConflict(VIEW, stored, FIELDS, { name: "renamed_variants", owner: "analyst-3" });

        expect(next["name"]).toBe("renamed_variants"); // touched: kept
        expect(next["owner"]).toBe("ops-9"); // untouched: the stored answer
    });

    it("a field typed back to the stored value counts as untouched", () => {
        // "Untouched" is a value comparison (the signal form has no dirty
        // flag): a field equal to its old seed re-seeds — to the same text.
        const next = valuesAfterConflict(VIEW, stored, FIELDS, { name: "genomic_variants", owner: "typed" });

        expect(next["name"]).toBe("stored_variants"); // re-seeded (it was untouched)
        expect(next["owner"]).toBe("typed");
    });

    it("a drafted value survives an oldView-less re-seed; a blank slot stays untouched", () => {
        const next = valuesAfterConflict(null, stored, FIELDS, { name: "drafted", owner: "" });

        // With no old view the seed is empty: typed text differs from it and
        // is kept; a blank slot equals the empty seed and counts untouched,
        // so the stored value answers (VDE-07).
        expect(next["name"]).toBe("drafted");
        expect(next["owner"]).toBe("ops-9");
    });
});

describe("picksAfterConflict (VDE-07, DD-610)", () => {
    const storedWithEnds: EntityView = {
        ...VIEW,
        sections: [
            { attribute: "inputToProcesses", entities: [{ guid: "p2", name: "load_orders", status: "ACTIVE" }] },
        ],
    };

    it("a picker nobody changed re-seeds from the stored ends", () => {
        const next = picksAfterConflict(
            VIEW,
            storedWithEnds,
            PICKER,
            new Map([["inputToProcesses", [{ guid: "p1", typeName: "Process" }]]]),
        );

        // The stored end carries no typeName of its own — the seed answers
        // what the view holds (entityFromView maps name → displayText).
        expect(next.get("inputToProcesses")).toEqual([{ guid: "p2", typeName: "", displayText: "load_orders" }]);
    });

    it("a picker the person changed keeps their chips", () => {
        const next = picksAfterConflict(
            VIEW,
            storedWithEnds,
            PICKER,
            new Map([["inputToProcesses", [{ guid: "p3", typeName: "Process" }]]]),
        );

        expect(next.get("inputToProcesses")).toEqual([{ guid: "p3", typeName: "Process" }]);
    });
});

describe("tagsAfterConflict (VDE-03, VDE-07)", () => {
    it("the stored tags answer, minus what the person removed; additions stay", () => {
        const stored: EntityView = { ...VIEW, classificationNames: ["PII", "APPROVED"] };

        // The person dropped PII and added CONFIDENTIAL before the conflict.
        const kept = tagsAfterConflict(VIEW, stored, ["CONFIDENTIAL"]);

        expect(kept).toEqual(["APPROVED", "CONFIDENTIAL"]);
    });

    it("nothing changed means the stored names answer whole", () => {
        const stored: EntityView = { ...VIEW, classificationNames: ["PII", "APPROVED"] };

        expect(tagsAfterConflict(VIEW, stored, ["PII"])).toEqual(["PII", "APPROVED"]);
    });
});
