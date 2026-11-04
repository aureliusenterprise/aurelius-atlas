import {
    AtlasAttributeDef,
    AtlasEntity,
    AtlasEntityDef,
    AtlasEntityHeader,
    AtlasEnumDef,
    AtlasRelatedEntity,
    AtlasRelationshipAttributeDef,
} from "aurelius-atlas-data-access";

/** The input one editor field renders. */
export type EditorFieldKind = "text" | "textarea" | "number" | "boolean" | "date" | "enum" | "multi";

/** One form control: its name, the input to render, and its label/state. */
export type EditorField = {
    /** The entity attribute this control writes. */
    readonly name: string;
    readonly kind: EditorFieldKind;
    /** The label text (the catalogue string, `displayName`, or the name). */
    readonly label: string;
    readonly required: boolean;
    /** A unique attribute other than `name` — it locates the entity (EDT-03). */
    readonly disabled: boolean;
    /** The enum's values, by ordinal — only for `kind === "enum"`. */
    readonly enumValues?: readonly string[];
};

/**
 * The localized strings for the attributes the catalogue names (EDT-11:
 * `search.components.editor.attribute.name`, `.definition`). The component
 * builds these with `$localize` and passes them in — the helper stays pure.
 */
export type EditorLabels = Partial<Record<"name" | "definition" | "description", string>>;

/** The two attribute keys the details box shows as the description (DET-10/DD-320). */
const DESCRIPTION_KEYS = ["definition", "description"] as const;

/** The primitive numeric `typeName`s (Atlas's built-in numeric types). */
const NUMERIC_TYPES = new Set(["int", "long", "float", "double", "byte", "short", "bigint"]);

/** The name that never renders and the header field that is never an attribute. */
const DROPPED_ATTRIBUTES = new Set(["qualifiedName", "guid"]);

/**
 * The field kinds for the shipped store's `typeName` values, so a reviewer can
 * see the coverage (EDT-03): string/`boolean`/`date`/enum → their inputs;
 * the numeric set → number; `array<string>` with LIST/SET cardinality → multi;
 * every other type (struct, `map<…>`, `array<struct>`, `array<entity>`) and
 * every relationship attribute renders nothing and passes a save untouched.
 */
function kindOf(def: AtlasAttributeDef, enumNames: ReadonlySet<string>): EditorFieldKind | null {
    const typeName = def.typeName ?? "";

    if (enumNames.has(typeName)) {
        return "enum";
    }
    if (def.cardinality === "LIST" || def.cardinality === "SET") {
        // Only a list of plain strings is editable here; a list of entity or
        // struct references (Process inputs, replicatedFrom) is 7.7c's.
        return typeName === "array<string>" ? "multi" : null;
    }
    if (typeName === "string") {
        return DESCRIPTION_KEYS.includes(def.name as (typeof DESCRIPTION_KEYS)[number]) ? "textarea" : "text";
    }
    if (typeName === "boolean") {
        return "boolean";
    }
    if (typeName === "date") {
        return "date";
    }
    if (NUMERIC_TYPES.has(typeName)) {
        return "number";
    }
    return null;
}

/**
 * The definition and its supertype chain, first-wins by attribute name (the
 * shipped defs carry only their own attributes, so `DataSet`'s fields live on
 * `Asset`/`Referenceable` — the walk is required, EDT-03).
 * @param def the entity definition to walk
 * @param defsByName every entity definition by name (for the supertype links)
 * @returns the merged attribute definitions, definition's own first
 */
function collectAttributeDefs(
    def: AtlasEntityDef,
    defsByName: ReadonlyMap<string, AtlasEntityDef>,
): AtlasAttributeDef[] {
    const merged: AtlasAttributeDef[] = [];
    const seenNames = new Set<string>();
    const seenDefs = new Set<string>();
    const queue: AtlasEntityDef[] = [def];

    while (queue.length > 0) {
        const current = queue.shift() as AtlasEntityDef;
        if (current.name && seenDefs.has(current.name)) {
            continue;
        }
        if (current.name) {
            seenDefs.add(current.name);
        }
        for (const attribute of current.attributeDefs ?? []) {
            if (attribute.name && !seenNames.has(attribute.name)) {
                seenNames.add(attribute.name);
                merged.push(attribute);
            }
        }
        for (const superName of current.superTypes ?? []) {
            const superDef = defsByName.get(superName);
            if (superDef) {
                queue.push(superDef);
            }
        }
    }

    return merged;
}

