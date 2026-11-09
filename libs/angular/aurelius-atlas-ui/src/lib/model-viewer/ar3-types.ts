/**
 * The diagram's model types (LDG-11's shape, DD-419): the pieces of the
 * parsed ar3 document the {@link ModelViewer} canvas reads — the view it
 * draws, the placed nodes and routed connections, and the relations whose
 * types style the connections. The types live with the canvas so a caller
 * outside the details page can hand it a document of its own; the webapp's
 * reader (`parse-ar3.ts`) parses into these same shapes and re-exports them,
 * so LDG-11's citations stay with the parser.
 *
 * The reader-only fields the canvas never touches (properties, descriptions,
 * the organization tree) stay in the reader's own interfaces.
 */

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
    /** The view's nodes, in document order. */
    readonly nodes: readonly Ar3ViewNode[];
    /** The view's connections, in document order. */
    readonly connections: readonly Ar3ViewConnection[];
}

/** The two attributes an archimate relation style reads (LDG-36). */
export interface Ar3RelationOptions {
    /** The `@accessType` attribute (`Read`, `Write`, or `ReadWrite`). */
    readonly accessType: string;
    /** The `@isDirected` attribute, kept as its raw string. */
    readonly isDirected: string;
}

/** One model relation as far as the canvas reads it (LDG-14/LDG-36). */
export interface Ar3DiagramRelation {
    /** The relation's `@identifier`. */
    readonly id: string;
    /** The relation's `@xsi_type` (`lineage_relation` on the shipped chain). */
    readonly type: string;
    /** The relation's styling options (LDG-36). */
    readonly options: Ar3RelationOptions;
}

/** One model element as far as the canvas reads it (LDG-13/LDG-33). */
export interface Ar3DiagramElement {
    /** The element's `@xsi_type` — the key of the shape, class, and glyph tables. */
    readonly type: string;
}

/** The document as far as the canvas reads it (LDG-12). */
export interface Ar3DiagramModel {
    /** The elements by id — a node takes its type from the element it references. */
    readonly elements: ReadonlyMap<string, Ar3DiagramElement>;
    /** The relations by id — a connection styles itself from its own type. */
    readonly relations: ReadonlyMap<string, Ar3DiagramRelation>;
    /** The views, in document order — the canvas draws the given one (LDG-12). */
    readonly views: readonly Ar3View[];
}

/**
 * The concept a node's click selects (LDG-17): the referenced element's id,
 * or the node's own when it references none — the legacy's `ref ?? id`.
 * @param node the placed node
 */
export function nodeConceptId(node: Ar3ViewNode): string {
    return node.ref ?? node.id;
}

/**
 * The concept a connection's click selects (LDG-17): the referenced
 * relation's id, or the connection's own — the legacy's `ref ?? id`.
 * @param connection the routed connection
 */
export function connectionConceptId(connection: Ar3ViewConnection): string {
    return connection.ref ?? connection.id;
}
