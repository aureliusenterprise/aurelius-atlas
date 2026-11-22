/**
 * The change list of an audit row (HST-10, DD-821).
 *
 * The audit wire stores the whole entity in the `details` string of the four
 * entity-state actions (`audit_detail`, AUD-03): the action's prefix and the
 * entity's JSON. The newest-first order (HST-03) means the event before a row
 * in the trail is the state its write replaced, so a row's change list is the
 * difference between the two stored bodies — no new endpoint, and the store
 * stays exactly as Atlas defines it (AUD-06).
 *
 * Two shapes stay visible rather than guessed (DD-821): a body the server cut
 * down for size lost its attributes (AUD-04) and answers `partial`, and an
 * event older than the loaded window has no comparison pair on screen and
 * answers `unloaded` until a next page brings one (HST-08). A create compares
 * against the empty state, because the entity did not exist before it.
 *
 * Relationship ends ride `relationshipAttributes` (EDT-15's field), keyed by
 * relationship attribute name, and match across two states on the end entity's
 * GUID. A DELETED edge is never counted as held, as the editor's own seed rule
 * never shows one.
 */

import type { EntityAuditEventV2 } from "aurelius-atlas-data-access";

import { DESCRIPTION_KEYS } from "./form-fields";

/** The attribute keys whose text the change list words (HST-15). */
const PROSE_KEYS: readonly string[] = DESCRIPTION_KEYS;

/** The actions whose event carries the entity's stored state (AUD-03). */
const STATE_ACTIONS: ReadonlySet<string> = new Set([
    "ENTITY_CREATE",
    "ENTITY_UPDATE",
    "ENTITY_IMPORT_CREATE",
    "ENTITY_IMPORT_UPDATE",
]);

/**
 * One relationship end a stored state holds, as far as it names it. The guid
 * is what matches two states (HST-10), and the type is what names the end's
 * icon on the change list's crumb (HST-12, DET-26).
 */
type AuditEnd = { guid: string; display: string; typeName?: string };

/** The part of a stored entity a change list reads. */
export type AuditState = {
    /** The attribute map, or nothing when the body never carried one. */
    attributes: Record<string, unknown>;
    /** The held relationship ends, keyed by relationship attribute name. */
    relationships: Record<string, readonly AuditEnd[]>;
};

/** What reading one row's stored body gave (HST-10). */
export type AuditStateParse =
    /** No usable body: no toggle, and no claim (HST-10). */
    | { status: "none" }
    /** The body lost its attributes to the size cap (AUD-04). */
    | { status: "partial" }
    /** The full stored state. */
    | { status: "full"; state: AuditState };

/** What one row's change list is (HST-10). */
export type AuditChanges =
    /** The row carries no state to show. */
    | { kind: "none" }
    /** The row's body was cut down (AUD-04). */
    | { kind: "partial" }
    /** No older row on screen holds the state this write replaced (HST-08). */
    | { kind: "unloaded" }
    /** The row's own state, compared with the state before it. */
    | AuditStateDiff;

/** Two stored states compared with each other (HST-10). */
export type AuditStateDiff = {
    kind: "diff";
    attributes: readonly AuditAttributeChange[];
    relationships: readonly AuditRelationshipChange[];
    /** The entity descriptions this write worded differently (HST-15), which
     * are not in {@link AuditStateDiff.attributes}. */
    descriptions: readonly AuditProseChange[];
};

/** One entity description a change list reworded (HST-15). */
export type AuditProseChange = {
    /** The attribute's name: `description` (EDT-20 as amended by 18.8). */
    name: string;
    /** The text before, empty when the write filled an empty description. */
    from: string;
    /** The text after, empty when the write cleared it. */
    to: string;
};

/** One attribute of a change list (HST-10). */
export type AuditAttributeChange = {
    kind: "added" | "changed" | "removed";
    /** The attribute's name, as the type defines it. */
    name: string;
    /** The value before, shown for a changed attribute. */
    from?: string;
    /** The value after, absent for a removed attribute. */
    to?: string;
    /** The stored value before the write, on the changed rows only (HST-11):
     * what a restore sends back, where {@link AuditAttributeChange.from} is
     * the text shown for it. */
    storedFrom?: unknown;
};