/** The catalogue string, else `displayName`, else the attribute name (EDT-03). */
function labelOf(def: AtlasAttributeDef, labels: EditorLabels): string {
    return labels[def.name as keyof EditorLabels] ?? def.displayName ?? def.name ?? "";
}

/**
 * The editor's form fields for an entity definition, ordered `name`, the
 * description key, then the rest by name (EDT-03).
 * @param entityDef the entity's own definition
 * @param defsByName every entity definition by name (the supertype walk)
 * @param enumsByName every enum definition by name (the enum values + the
 *   `typeName` → enum lookup)
 * @param labels the localized strings for the catalogue-named attributes
 * @returns the fields to render
 */
export function buildFields(
    entityDef: AtlasEntityDef,
    defsByName: ReadonlyMap<string, AtlasEntityDef>,
    enumsByName: ReadonlyMap<string, AtlasEnumDef>,
    labels: EditorLabels = {},
): EditorField[] {
    const enumNames = new Set(enumsByName.keys());
    const fields: EditorField[] = [];

    for (const def of collectAttributeDefs(entityDef, defsByName)) {
        if (!def.name || DROPPED_ATTRIBUTES.has(def.name)) {
            continue;
        }
        const kind = kindOf(def, enumNames);
        if (!kind) {
            continue;
        }
        fields.push({
            name: def.name,
            kind,
            label: labelOf(def, labels),
            required: def.name === "name" || def.isOptional === false,
            disabled: Boolean(def.isUnique) && def.name !== "name",
            ...(kind === "enum"
                ? {
                      enumValues: (enumsByName.get(def.typeName ?? "")?.elementDefs ?? [])
                          .slice()
                          .sort((a, b) => (a.ordinal ?? 0) - (b.ordinal ?? 0))
                          .map((element) => element.value ?? "")
                          .filter((value) => value !== ""),
                  }
                : {}),
        });
    }

    const rank = (field: EditorField): number =>
        field.name === "name" ? 0 : DESCRIPTION_KEYS.includes(field.name as (typeof DESCRIPTION_KEYS)[number]) ? 1 : 2;

    return fields.sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));
}

/**
 * One relationship-attribute picker's field (EDT-13): the def-driven data the
 * editor renders and the save writes. The picker component itself lives in
 * the webapp (DD-341); the descriptor and the merge/seed rules live here,
 * next to the plain fields' own (EDT-15/EDT-16).
 */
export type RelationshipField = {
    /** The `relationshipAttributes` key this picker owns. */
    readonly name: string;
    /** The label text: the attribute's `displayName` else its name (EDT-13). */
    readonly label: string;
    /** The entity type the picker searches for (the def's, unwrapped). */
    readonly targetType: string;
    /** `SINGLE` holds one entity, `SET`/`LIST` hold many (EDT-13). */
    readonly single: boolean;
    /** A definition whose `isOptional` is `false` carries the marker (EDT-13/17). */
    readonly required: boolean;
    /** The definition's relationship type, sent in every entry (EDT-16). */
    readonly relationshipTypeName?: string;
};

/** One chosen relationship target — a chip's value and a save entry (EDT-15). */
export type RelationshipPick = {
    readonly guid: string;
    readonly typeName: string;
    readonly displayText?: string;
    readonly qualifiedName?: string;
};

/** `array<X>` → `X`; anything else unchanged (EDT-13's target unwrap). */
function unwrapArrayType(typeName: string): string {
    const match = /^array<(.+)>$/.exec(typeName);

    return match?.[1] ?? typeName;
}

/**
 * The relationship-attribute fields for an entity definition, from its own
 * `relationshipAttributeDefs` and its supertype chain — the same walk and the
 * same first-wins merge EDT-03 makes (EDT-13, DD-338). A name two definitions
 * carry once keeps the first definition's `relationshipTypeName`.
 * @param entityDef the entity's own definition
 * @param defsByName every entity definition by name (for the supertype links)
 * @returns the picker fields, in name order (the plain fields keep the top)
 */
