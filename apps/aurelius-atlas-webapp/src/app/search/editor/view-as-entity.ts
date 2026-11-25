/**
 * The bridge between the view family and the editor's Atlas-shaped helpers
 * (VDE-01, VDE-04, VDE-07, DD-608, DD-612).
 *
 * The drawer reads and saves through the view doors (16.5c), but the form
 * helpers (`toFormValues`, `mergeOntoEntity`, `seedRelationshipValues`) and
 * the governance banner (EDT-23, VDE-11) were built on the `AtlasEntity`
 * shape and stay there. `entityFromView` answers that shape from a view —
 * the values as they are, the own tags as `classifications`, and each
 * `sections` end as a `relationshipAttributes` entry the pickers seed from —
 * so every helper keeps working on the view's material unchanged. 7.44
 * lifted `entityFromView` itself to `../shared/entity-from-view` so the
 * governance banner in details and the editor name it as a peer (DD-870);
 * this file imports it back. The save body is built from the view directly
 * by {@link bodyFromEdits}.
 */

import type { AtlasEntity, EntityView, ViewSaveRequest, ViewSectionInput } from "aurelius-atlas-data-access";

import { entityFromView } from "../shared/entity-from-view";
import {
    HIDDEN_BASE_ATTRIBUTES,
    type EditorField,
    type RelationshipField,
    type RelationshipPick,
    mergeOntoEntity,
    seedRelationshipValues,
    toFormValues,
} from "./form-fields";

/**
 * The mutation-door body for one save (VDE-03..VDE-05): the full attribute
 * map, the tag box's names as `classifications`, and one `sections` entry per
 * picker the form rendered (VDE-04). Term assignments ride no key at all —
 * the editor builds no picker for them, so the door leaves them as stored
 * (EDT-36, DD-828; the door's own `meanings` key stays for the glossary
 * callers, DD-612). An update names the base view's `updateTime` (AVW-04); a
 * create names no guid and carries the qualified name the editor seeded
 * (DD-592).
 * A field the person cleared rides `null`, so the door's merge (EWR-10)
 * drops the stored value instead of keeping it. A set no rendered picker
 * owns is left out, and the door leaves it unchanged (AVW-05). The three
 * hidden base attributes ride no key either (EDT-37): the read carries them,
 * the editor builds no control for them, and the body builder drops the keys
 * so the door leaves the stored values exactly as stored.
 * @param options the base (edit: the view being edited; create: null) and
 *   the draft it merges onto, the rendered fields and pickers, the form's
 *   values and picks, the tag names, and (quality mode, EDT-27) a full
 *   attribute map that replaces the field merge
 * @returns the one POST body for `ViewSaveService.save`
 */
export function bodyFromEdits(options: {
    base: EntityView | null;
    entity: AtlasEntity;
    typeName: string;
    fields: readonly EditorField[];
    values: Record<string, unknown>;
    relationshipFields: readonly RelationshipField[];
    relationshipValues: ReadonlyMap<string, readonly RelationshipPick[]>;
    classifications: readonly string[];
    attributes?: Record<string, unknown>;
}): ViewSaveRequest {
    const attributes =
        options.attributes !== undefined
            ? { ...options.attributes }
            : cleared(mergeOntoEntity(options.entity, options.fields, options.values).attributes ?? {}, options.fields);
    // The editor builds no control for the three (EDT-37), so the body names
    // none of them: the door's merge leaves an attribute it does not name as
    // stored (AVW-05), which is what keeps a stored owner intact. Only the
    // unrendered keys drop — a control the form does render keeps its write.
    if (options.attributes === undefined) {
        const rendered = new Set(options.fields.map((field) => field.name));
        for (const hidden of HIDDEN_BASE_ATTRIBUTES) {
            if (!rendered.has(hidden)) {
                delete attributes[hidden];
            }
        }
    }

    const sections: ViewSectionInput[] = [];
    for (const field of options.relationshipFields) {
        const picks = options.relationshipValues.get(field.name);
        if (picks === undefined) {
            continue; // a picker the form did not render: the set stays unchanged (AVW-05)
        }
        sections.push({ attribute: field.name, entities: picks.map((pick) => pick.guid) });
    }

    return {
        ...(options.base !== null ? { guid: options.base.guid, updateTime: options.base.updateTime } : {}),
        typeName: options.typeName,
        attributes,
        classifications: [...options.classifications],
        ...(options.relationshipFields.length > 0 ? { sections } : {}),
    };
}

