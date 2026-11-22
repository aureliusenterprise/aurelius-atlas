/**
 * The change list of an audit row (HST-10, DD-821): the parse of the stored
 * `details` body, the differ over two stored states, and the walk of a loaded
 * trail. The bodies are the text the ported listener writes
 * (`entity_audit_listener.audit_detail`, AUD-03), including the two shapes its
 * size cap produces (AUD-04).
 */
import type { EntityAuditEventV2 } from "aurelius-atlas-data-access";

import {
    auditRowKey,
    auditTrailChanges,
    diffAuditStates,
    emptyAuditState,
    isCreateAction,
    isStateAction,
    parseAuditState,
} from "./audit-details";

/** An event whose `details` carry the JSON of a stored entity (AUD-03). */
function stateEvent(action: EntityAuditEventV2["action"], entity: unknown, key = "k"): EntityAuditEventV2 {
    return { action, eventKey: key, details: `${prefixOf(action)}${JSON.stringify(entity)}` };
}

/** The listener's own prefix for an action (`_PREFIXES`, AUD-03). */
const PREFIXES: Record<string, string> = {
    ENTITY_CREATE: "Created: ",
    ENTITY_UPDATE: "Updated: ",
    ENTITY_IMPORT_CREATE: "Created by import: ",
    ENTITY_IMPORT_UPDATE: "Updated by import: ",
};

function prefixOf(action: EntityAuditEventV2["action"]): string {
    return PREFIXES[String(action)];
}

/** The end of a stored `relationshipAttributes` list, as the writer leaves it. */
function end(guid: string, displayText?: string, relationshipStatus?: "ACTIVE" | "DELETED"): unknown {
    return {
        guid,
        ...(displayText === undefined ? {} : { displayText }),
        ...(relationshipStatus === undefined ? {} : { relationshipStatus }),
    };
}