export function buildRelationshipFields(
    entityDef: AtlasEntityDef,
    defsByName: ReadonlyMap<string, AtlasEntityDef>,
): RelationshipField[] {
    const merged = new Map<string, AtlasRelationshipAttributeDef>();
    const seenDefs = new Set<string>();
    const queue: AtlasEntityDef[] = [entityDef];

    while (queue.length > 0) {
        const current = queue.shift() as AtlasEntityDef;
        if (current.name && seenDefs.has(current.name)) {
            continue;
        }
        if (current.name) {
            seenDefs.add(current.name);
        }
        for (const def of current.relationshipAttributeDefs ?? []) {
            if (def.name && !merged.has(def.name) && !DROPPED_ATTRIBUTES.has(def.name)) {
                merged.set(def.name, def);
            }
        }
        for (const superName of current.superTypes ?? []) {
            const superDef = defsByName.get(superName);
            if (superDef) {
                queue.push(superDef);
            }
        }
    }

    const fields: RelationshipField[] = [];
    for (const def of merged.values()) {
        const typeName = def.typeName ?? "";
        if (typeName === "") {
            continue;
        }
        const target = unwrapArrayType(typeName);
        fields.push({
            name: def.name as string,
            label: `${def.displayName ?? def.name} (${target})`,
            targetType: target,
            single: (def.cardinality ?? "SINGLE") === "SINGLE",
            required: def.isOptional === false,
            ...(def.relationshipTypeName ? { relationshipTypeName: def.relationshipTypeName } : {}),
        });
    }

    return fields.sort((a, b) => a.name.localeCompare(b.name));
}

/** The entry a found entity or a seed row becomes, or null without a guid. */
function pickFrom(source: {
    guid?: string | null;
    typeName?: string | null;
    displayText?: string | null;
    qualifiedName?: string | null;
}): RelationshipPick | null {
    if (typeof source.guid !== "string" || source.guid === "") {
        return null;
    }

    return {
        guid: source.guid,
        typeName: source.typeName ?? "",
        ...(typeof source.displayText === "string" && source.displayText !== ""
            ? { displayText: source.displayText }
            : {}),
        ...(typeof source.qualifiedName === "string" && source.qualifiedName !== ""
            ? { qualifiedName: source.qualifiedName }
            : {}),
    };
}

/**
 * The pick entry a search answer contributes (EDT-14's pick path — the
 * component keeps no copy of the wire shape).
 * @param entity the search result's entity header
 * @returns the chip's value, or null when it carries no guid to attach
 */
export function relationshipEntry(entity: AtlasEntityHeader): RelationshipPick | null {
    return pickFrom(entity);
}

/** A read's `relationshipAttributes` value as a list of related entities. */
function asRelatedList(value: unknown): AtlasRelatedEntity[] {
    if (Array.isArray(value)) {
        return value as AtlasRelatedEntity[];
    }
    if (value !== null && typeof value === "object") {
        return [value as AtlasRelatedEntity];
    }

    return [];
}

/**
 * The picker seeds for the fields, read off the entity (EDT-15): each key's
 * list keeps only the `ACTIVE` entries (the server keeps removed edges in the
 * read as `DELETED`); a `SINGLE` field seeds from the first ACTIVE entry;
 * create mode (no `relationshipAttributes`) seeds nothing.
 * @param entity the entity being edited
 * @param fields the picker fields to seed
 * @returns the field name → chips map
 */
export function seedRelationshipValues(
    entity: AtlasEntity,
    fields: readonly RelationshipField[],
): Record<string, RelationshipPick[]> {
    const stored = entity.relationshipAttributes ?? {};
    const values: Record<string, RelationshipPick[]> = {};

    for (const field of fields) {
        const picks: RelationshipPick[] = [];
        for (const row of asRelatedList(stored[field.name])) {
            if (row.relationshipStatus !== undefined && row.relationshipStatus !== "ACTIVE") {
                continue; // EDT-15: a DELETED edge is never seeded, shown, or echoed
            }
            const pick = pickFrom(row);
            if (pick !== null) {
                picks.push(pick);
            }
            if (field.single) {
                break;
            }
        }
        values[field.name] = picks;
    }

    return values;
}

/** The save entry one chip becomes (EDT-16's shape — no relationshipGuid). */
function saveEntry(pick: RelationshipPick, field: RelationshipField): Record<string, unknown> {
    return {
        guid: pick.guid,
        typeName: pick.typeName,
        ...(pick.displayText !== undefined ? { displayText: pick.displayText } : {}),
        ...(field.relationshipTypeName !== undefined ? { relationshipType: field.relationshipTypeName } : {}),
        relationshipStatus: "ACTIVE",
    };
}