/** Every field the merge left out rides `null` — the door's merge drops a
 * null the way the old full-map POST dropped an omitted key (EWR-10: a null
 * optional primitive stores nothing). */
function cleared(attributes: Record<string, unknown>, fields: readonly EditorField[]): Record<string, unknown> {
    for (const field of fields) {
        if (!(field.name in attributes)) {
            attributes[field.name] = null;
        }
    }

    return attributes;
}

/**
 * The values to keep after a conflict (VDE-07, DD-610): every control the
 * person left at the value it opened with answers the stored view; every one
 * they changed keeps their value. "Opened with" is a value comparison
 * against the old seed — the signal form exposes no dirty flag — so a field
 * typed back to its stored value counts as untouched and re-seeds the same.
 * @param oldView the view the editor held before the conflict
 * @param newView the stored view from the conflict answer
 * @param fields the rendered fields
 * @param current the form's values
 * @returns the values to keep
 */
export function valuesAfterConflict<T>(
    oldView: EntityView | null,
    newView: EntityView,
    fields: readonly EditorField[],
    current: Record<string, T>,
): Record<string, T> {
    const oldSeed = toFormValues(oldView === null ? { typeName: newView.typeName } : entityFromView(oldView), fields);
    const newSeed = toFormValues(entityFromView(newView), fields);
    const next: Record<string, T> = { ...current };
    for (const field of fields) {
        if (sameValue(current[field.name], oldSeed[field.name])) {
            // The seed answers the kinds the form holds (text, number-as-text,
            // boolean, string list) — the helper's own output contract.
            next[field.name] = newSeed[field.name] as T; // untouched: the stored value answers (VDE-07)
        }
    }

    return next;
}

/**
 * Whether a form value still answers the seed it opened with (the VDE-07
 * untouched test). A multi list ignores its blank trailing row — the
 * component always adds one, and it is not an edit (EDT-03).
 * @param value the form's current value
 * @param seed the value the old view seeded
 */
function sameValue(value: unknown, seed: unknown): boolean {
    if (Array.isArray(value) && Array.isArray(seed)) {
        const rows = (list: unknown[]): string[] => list.map((row) => textOf(row)).filter((row) => row !== "");

        return rows(value).join("\u0000") === rows(seed).join("\u0000");
    }

    return textOf(value) === textOf(seed);
}

/** The text one form slot holds; a non-text (a stray object) is "". */
function textOf(value: unknown): string {
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
        return String(value);
    }

    return value === null || value === undefined ? "" : "\u0001";
}

/**
 * The picks to keep after a conflict (VDE-07, DD-610): a picker whose chips
 * still answer the old seed re-seeds from the stored view; one the person
 * changed keeps their chips.
 * @param oldView the view the editor held before the conflict
 * @param newView the stored view from the conflict answer
 * @param fields the rendered pickers
 * @param current the person's pick maps
 * @returns the pick maps to keep, per picker
 */
export function picksAfterConflict(
    oldView: EntityView | null,
    newView: EntityView,
    fields: readonly RelationshipField[],
    current: ReadonlyMap<string, readonly RelationshipPick[]>,
): ReadonlyMap<string, readonly RelationshipPick[]> {
    const oldSeeds = seedRelationshipValues(
        oldView === null ? { typeName: newView.typeName } : entityFromView(oldView),
        fields,
    );
    const newSeeds = seedRelationshipValues(entityFromView(newView), fields);
    const next = new Map<string, readonly RelationshipPick[]>();
    for (const field of fields) {
        const picks = current.get(field.name) ?? [];
        const before = oldSeeds[field.name] ?? [];
        const untouched = picks.length === before.length && picks.every((pick, at) => pick.guid === before[at]?.guid);
        next.set(field.name, untouched ? (newSeeds[field.name] ?? []) : picks);
    }

    return next;
}

/**
 * The tag names to keep after a conflict (VDE-07, DD-610): the stored
 * entity's own tags answer the box, except the ones the person removed; the
 * ones they added stay added.
 * @param oldView the view the editor held before the conflict
 * @param newView the stored view from the conflict answer
 * @param current the box's names
 * @returns the names to keep
 */
export function tagsAfterConflict(
    oldView: EntityView | null,
    newView: EntityView,
    current: readonly string[],
): string[] {
    const before = oldView?.classificationNames ?? [];
    const removed = new Set(before.filter((name) => !current.includes(name)));

    return [
        ...(newView.classificationNames ?? []).filter((name) => !removed.has(name)),
        ...current.filter((name) => !before.includes(name)),
    ];
}