/** One relationship end a change list added or removed (HST-10). */
export type AuditRelationshipChange = {
    kind: "added" | "removed";
    /** The relationship attribute name the end belongs to. */
    attribute: string;
    /** The end's display text, or its GUID when it carries none. */
    entity: string;
    /** The end entity's GUID (HST-12): what the change list's crumb links to. */
    guid: string;
    /** The end entity's type, when the stored end names it (HST-12): what
     * gives the crumb its icon (DET-26). */
    typeName?: string;
};

/** Whether a row offers a change list at all (HST-10). */
export function isStateAction(action: string | null | undefined): boolean {
    return action !== undefined && action !== null && STATE_ACTIONS.has(action);
}

/** Whether a row is a create — the one state action compared with nothing. */
export function isCreateAction(action: string | null | undefined): boolean {
    return action === "ENTITY_CREATE" || action === "ENTITY_IMPORT_CREATE";
}

/** The key a row's change list is opened by (HST-10): the row's `eventKey`
 * (AUD-05), the same value the pane tracks its rows on. */
export function auditRowKey(event: EntityAuditEventV2): string {
    return event.eventKey ?? "";
}

/** The state an event that did not exist holds: a create compares against it. */
export function emptyAuditState(): AuditState {
    return { attributes: {}, relationships: {} };
}

/**
 * Read the stored state out of an event's `details` (HST-10, AUD-03): the
 * prefix and the entity's JSON the listener wrote. The answer is `partial`
 * when the body lost its attributes to the size cap (AUD-04) and `none` when
 * there is no body to read at all.
 * @param event the audit row
 */
export function parseAuditState(event: EntityAuditEventV2): AuditStateParse {
    if (!isStateAction(event.action)) {
        return { status: "none" };
    }

    const body = event.details?.slice(event.details.indexOf("{"));
    if (!body || body[0] !== "{") {
        return { status: "none" };
    }

    let entity: unknown;
    try {
        entity = JSON.parse(body);
    } catch {
        return { status: "none" };
    }

    if (entity === null || typeof entity !== "object") {
        return { status: "none" };
    }

    const fields = entity as Record<string, unknown>;
    // The writer drops nulls (AUD-03's `codec.dumps`), so the two fields the
    // size cap clears (AUD-04) are simply absent from a cut-down body. A full
    // body always carries `attributes`; `relationshipAttributes` can be absent
    // from a whole body that holds no relationships, so only the attribute
    // field tells the two shapes apart.
    if (!("attributes" in fields)) {
        return { status: "partial" };
    }

    return {
        status: "full",
        state: {
            attributes: asRecord(fields["attributes"]),
            relationships: asRelationships(fields["relationshipAttributes"]),
        },
    };
}

/**
 * Compare two stored states (HST-10): each attribute that differs is changed
 * with both values, each attribute only the newer state holds is added, each
 * one only the older holds is removed, and each relationship end is added or
 * removed by its GUID. Names come in the order the states list them.
 *
 * An attribute whose value is an entity reference — one `AtlasObjectId` or a
 * list of them, the shape the metamodel's entity-typed attributes hold (a
 * collection's `systems`, a process's `inputs`) — is a relationship, not a
 * value: it joins the relationship section under its own name, so the
 * attribute table never prints a reference as JSON (HST-12, DD-823). An
 * attribute that holds nothing on the side that gained it claims no line, so a
 * create stays silent about the optional fields the store keeps blank (HST-13,
 * DD-824).
 * @param from the state before the write
 * @param to the state the write stored
 */