describe("audit-details (HST-10, DD-821)", () => {
    it("offers a change list for the four stored-state actions only (HST-10)", () => {
        expect(isStateAction("ENTITY_CREATE")).toBe(true);
        expect(isStateAction("ENTITY_UPDATE")).toBe(true);
        expect(isStateAction("ENTITY_IMPORT_CREATE")).toBe(true);
        expect(isStateAction("ENTITY_IMPORT_UPDATE")).toBe(true);
        for (const action of [
            "ENTITY_DELETE",
            "CLASSIFICATION_ADD",
            "TERM_ADD",
            "BUSINESS_ATTRIBUTE_UPDATE",
            null,
            undefined,
        ]) {
            expect(isStateAction(action)).toBe(false);
        }
    });

    it("names the two create actions as the ones compared with nothing (HST-10)", () => {
        expect(isCreateAction("ENTITY_CREATE")).toBe(true);
        expect(isCreateAction("ENTITY_IMPORT_CREATE")).toBe(true);
        expect(isCreateAction("ENTITY_UPDATE")).toBe(false);
        expect(isCreateAction("ENTITY_IMPORT_UPDATE")).toBe(false);
    });

    it("keys a row's change list by its eventKey (HST-10, AUD-05)", () => {
        expect(auditRowKey({ eventKey: "g:1:0:1" })).toBe("g:1:0:1");
        expect(auditRowKey({ eventKey: null })).toBe("");
    });

    it("reads the stored state of each action past its own prefix (HST-10, AUD-03)", () => {
        for (const action of [
            "ENTITY_CREATE",
            "ENTITY_UPDATE",
            "ENTITY_IMPORT_CREATE",
            "ENTITY_IMPORT_UPDATE",
        ] as const) {
            const parsed = parseAuditState(
                stateEvent(action, { typeName: "t", attributes: { name: "n" }, relationshipAttributes: {} }),
            );

            expect(parsed.status).toBe("full");
            if (parsed.status === "full") {
                expect(parsed.state.attributes).toEqual({ name: "n" });
                expect(parsed.state.relationships).toEqual({});
            }
        }
    });

    it("answers a cut-down body as partial (HST-10, AUD-04)", () => {
        // The writer's second shape clears attributes and relationship
        // attributes, and it drops nulls, so both keys are simply gone.
        const cut = stateEvent("ENTITY_UPDATE", { typeName: "t", guid: "g" });

        expect(parseAuditState(cut)).toEqual({ status: "partial" });
    });

    it("answers the shallow header the size cap can leave as partial (AUD-04)", () => {
        const shallow = stateEvent("ENTITY_UPDATE", { guid: "g", typeName: "t", version: 2 });

        expect(parseAuditState(shallow)).toEqual({ status: "partial" });
    });

    it("answers a body it cannot use with no claim (HST-10)", () => {
        expect(parseAuditState({ action: "ENTITY_UPDATE", details: null })).toEqual({ status: "none" });
        expect(parseAuditState({ action: "ENTITY_UPDATE", details: "Updated: " })).toEqual({ status: "none" });
        expect(parseAuditState({ action: "ENTITY_UPDATE", details: "Updated: {not json" })).toEqual({ status: "none" });
        expect(parseAuditState({ action: "ENTITY_UPDATE", details: "Updated: [1,2]" })).toEqual({ status: "none" });
        expect(parseAuditState({ action: "ENTITY_DELETE", details: "Deleted entity" })).toEqual({ status: "none" });
    });

    it("counts no relationship of a full body that holds none (HST-10)", () => {
        const full = stateEvent("ENTITY_UPDATE", { attributes: { name: "n" } });

        expect(parseAuditState(full)).toEqual({
            status: "full",
            state: { attributes: { name: "n" }, relationships: {} },
        });
    });

    it("reads a single end and a list of ends alike, and skips a DELETED edge (EDT-15)", () => {
        const single = stateEvent("ENTITY_UPDATE", {
            attributes: {},
            relationshipAttributes: { input: end("a", "A") },
        });
        const many = stateEvent("ENTITY_UPDATE", {
            attributes: {},
            relationshipAttributes: { input: [end("a", "A"), end("b", "B", "DELETED")] },
        });

        if (parseAuditState(single).status === "full") {
            expect(parseAuditState(single)).toEqual({
                status: "full",
                state: { attributes: {}, relationships: { input: [{ guid: "a", display: "A" }] } },
            });
        }
        if (parseAuditState(many).status === "full") {
            expect(parseAuditState(many)).toEqual({
                status: "full",
                state: { attributes: {}, relationships: { input: [{ guid: "a", display: "A" }] } },
            });
        }
    });

    it("falls back to an end's GUID when it carries no display text (HST-10)", () => {
        const parsed = parseAuditState(
            stateEvent("ENTITY_UPDATE", { attributes: {}, relationshipAttributes: { input: [end("a")] } }),
        );

        expect(parsed).toEqual({
            status: "full",
            state: { attributes: {}, relationships: { input: [{ guid: "a", display: "a" }] } },
        });
    });

    it("diffs attributes as changed, added and removed, with the values each shows (HST-10)", () => {
        const { attributes } = diffAuditStates(
            { attributes: { name: "old", kept: 1, gone: true }, relationships: {} },
            { attributes: { name: "new", kept: 1, fresh: "f" }, relationships: {} },
        );

        expect(attributes).toEqual([
            { kind: "changed", name: "name", from: "old", to: "new" },
            { kind: "removed", name: "gone", from: "true" },
            { kind: "added", name: "fresh", to: "f" },
        ]);
    });

    it("formats every stored value kind for the change list (HST-10)", () => {
        const { attributes } = diffAuditStates(
            { attributes: { list: [1, 2], nothing: null }, relationships: {} },
            { attributes: { list: [1, 3], nothing: 7 }, relationships: {} },
        );

        expect(attributes).toEqual([
            { kind: "changed", name: "list", from: "[1,2]", to: "[1,3]" },
            { kind: "changed", name: "nothing", from: "", to: "7" },
        ]);
    });

    it("treats an equal array or object as no change (HST-10)", () => {
        const { attributes } = diffAuditStates(
            { attributes: { list: [1, 2], obj: { a: 1 } }, relationships: {} },
            { attributes: { list: [1, 2], obj: { a: 1 } }, relationships: {} },
        );

        expect(attributes).toEqual([]);
    });

    it("diffs relationship ends by GUID, so a renamed end is no change (HST-10)", () => {
        const from = { attributes: {}, relationships: { input: [{ guid: "a", display: "Old name" }] } };
        const to = { attributes: {}, relationships: { input: [{ guid: "a", display: "New name" }] } };

        expect(diffAuditStates(from, to).relationships).toEqual([]);
    });

    it("lists an added and a removed end under its attribute name (HST-10)", () => {
        const { relationships } = diffAuditStates(
            { attributes: {}, relationships: { input: [{ guid: "a", display: "A" }] } },
            { attributes: {}, relationships: { input: [{ guid: "b", display: "B" }] } },
        );

        expect(relationships).toEqual([
            { kind: "added", attribute: "input", entity: "B" },
            { kind: "removed", attribute: "input", entity: "A" },
        ]);
    });

    it("answers two identical states with nothing changed (HST-10)", () => {
        const state = { attributes: { name: "n" }, relationships: { input: [{ guid: "a", display: "A" }] } };

        expect(diffAuditStates(state, state)).toEqual({ kind: "diff", attributes: [], relationships: [] });
    });

    it("answers a create against the empty state: everything it holds is added (HST-10)", () => {
        const created = { attributes: { name: "n" }, relationships: { input: [{ guid: "a", display: "A" }] } };

        expect(diffAuditStates(emptyAuditState(), created)).toEqual({
            kind: "diff",
            attributes: [{ kind: "added", name: "name", to: "n" }],
            relationships: [{ kind: "added", attribute: "input", entity: "A" }],
        });
    });

    it("pairs each row of a trail with the nearest older stored state (HST-10)", () => {
        const trail = [
            stateEvent("ENTITY_UPDATE", { attributes: { name: "third" } }, "3"),
            stateEvent("ENTITY_UPDATE", { attributes: { name: "second" } }, "2"),
            stateEvent("ENTITY_CREATE", { attributes: { name: "first" } }, "1"),
        ];

        const changes = auditTrailChanges(trail);

        expect(changes.get("3")).toEqual({
            kind: "diff",
            attributes: [{ kind: "changed", name: "name", from: "second", to: "third" }],
            relationships: [],
        });
        expect(changes.get("2")).toEqual({
            kind: "diff",
            attributes: [{ kind: "changed", name: "name", from: "first", to: "second" }],
            relationships: [],
        });
        expect(changes.get("1")).toEqual({
            kind: "diff",
            attributes: [{ kind: "added", name: "name", to: "first" }],
            relationships: [],
        });
    });

    it("answers a create as added even when an older state is on screen (HST-10)", () => {
        // A create has no state to pair with, whatever sits below it: the
        // entity did not exist before it (DD-821).
        const trail = [
            stateEvent("ENTITY_CREATE", { attributes: { name: "n" } }, "2"),
            stateEvent("ENTITY_UPDATE", { attributes: { name: "m" } }, "1"),
        ];

        expect(auditTrailChanges(trail).get("2")).toEqual({
            kind: "diff",
            attributes: [{ kind: "added", name: "name", to: "n" }],
            relationships: [],
        });
    });

    it("answers the oldest row of a page with the earlier state not loaded (HST-10)", () => {
        const trail = [
            stateEvent("ENTITY_UPDATE", { attributes: { name: "b" } }, "2"),
            stateEvent("ENTITY_UPDATE", { attributes: { name: "a" } }, "1"),
        ];

        expect(auditTrailChanges(trail).get("1")).toEqual({ kind: "unloaded" });
    });

    it("answers the row once a next page brings the earlier state (HST-08)", () => {
        const firstPage = [
            stateEvent("ENTITY_UPDATE", { attributes: { name: "b" } }, "2"),
            stateEvent("ENTITY_UPDATE", { attributes: { name: "a" } }, "1"),
        ];
        expect(auditTrailChanges(firstPage).get("1")).toEqual({ kind: "unloaded" });

        const longer = [...firstPage, stateEvent("ENTITY_CREATE", { attributes: { name: "start" } }, "0")];
        expect(auditTrailChanges(longer).get("1")).toEqual({
            kind: "diff",
            attributes: [{ kind: "changed", name: "name", from: "start", to: "a" }],
            relationships: [],
        });
    });

    it("keeps a cut-down row out of the pairing and says its details are not recorded (HST-10, AUD-04)", () => {
        const cut = stateEvent("ENTITY_UPDATE", { typeName: "t" }, "2");
        const trail = [
            stateEvent("ENTITY_UPDATE", { attributes: { name: "c" } }, "3"),
            cut,
            stateEvent("ENTITY_UPDATE", { attributes: { name: "a" } }, "1"),
        ];

        const changes = auditTrailChanges(trail);

        expect(changes.get("2")).toEqual({ kind: "partial" });
        // The newest row pairs with the nearest older row that holds a state,
        // which is the oldest one on screen — the cut-down row is skipped.
        expect(changes.get("3")).toEqual({
            kind: "diff",
            attributes: [{ kind: "changed", name: "name", from: "a", to: "c" }],
            relationships: [],
        });
    });

    it("pairs across a row that holds no state at all (HST-10)", () => {
        const trail = [
            stateEvent("ENTITY_UPDATE", { attributes: { name: "c" } }, "3"),
            { action: "CLASSIFICATION_ADD", eventKey: "x", details: "Added classification: {}" } as EntityAuditEventV2,
            stateEvent("ENTITY_UPDATE", { attributes: { name: "a" } }, "1"),
        ];

        expect(auditTrailChanges(trail).get("3")).toEqual({
            kind: "diff",
            attributes: [{ kind: "changed", name: "name", from: "a", to: "c" }],
            relationships: [],
        });
        expect(auditTrailChanges(trail).has("x")).toBe(false);
    });

    it("lists a state row whose write changed nothing as nothing changed (HST-10)", () => {
        const trail = [
            stateEvent("ENTITY_UPDATE", { attributes: { name: "a" } }, "2"),
            stateEvent("ENTITY_UPDATE", { attributes: { name: "a" } }, "1"),
        ];

        expect(auditTrailChanges(trail).get("2")).toEqual({ kind: "diff", attributes: [], relationships: [] });
    });

    it("ignores a trail with no state rows at all (HST-10)", () => {
        const changes = auditTrailChanges([{ action: "TERM_ADD", eventKey: "t", details: "Added term: {}" }]);

        expect(changes.size).toBe(0);
    });
});