/**
 * The merged entity for a relationship save (EDT-16), applied on top of
 * {@link mergeOntoEntity}'s attribute merge. For every picker the form
 * rendered, `relationshipAttributes` carries that key's full value — the
 * entry list for a multi field (`[]` empties it), the one entry or null for
 * a `SINGLE` one (null clears the edge; `[]` would answer 400, probed). Each
 * rendered key also drops from `attributes`: the picker owns the key, and a
 * reference left there re-attaches the edge the picker removed (the server's
 * `compactAttributes` moves it back, probed — DD-340). A key no picker
 * rendered passes through untouched; a `DELETED` seed is never echoed (the
 * seed never holds one, EDT-15).
 * @param entity the merged entity (attributes already written)
 * @param fields the picker fields the form rendered
 * @param values the picker values, by field name
 * @returns the entity to POST
 */
export function mergeRelationshipsOntoEntity(
    entity: AtlasEntity,
    fields: readonly RelationshipField[],
    values: ReadonlyMap<string, readonly RelationshipPick[]>,
): AtlasEntity {
    const relationshipAttributes: Record<string, unknown> = { ...entity.relationshipAttributes };
    const attributes = { ...(entity.attributes ?? {}) };

    for (const field of fields) {
        const picks = values.get(field.name);
        if (picks === undefined) {
            continue; // a picker the form did not render: the key passes through
        }
        delete attributes[field.name];
        if (field.single) {
            const only = picks[0];
            relationshipAttributes[field.name] = only === undefined ? null : saveEntry(only, field);
        } else {
            relationshipAttributes[field.name] = picks.map((pick) => saveEntry(pick, field));
        }
    }

    return { ...entity, attributes, relationshipAttributes };
}

/** A `datetime-local` input value from epoch milliseconds, local time. */
function toDateTimeLocal(epochMs: number): string {
    const date = new Date(epochMs);
    const pad = (value: number): string => String(value).padStart(2, "0");

    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * The form's initial values for the fields, read off the entity (EDT-02).
 * @param entity the entity being edited (create passes a bare entity)
 * @param fields the fields to seed
 * @returns the control name → value map
 */
export function toFormValues(entity: AtlasEntity, fields: readonly EditorField[]): Record<string, unknown> {
    const attributes = entity.attributes ?? {};
    const values: Record<string, unknown> = {};

    for (const field of fields) {
        const raw = attributes[field.name];
        switch (field.kind) {
            case "date":
                values[field.name] = typeof raw === "number" ? toDateTimeLocal(raw) : "";
                break;
            case "multi":
                values[field.name] = Array.isArray(raw) ? raw.map((value) => String(value ?? "")) : [];
                break;
            case "boolean":
                values[field.name] = raw === true;
                break;
            default:
                values[field.name] = raw ?? "";
        }
    }

    return values;
}

/**
 * The merged entity for a save: a clone of `entity` with each field's value
 * written back to `attributes`; everything else — `relationshipAttributes`,
 * `classifications`, unwritten attributes — passes through untouched (EDT-06).
 * @param entity the fetched (create: seeded) entity
 * @param fields the fields the form wrote
 * @param values the form's values
 * @returns the entity to POST
 */
export function mergeOntoEntity(
    entity: AtlasEntity,
    fields: readonly EditorField[],
    values: Record<string, unknown>,
): AtlasEntity {
    const attributes: Record<string, unknown> = { ...entity.attributes };

    for (const field of fields) {
        const raw = values[field.name];
        switch (field.kind) {
            case "date": {
                const parsed = raw ? new Date(String(raw)).getTime() : NaN;

                if (Number.isNaN(parsed)) {
                    delete attributes[field.name];
                } else {
                    attributes[field.name] = parsed;
                }
                break;
            }
            case "multi": {
                const list = Array.isArray(raw)
                    ? raw.map((value) => String(value).trim()).filter((value) => value !== "")
                    : [];

                if (list.length === 0) {
                    delete attributes[field.name];
                } else {
                    attributes[field.name] = list;
                }
                break;
            }
            case "number": {
                const text = String(raw ?? "").trim();

                if (text === "") {
                    delete attributes[field.name];
                } else {
                    const parsed = Number(text);

                    attributes[field.name] = Number.isNaN(parsed) ? text : parsed;
                }
                break;
            }
            case "boolean":
                attributes[field.name] = raw === true;
                break;
            default: {
                const text = String(raw ?? "").trim();

                if (text === "") {
                    delete attributes[field.name];
                } else {
                    attributes[field.name] = text;
                }
            }
        }
    }

    return { ...entity, attributes };
}