export function diffAuditStates(from: AuditState, to: AuditState): AuditStateDiff {
    // The key's kind is decided on both states together: an attribute the
    // older state holds empty and the newer one fills with a reference is one
    // relationship that gained an end, not a value that changed.
    const attributeNames = [...new Set([...Object.keys(from.attributes), ...Object.keys(to.attributes)])];
    const referenceNames = new Set(
        attributeNames.filter((name) => isEntityValue(from.attributes[name]) || isEntityValue(to.attributes[name])),
    );

    const attributes: AuditAttributeChange[] = [];
    const descriptions: AuditProseChange[] = [];
    for (const name of attributeNames) {
        if (referenceNames.has(name)) {
            continue;
        }
        const before = from.attributes[name];
        const after = to.attributes[name];
        // The prose attribute leaves the tables for its own section (HST-15).
        const prose = PROSE_KEYS.includes(name);
        if (!(name in from.attributes)) {
            // The attribute appeared, so the write set it — unless what it
            // holds is nothing at all, which sets nothing (HST-13).
            if (isNothingValue(after)) {
                continue;
            }
            if (prose) {
                descriptions.push({ name, from: "", to: formatValue(after) ?? "" });
            } else {
                attributes.push({ kind: "added", name, to: formatValue(after) });
            }
        } else if (!(name in to.attributes)) {
            if (isNothingValue(before)) {
                continue;
            }
            if (prose) {
                descriptions.push({ name, from: formatValue(before) ?? "", to: "" });
            } else {
                attributes.push({ kind: "removed", name, from: formatValue(before) });
            }
        } else if (!sameValue(before, after)) {
            if (prose) {
                descriptions.push({
                    name,
                    from: formatValue(before) ?? "",
                    to: formatValue(after) ?? "",
                });
            } else {
                attributes.push({
                    kind: "changed",
                    name,
                    from: formatValue(before),
                    to: formatValue(after),
                    storedFrom: before,
                });
            }
        }
    }

    const relationships: AuditRelationshipChange[] = [];
    const heldNames = [
        ...new Set([...Object.keys(from.relationships), ...Object.keys(to.relationships)]),
        ...referenceNames,
    ];
    for (const attribute of heldNames) {
        const before = new Map(
            (from.relationships[attribute] ?? endsOf(from.attributes[attribute])).map((end) => [end.guid, end]),
        );
        const after = new Map(
            (to.relationships[attribute] ?? endsOf(to.attributes[attribute])).map((end) => [end.guid, end]),
        );
        for (const [guid, end] of after) {
            if (!before.has(guid)) {
                relationships.push({ kind: "added", attribute, entity: end.display, guid, typeName: end.typeName });
            }
        }
        for (const [guid, end] of before) {
            if (!after.has(guid)) {
                relationships.push({ kind: "removed", attribute, entity: end.display, guid, typeName: end.typeName });
            }
        }
    }

    return { kind: "diff", attributes, relationships, descriptions };
}

/**
 * The change list of every state row of a trail (HST-10, DD-821): keyed by the
 * row's `eventKey`, so a caller reads a row's answer by the key it already
 * tracks rows on. The newest-first list (HST-03) is walked from its oldest row
 * inwards, because the state a write replaced is the next full state older
 * than it. A create's "before" is the empty state, because the entity did not
 * exist before it; any other row with no older state in the list answers
 * "not loaded" and claims nothing, and a next page that brings that state
 * answers it on the next read (HST-08). A row whose body the server cut down
 * (AUD-04) holds no state of its own and answers "not recorded" — but the
 * older state below it stays usable, so a newer row pairs with the nearest
 * older row that does hold one.
 * @param events the loaded trail, newest first as the server answered it
 */
export function auditTrailChanges(events: readonly EntityAuditEventV2[]): ReadonlyMap<string, AuditChanges> {
    const changes = new Map<string, AuditChanges>();
    let older: AuditState | null = null;
    for (let index = events.length - 1; index >= 0; index -= 1) {
        const event = events[index];
        if (!isStateAction(event.action)) {
            continue;
        }
        const parsed = parseAuditState(event);
        if (parsed.status === "none") {
            continue;
        }
        if (parsed.status === "partial") {
            changes.set(auditRowKey(event), { kind: "partial" });
            continue;
        }
        const from = isCreateAction(event.action) ? emptyAuditState() : older;
        changes.set(auditRowKey(event), from === null ? { kind: "unloaded" } : diffAuditStates(from, parsed.state));
        older = parsed.state;
    }

    return changes;
}

/**
 * Whether a changed row's stored old value can be written back (HST-11, EWR-15):
 * the single-attribute door takes a primitive or a reference, and a change
 * list's own value shape holds no reference, so only text, number and boolean
 * values answer yes. A list, an object and a missing value answer no.
 * @param value the stored value a changed row carries
 */
export function isRestorableValue(value: unknown): value is string | number | boolean {
    return typeof value === "string" || typeof value === "number" || typeof value === "boolean";
}

/** What one change-list row restores (HST-11): the attribute and the value. */
export type AuditRestore = { name: string; value: string | number | boolean };

/**
 * The attribute a row restores, or null when the row restores nothing (HST-11):
 * only a changed row whose stored old value the single-attribute door can take
 * names one, so an added, removed or multi-valued row carries no restore.
 * @param change one attribute line of a change list
 */
