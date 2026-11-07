import type { LineageModelMetadata } from "aurelius-atlas-data-access";

import type { Ar3Model, Ar3Property } from "./parse-ar3";
import { humanReadableType } from "./lineage-metamodel";

/**
 * What the quickview knows about one thing in the model (LDG-19..LDG-24): the
 * legacy's `ModelEntity` (`libs/modelview2/src/lib/parsers/types.ts`), built
 * here from the parsed model instead of the legacy parser's output. The
 * {@link entitiesById} index keys every element, relation, view, view node,
 * and view connection by id (the legacy's `buildModelEntityIndex` spread:
 * elements, relations, views, then the view nodes and connections of every
 * view) — the id a selection carries (LDG-17's `ref ?? id`) always resolves,
 * and a node/connection with no reference selects itself (LDG-18).
 *
 * `kind` replaces the legacy's `parserType` discriminator (`'element' |
 * 'relationship' | 'view' | 'node' | 'connection'`); it drives the Open-this-
 * view button (LDG-20, the legacy's `parserType === 'view'` condition) and
 * which rows the Model tab lists (LDG-23: elements and relations only — the
 * legacy's tables hold `Object.values(elements)` and `Object.values(relations)`).
 */
export type LineageEntityKind = "element" | "relation" | "view" | "node" | "connection";

/** One row of the quickview's entity index (a `type`, not an interface: the
 * ui SortableTable's row constraint is `Record<string, unknown>`). */
export type LineageEntity = {
    /** The entity id — the concept id a selection carries. */
    readonly id: string;
    /** What kind of model entry this is. */
    readonly kind: LineageEntityKind;
    /** The name to show: the model name (the legacy's `name`). */
    readonly name: string;
    /** The raw type (`@xsi_type`; `ar3_View` for a view; empty for a plain node/connection). */
    readonly type: string;
    /** The metamodel's display name (LDG-20), or empty when unknown. */
    readonly humanReadableType: string;
    /** The documentation text (LDG-20), or empty. */
    readonly description: string;
    /** The `ar3_properties` rows (LDG-21's left side of the merge). */
    readonly properties: readonly Ar3Property[];
};

/**
 * The legacy's `entitiesById` spread, ported (LDG-19..LDG-22): elements,
 * relations, views, then every view's nodes and connections — a later entry
 * with the same id wins, exactly like the object spread did (in the shipped
 * model no two share an id; a producer that breaks that gets the view's copy,
 * as the legacy's did, because the view entities come last).
 * @param model the parsed model
 */
export function buildEntitiesById(model: Ar3Model): ReadonlyMap<string, LineageEntity> {
    const entities = new Map<string, LineageEntity>();
    for (const element of model.elements.values()) {
        entities.set(element.id, {
            id: element.id,
            kind: "element",
            name: element.name,
            type: element.type,
            humanReadableType: humanReadableType(element.type),
            description: element.description,
            properties: element.properties,
        });
    }
    for (const relation of model.relations.values()) {
        entities.set(relation.id, {
            id: relation.id,
            kind: "relation",
            name: relation.name,
            type: relation.type,
            humanReadableType: humanReadableType(relation.type),
            description: relation.description,
            properties: relation.properties,
        });
    }
    for (const view of model.views) {
        entities.set(view.id, {
            id: view.id,
            kind: "view",
            name: view.name,
            // The legacy parser stamps a view with the type its human name
            // resolves from (parse-view.ts: type 'ar3_View').
            type: "ar3_View",
            humanReadableType: humanReadableType("ar3_View"),
            description: view.description,
            properties: view.properties,
        });
        for (const node of view.nodes) {
            entities.set(node.id, {
                id: node.id,
                kind: "node",
                // The legacy keeps the node's own label (its `ar3_label`); the
                // diagram's placement, not the element's name.
                name: node.label,
                type: "",
                humanReadableType: "",
                description: "",
                properties: [],
            });
        }
        for (const connection of view.connections) {
            entities.set(connection.id, {
                id: connection.id,
                kind: "connection",
                name: "",
                type: "",
                humanReadableType: "",
                description: "",
                properties: [],
            });
        }
    }
    return entities;
}

/**
 * The Selection tab's property rows (LDG-21): the concept's `ar3_properties`
 * widened by the metadata row whose `id` equals the concept id — the legacy's
 * `{ ...entity.properties, ...data }` merge over
 * `ModelDataService.dataByConceptId`. The merge is a dictionary in the legacy;
 * here it is the row list the sortable table sorts (default order = the
 * merge's own order: the concept's properties, then the row's new names).
 * A row value replaces a same-named property (the spread's precedence); a
 * concept with no metadata row keeps its properties alone; the empty merge
 * hides the table (the legacy's `length` condition).
 * @param entity the selected concept, or null for none
 * @param metadata the answer's metadata rows (LDG-02's list)
 * @returns one `{ name, value }` row per merged property name
 */
export function mergeProperties(
    entity: LineageEntity | null,
    metadata: readonly LineageModelMetadata[],
): { name: string; value: string }[] {
    if (entity === null) {
        return [];
    }
    const rows = new Map<string, string>();
    for (const property of entity.properties) {
        rows.set(property.name, property.value);
    }
    for (const row of metadata) {
        // Duplicate ids collapse to the last row's data — the legacy store's
        // per-id write (`dataByConceptId[id] = row.data`), so the row's own
        // keys replace earlier duplicates.
        if (row.id !== entity.id) {
            continue;
        }
        for (const [key, value] of Object.entries(row.data)) {
            rows.set(key, stringifyValue(value));
        }
    }
    return (
        [...rows.entries()]
            .map(([name, value]) => ({ name, value }))
            // The legacy renders the merged dictionary through the `keyvalue`
            // pipe, whose default comparator sorts by key — the table's default
            // order is therefore the names in code-unit order.
            .sort((left, right) => (left.name < right.name ? -1 : left.name > right.name ? 1 : 0))
    );
}

/**
 * What a metadata `data` value shows as (LDG-21): the shipped chain's values
 * are strings, numbers, booleans, and nulls (8.1's verified list — and the
 * details page shows the same rule, DET-11); anything else reads as its JSON.
 * @param value the row's value
 */
function stringifyValue(value: unknown): string {
    if (typeof value === "string") {
        return value;
    }
    if (value === null || value === undefined) {
        return "";
    }
    if (typeof value === "object") {
        return JSON.stringify(value);
    }
    return String(value);
}
