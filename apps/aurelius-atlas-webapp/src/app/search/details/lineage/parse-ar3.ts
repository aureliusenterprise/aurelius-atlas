/**
 * The archimate3 reader for the lineage document (LDG-11, DD-389): the legacy
 * `libs/modelview2/src/lib/parsers/archimate3/` field map
 * (`parse-model.ts`, `parse-element.ts`, `parse-relation.ts`, `parse-view.ts`,
 * `parse-view-node.ts`, `parse-view-connection.ts`) narrowed to what the
 * shipped producer emits — 8.2's fixed rule set (`lineage.py`) writes two
 * concept types, one relation type, and one view, and its own scenario fixture
 * (`apps/aurelius-atlas-lineage-model/scenarios/fixtures/graph.extract.json`)
 * shows no organization, no view reference, no property dict, and no style
 * block in that output. Those stay unparsed (DD-389): the rest has no page that
 * renders it. The property dict and the documentation reader arrived with
 * 7.22c's selection panel (LDG-21) — the page that needs them.
 *
 * The reader is pure and synchronous — the legacy `async` on every parse
 * function carried no behaviour (no await ever resolved anything). The names
 * keep the legacy precedence: a node shows the referenced element's name and
 * falls back to its own view label (the legacy's
 * `modelNode.name ?? viewNode.name`), a connection shows its relation's name.
 * The legacy decoded XML entities in the names (`decodeXML`); the shipped
 * producer writes plain JSON strings, so the raw value is the name.
 *
 * {@link parseAr3Model} throws on a document without `ar3_model` (DD-389):
 * a producer that changes its contract fails loudly here, and the box renders
 * the failure as LDG-10's empty state.
 */

/** A name/value property of a concept (`ar3_property`: the `get-properties.ts` map). */
export interface Ar3Property {
    /** The property name (`@propertyDefinitionRef`). */
    readonly name: string;
    /** The property value (`ar3_value.value`). */
    readonly value: string;
}

/** One model element (an entity of the lineage graph; its id is the guid). */
export interface Ar3Element {
    /** The element's `@identifier` — the entity guid on the shipped chain. */
    readonly id: string;
    /** The element's `@xsi_type` (`lineage_dataset` / `lineage_process`). */
    readonly type: string;
    /** The element's name (`ar3_name[0].value`), or empty. */
    readonly name: string;
    /** The element's description (`ar3_documentation.value`), or empty (LDG-21). */
    readonly description: string;
    /** The element's properties (`ar3_properties.ar3_property[]`), in order (LDG-21). */
    readonly properties: readonly Ar3Property[];
}

/** One model relation (one lineage edge). */
export interface Ar3Relation {
    /** The relation's `@identifier`. */
    readonly id: string;
    /** The `@source` element id. */
    readonly source: string;
    /** The `@target` element id. */
    readonly target: string;
    /** The relation's `@xsi_type` (`lineage_relation` on the shipped chain). */
    readonly type: string;
    /** The relation's name (`ar3_name[0].value`), or empty. */
    readonly name: string;
    /** The relation's description (`ar3_documentation.value`), or empty (LDG-21). */
    readonly description: string;
    /** The relation's properties (`ar3_properties.ar3_property[]`), in order (LDG-21). */
    readonly properties: readonly Ar3Property[];
}

/** One bendpoint of a view connection — a waypoint in model coordinates. */
export interface Ar3Bendpoint {
    readonly x: number;
    readonly y: number;
}

/** One node of a view: a placed rectangle referencing a model element. */
export interface Ar3ViewNode {
    /** The node's `@identifier`. */
    readonly id: string;
    /** The referenced element's id (`@elementRef`), or null for none. */
    readonly ref: string | null;
    /** The node's own label (`ar3_label[0].value`), or empty. */
    readonly label: string;
    /** The name to draw: the element's name, else the label (LDG-11). */
    readonly displayName: string;
    readonly x: number;
    readonly y: number;
    readonly width: number;
    readonly height: number;
}

/** One connection of a view: a path referencing a model relation. */
export interface Ar3ViewConnection {
    /** The connection's `@identifier`. */
    readonly id: string;
    /** The referenced relation's id (`@relationshipRef`), or null for none. */
    readonly ref: string | null;
    /** The `@source` view-node id. */
    readonly source: string;
    /** The `@target` view-node id. */
    readonly target: string;
    /** The name to draw: the relation's name, or empty (LDG-11). */
    readonly displayName: string;
    /** The waypoints, in order (`ar3_bendpoint[]`). */
    readonly bendpoints: readonly Ar3Bendpoint[];
}