export function restoreOf(change: AuditAttributeChange): AuditRestore | null {
    return change.kind === "changed" && isRestorableValue(change.storedFrom)
        ? { name: change.name, value: change.storedFrom }
        : null;
}

/** The stored attribute map, or nothing when the body held none. */
function asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === "object" && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : {};
}

/**
 * The held ends of a stored `relationshipAttributes` map, keyed by attribute
 * name. A DELETED edge is skipped, as the editor's seed rule skips it (EDT-15),
 * and an end without a GUID is skipped because nothing can match it.
 */
function asRelationships(value: unknown): Record<string, readonly AuditEnd[]> {
    const stored = asRecord(value);
    const held: Record<string, AuditEnd[]> = {};
    for (const attribute of Object.keys(stored)) {
        const rows = Array.isArray(stored[attribute]) ? stored[attribute] : [stored[attribute]];
        const ends: AuditEnd[] = [];
        for (const row of rows) {
            if (row === null || typeof row !== "object") {
                continue;
            }
            const end = row as Record<string, unknown>;
            const guid = end["guid"];
            if (
                typeof guid !== "string" ||
                (end["relationshipStatus"] !== undefined && end["relationshipStatus"] !== "ACTIVE")
            ) {
                continue;
            }
            ends.push({ guid, display: textOf(end["displayText"]) ?? guid, typeName: textOf(end["typeName"]) });
        }
        if (ends.length > 0) {
            held[attribute] = ends;
        }
    }

    return held;
}

/**
 * Whether a stored attribute value names an entity: one `AtlasObjectId` (the
 * listener writes the type and the GUID of the entity it points at) or a list
 * of them. An empty list carries no evidence and stays a plain value — the
 * differ decides on both states together, so filling it reads as adding an
 * end.
 */
function isEntityValue(value: unknown): boolean {
    if (Array.isArray(value)) {
        return value.length > 0 && value.every((row) => isEndObject(row));
    }

    return isEndObject(value);
}

/**
 * Whether a stored attribute value holds nothing at all (HST-13, DD-824): the
 * blank shape the store keeps for an attribute the entity leaves unset — no
 * value, empty text, an empty list or an empty struct. A number, `false`, a
 * blank-looking space and a list with one entry are values, not nothing.
 * @param value the stored value of one attribute
 */
function isNothingValue(value: unknown): boolean {
    if (value === null || value === undefined || value === "") {
        return true;
    }
    if (Array.isArray(value)) {
        return value.length === 0;
    }
    if (typeof value === "object") {
        return Object.keys(value).length === 0;
    }

    return false;
}

/** Whether a value is the wire shape of a reference to one entity. */
function isEndObject(value: unknown): boolean {
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
        return false;
    }
    const fields = value as Record<string, unknown>;

    return typeof fields["guid"] === "string" && typeof fields["typeName"] === "string";
}

/**
 * The ends a stored attribute value names (HST-12): its references, each read
 * as one end. Anything that is not a reference names no end, so a plain value
 * answers the empty list.
 */
function endsOf(value: unknown): readonly AuditEnd[] {
    if (!isEntityValue(value)) {
        return [];
    }

    return (Array.isArray(value) ? value : [value]).map((row) => {
        const end = row as Record<string, unknown>;
        const guid = end["guid"] as string;
        const unique = end["uniqueAttributes"];
        const qualifiedName =
            unique !== null && typeof unique === "object"
                ? (unique as Record<string, unknown>)["qualifiedName"]
                : undefined;
        return {
            guid,
            display: textOf(end["displayText"]) ?? textOf(qualifiedName) ?? guid,
            typeName: textOf(end["typeName"]),
        };
    });
}

/** The value's display text: a string as it is, anything else its JSON. */
function formatValue(value: unknown): string {
    if (typeof value === "string") {
        return value;
    }
    if (value === null || value === undefined) {
        return "";
    }
    if (typeof value === "number" || typeof value === "boolean") {
        return String(value);
    }

    return JSON.stringify(value);
}

/** Whether two stored values are the same value. */
function sameValue(a: unknown, b: unknown): boolean {
    if (a === b) {
        return true;
    }

    return JSON.stringify(a) === JSON.stringify(b);
}

/** A field's text, or nothing when it is not a usable string. */
function textOf(value: unknown): string | undefined {
    return typeof value === "string" && value !== "" ? value : undefined;
}