/** One diagram view of the model (the lineage document carries exactly one). */
export interface Ar3View {
    /** The view's `@identifier`. */
    readonly id: string;
    /** The view's name (`ar3_name[0].value`) — the box's header (LDG-09). */
    readonly name: string;
    /** The view's description (`ar3_documentation.value`), or empty (LDG-24). */
    readonly description: string;
    /** The view's properties (`ar3_properties.ar3_property[]`), in order (LDG-24). */
    readonly properties: readonly Ar3Property[];
    /** The view's nodes, in document order. */
    readonly nodes: readonly Ar3ViewNode[];
    /** The view's connections, in document order. */
    readonly connections: readonly Ar3ViewConnection[];
}

/** The parsed model: the elements, the relations, and the views. */
export interface Ar3Model {
    /**
     * The model's name (`ar3_model.ar3_name[0].value`) — the quickview's
     * title (LDG-19, the legacy's `parseModel` info.name; 7.22d's toolbar
     * reads it too). The legacy's fallback for a nameless model is kept.
     */
    readonly name: string;
    /** The elements by id. */
    readonly elements: ReadonlyMap<string, Ar3Element>;
    /** The relations by id. */
    readonly relations: ReadonlyMap<string, Ar3Relation>;
    /** The views, in document order — the viewer draws the first (LDG-12). */
    readonly views: readonly Ar3View[];
}

/** One JSON object row, read by bracket access only (strict index rules). */
type JsonRow = Record<string, unknown>;

/**
 * Parse the answer's `model` string (LDG-11): the elements, the relations, and
 * the views with their placed nodes and routed connections.
 * @param model the ar3 document, JSON-encoded (DV-68's passthrough)
 * @returns the parsed model
 * @throws when the string is not JSON, or the JSON carries no `ar3_model`
 */
export function parseAr3Model(model: string): Ar3Model {
    const document = JSON.parse(model) as unknown;
    const ar3 = isRow(document) ? document["ar3_model"] : undefined;
    if (!isRow(ar3)) {
        throw new Error("the lineage document carries no ar3_model");
    }

    const elements = indexById(
        rows(ar3, "ar3_elements", "ar3_element").map((row) => ({
            id: text(row["@identifier"]),
            type: text(row["@xsi_type"]),
            name: entryName(row["ar3_name"]),
            description: entryText(row["ar3_documentation"]),
            properties: properties(row),
        })),
    );
    const relations = indexById(
        rows(ar3, "ar3_relationships", "ar3_relationship").map((row) => ({
            id: text(row["@identifier"]),
            source: text(row["@source"]),
            target: text(row["@target"]),
            type: text(row["@xsi_type"]),
            name: entryName(row["ar3_name"]),
            description: entryText(row["ar3_documentation"]),
            properties: properties(row),
        })),
    );
    const views = rows(ar3, "ar3_views", "ar3_diagrams")
        .flatMap((diagrams) => rowsOf(diagrams, "ar3_view"))
        .map((view) => parseView(view, elements, relations));
    // The legacy's info.name: the model's own name, with its fallback for a
    // document that carries none (parse-model.ts).
    const name = entryName(ar3["ar3_name"]);

    return { name: name === "" ? "ArchiMate Model" : name, elements, relations, views };
}

/**
 * Resolve a node's concept id for selection (LDG-17): the element it
 * references, else the node itself — the legacy's `ref ?? id`.
 * @param node the view node
 */
export function nodeConceptId(node: Ar3ViewNode): string {
    return node.ref ?? node.id;
}

/**
 * Resolve a connection's concept id for selection (LDG-17): the relation it
 * references, else the connection itself — the legacy's `ref ?? id`.
 * @param connection the view connection
 */
export function connectionConceptId(connection: Ar3ViewConnection): string {
    return connection.ref ?? connection.id;
}

/**
 * The concept a node stands for (LDG-18): the referenced element, or nothing
 * when the node references none the model carries.
 * @param model the parsed model
 * @param node the view node
 */
export function nodeElement(model: Ar3Model, node: Ar3ViewNode): Ar3Element | undefined {
    return node.ref === null ? undefined : model.elements.get(node.ref);
}

/** Parse one view and its placements (the legacy's `parseView`). */
function parseView(
    view: JsonRow,
    elements: ReadonlyMap<string, Ar3Element>,
    relations: ReadonlyMap<string, Ar3Relation>,
): Ar3View {
    const nodes = rowsOf(view, "ar3_node").map((node): Ar3ViewNode => {
        const ref = optionalText(node["@elementRef"]);
        const label = entryName(node["ar3_label"]);
        const element = ref === null ? undefined : elements.get(ref);
        return {
            id: text(node["@identifier"]),
            ref,
            label,
            displayName: element?.name !== undefined && element.name !== "" ? element.name : label,
            x: number(node["@x"]),
            y: number(node["@y"]),
            width: number(node["@w"]),
            height: number(node["@h"]),
        };
    });
    const connections = rowsOf(view, "ar3_connection").map((connection): Ar3ViewConnection => {
        const ref = optionalText(connection["@relationshipRef"]);
        const relation = ref === null ? undefined : relations.get(ref);
        return {
            id: text(connection["@identifier"]),
            ref,
            source: text(connection["@source"]),
            target: text(connection["@target"]),
            displayName: relation?.name ?? "",
            bendpoints: rowsOf(connection, "ar3_bendpoint").map((bendpoint) => ({
                x: number(bendpoint["@x"]),
                y: number(bendpoint["@y"]),
            })),
        };
    });

    return {
        id: text(view["@identifier"]),
        name: entryName(view["ar3_name"]),
        description: entryText(view["ar3_documentation"]),
        properties: properties(view),
        nodes,
        connections,
    };
}

/**
 * The concept's property list (the legacy's `getProperties`): each
 * `ar3_property` row contributes `{ name: @propertyDefinitionRef,
 * value: ar3_value.value }`. The legacy decoded XML entities in both; the
 * shipped producer writes plain JSON strings, so the raw value wins (as with
 * the names).
 */
function properties(concept: JsonRow): Ar3Property[] {
    const dict = concept["ar3_properties"];
    return isRow(dict)
        ? rowsOf(dict, "ar3_property").map((property) => ({
              name: text(property["@propertyDefinitionRef"]),
              value: entryText(property["ar3_value"]),
          }))
        : [];
}

/** The nested list at `container[key][key]` (the legacy's double-key walk). */
function rows(container: JsonRow, outerKey: string, innerKey: string): JsonRow[] {
    const outer = container[outerKey];
    return isRow(outer) ? rowsOf(outer, innerKey) : [];
}

/** The list under `row[key]`, tolerating the absent key and a lone object. */
function rowsOf(row: JsonRow, key: string): JsonRow[] {
    const value = row[key];
    if (Array.isArray(value)) {
        return value.filter(isRow);
    }
    return isRow(value) ? [value] : [];
}

/** Index rows by their id, first entry winning. */
function indexById<T extends { id: string }>(items: T[]): Map<string, T> {
    const byId = new Map<string, T>();
    for (const item of items) {
        if (!byId.has(item.id)) {
            byId.set(item.id, item);
        }
    }
    return byId;
}

/** Whether a value is a JSON object (the reader's only type test). */
function isRow(value: unknown): value is JsonRow {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** A required string field: absent or non-string answers the empty string. */
function text(value: unknown): string {
    return typeof value === "string" ? value : "";
}

/** An optional string field: absent or non-string answers null. */
function optionalText(value: unknown): string | null {
    return typeof value === "string" && value !== "" ? value : null;
}

/** The name of an `{ value }` entry list (the legacy's `ar3_name?.[0]`). */
function entryName(entries: unknown): string {
    const first = Array.isArray(entries) ? entries[0] : undefined;
    return isRow(first) ? text(first["value"]) : "";
}

/** The `value` of a single `{ value }` object (the legacy's `ar3_documentation?.value`). */
function entryText(entry: unknown): string {
    return isRow(entry) ? text(entry["value"]) : "";
}

/** A coordinate field (the legacy's `Number.parseFloat(@x ?? 0)`). */
function number(value: unknown): number {
    let parsed: number;
    if (typeof value === "number") {
        parsed = value;
    } else if (typeof value === "string") {
        parsed = Number.parseFloat(value);
    } else {
        parsed = 0;
    }
    return Number.isNaN(parsed) ? 0 : parsed;
}
