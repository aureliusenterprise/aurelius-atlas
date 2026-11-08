import { NgClass } from "@angular/common";
import {
    ChangeDetectionStrategy,
    Component,
    computed,
    effect,
    input,
    output,
    viewChild,
    type ElementRef,
} from "@angular/core";
import { select } from "d3-selection";
import { zoom, zoomIdentity, type ZoomBehavior, type ZoomTransform } from "d3-zoom";

import {
    AR3_MARKER_DEFS,
    ar3Class,
    ar3ConnectionStyle,
    ar3Icon,
    ar3NodeShape,
    nodePath,
    NO_RELATION_OPTIONS,
    type Ar3ConnectionStyle,
    type Ar3MarkerDef,
} from "./archimate-shapes";
import { BOUNDS_INSET, ZOOM_SCALE_EXTENT } from "./lineage-shapes";
import { buildConnectionPath, type PathSurface } from "./connection-path";
import {
    connectionConceptId,
    nodeConceptId,
    type Ar3DiagramModel,
    type Ar3View,
    type Ar3ViewConnection,
    type Ar3ViewNode,
} from "./ar3-types";

/** The drawn node: a view node with its resolved shape (LDG-12/LDG-13/LDG-33). */
interface DrawnNode {
    readonly node: Ar3ViewNode;
    /** The shape path from `x,y,w,h` (the legacy's `basicShapes`, LDG-33). */
    readonly shape: string;
    /** The fill class (LDG-34: the archimate layer, or dataset/process). */
    readonly shapeClass: string;
    /** Whether the type icon draws (LDG-33: no for a junction or the grouping). */
    readonly showIcon: boolean;
    /** Whether the name draws (LDG-33: no for a junction). */
    readonly showName: boolean;
    /** The name inside the shape (LDG-11's display name). */
    readonly name: string;
    /** The 16x16 icon path, or null when the type has none. */
    readonly icon: string | null;
    /** The icon's fill class (LDG-35), empty when no table names the type. */
    readonly iconColor: string;
    /** The concept a click selects (LDG-17: `ref ?? id`). */
    readonly concept: string;
    /** The raw model position (LDG-15: `translate(x, y)`; the group holds the shift). */
    readonly transform: string;
}

/** The drawn connection: a view connection with its resolved path (LDG-14/LDG-36). */
interface DrawnConnection {
    readonly connection: Ar3ViewConnection;
    /** The absolute path in model coordinates, empty when nothing draws. */
    readonly path: string;
    /** The relation name at the path centre, or empty (no label). */
    readonly name: string;
    /** The relation type's markers and dash (LDG-36). */
    readonly style: Ar3ConnectionStyle;
    /** The concept a click selects (LDG-17: `ref ?? id`). */
    readonly concept: string;
}

/**
 * The lineage/archimate diagram canvas (LDG-12..18, LDG-33..36, DD-418,
 * DD-419): one ar3 view drawn as the legacy modelview2 drew it — nodes first,
 * connections on top, every node and connection riding its raw model
 * coordinate under one bounds group shifted by `-minX, -minY` plus the
 * default inset (LDG-15, DD-417), each connection the
 * `getShortestLineEndpoints` polyline through the given bendpoints with its
 * relation type's markers and dash (LDG-14/LDG-36). The shape, fill class,
 * and glyph tables behind it are the ported legacy tables (LDG-33..35); the
 * eight defs markers and the twelve relation styles are `ar3Relations` and
 * `ar3RelationDef` verbatim (LDG-36).
 *
 * The component is dumb (DD-419, the lib's rule): it draws the `view` of the
 * `model` it is given and never fetches, routes, or owns the selection. The
 * caller reads {@link conceptSelected} and answers with {@link selected};
 * the drawing styles the selected concept with the legacy's `.is-selected`
 * stroke (`#40e0d0`), and {@link highlightedGuid} paints one concept with the
 * legacy's `.is-highlighted` stroke (`hsl(141, 53%, 53%)`, LDG-18) — the node
 * whose element ref or id equals it. Pan and zoom ride the SVG with d3-zoom at
 * the legacy's [0.5, 3] extent on the drawing group (LDG-16); {@link resetZoom}
 * returns to the identity for the caller's toolbar.
 *
 * 7.22b's details-page box (LDG-09) and 7.22d's toolbar (LDG-27) stay with
 * the webapp: the box fetches, the toolbar toggles fullscreen and saves the
 * PNG. This canvas is the picture both serve, reusable wherever a model
 * needs drawing.
 */
@Component({
    selector: "aurelius-atlas-ui-lineage-diagram",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [NgClass],
    template: `
        <svg class="lineage-svg" #svg>
            <!-- LDG-14/LDG-36: the marker set — the legacy defs loop over
                 ar3RelationDef, each path keeping the legacy's
                 stroke-dasharray="999" so a dashed connection never dashes
                 its own arrowhead. -->
            <svg:defs>
                @for (marker of markerDefs; track marker.id) {
                    <svg:marker
                        [attr.id]="marker.id"
                        [attr.refX]="marker.refX"
                        [attr.refY]="marker.refY"
                        [attr.markerWidth]="marker.markerWidth"
                        [attr.markerHeight]="marker.markerHeight"
                        orient="auto"
                    >
                        <svg:path
                            [attr.d]="marker.path"
                            [style.fill]="marker.fill"
                            [style.stroke]="marker.stroke === '' ? null : marker.stroke"
                            stroke-dasharray="999"
                        ></svg:path>
                    </svg:marker>
                }
            </svg:defs>
            <!-- The legacy's #modelview-background rect: the white ground the
                 drawing rides (modelview.component.scss's .background) — the
                 caller's fullscreen overlay is only opaque because of it.
                 Excluded from the html2canvas fallback, as in the legacy. -->
            <svg:rect class="background" width="100%" height="100%" data-html2canvas-ignore></svg:rect>
            <!-- LDG-15: the bounds group carries the legacy's -minX/-minY
                 translate; LDG-16: the zoom transform rides the parent so
                 pan/zoom and the bounds compose (the legacy applied the
                 transform to the whole #modelview group — same DOM here). -->
            <svg:g class="lineage-zoom" #zoomTarget>
                <svg:g class="lineage-bounds" [attr.transform]="boundsTransform()">
                    @for (drawn of nodes(); track drawn.node.id) {
                        <!-- LDG-12/LDG-13: the node — the shape path from
                             x,y,w,h translated to the bounds-normalised
                             position, the type-class fill, the 16x16 icon
                             floated right, the clipped name (the legacy's
                             foreignObject label, LDG-13/LDG-33..35). -->
                        <svg:g
                            class="node"
                            [ngClass]="drawn.shapeClass"
                            [class.is-selected]="isSelected(drawn.concept)"
                            [class.is-highlighted]="isHighlighted(drawn)"
                            [attr.transform]="drawn.transform"
                            [attr.data-concept]="drawn.concept"
                            (click)="conceptSelected.emit(drawn.concept)"
                        >
                            <svg:clipPath [attr.id]="'clip-' + drawn.node.id">
                                <svg:path [attr.d]="drawn.shape"></svg:path>
                            </svg:clipPath>
                            <svg:path class="node-shape" [attr.d]="drawn.shape"></svg:path>
                            <svg:g [attr.clip-path]="'url(#clip-' + drawn.node.id + ')'">
                                <svg:foreignObject [attr.width]="drawn.node.width" [attr.height]="drawn.node.height">
                                    <xhtml:div xmlns="http://www.w3.org/1999/xhtml" class="node-content">
                                        @if (drawn.showIcon && drawn.icon) {
                                            <xhtml:span class="node-icon">
                                                <svg width="16px" height="16px" viewBox="0 0 16 16">
                                                    <path [attr.d]="drawn.icon" [class]="drawn.iconColor"></path>
                                                </svg>
                                            </xhtml:span>
                                        }
                                        @if (drawn.showName && drawn.name) {
                                            <xhtml:span class="node-text" [attr.title]="drawn.name">{{
                                                drawn.name
                                            }}</xhtml:span>
                                        }
                                    </xhtml:div>
                                </svg:foreignObject>
                            </svg:g>
                        </svg:g>
                    }
                    @for (drawn of connections(); track drawn.connection.id) {
                        <!-- LDG-14: the connection — the edge-anchored path
                             through the bendpoints, the arrow markers, the
                             relation name at the path centre. -->
                        @if (drawn.path) {
                            <svg:g
                                class="connection"
                                [class.is-selected]="isSelected(drawn.concept)"
                                [attr.data-concept]="drawn.concept"
                                (click)="conceptSelected.emit(drawn.concept)"
                            >
                                <!-- DD-409: the wide invisible twin of the visible
                                 path — the click target. The legacy's edge is a
                                 ~1 px stroke, nearly unhittable (its own known
                                 flaw); this stroke makes the whole edge clickable. -->
                                <svg:path class="connection-hit" [attr.d]="drawn.path"></svg:path>
                                <svg:path
                                    class="connection-path"
                                    [attr.id]="'path-' + drawn.connection.id"
                                    [attr.d]="drawn.path"
                                    [attr.marker-start]="
                                        drawn.style.markerStart ? 'url(#' + drawn.style.markerStart + ')' : null
                                    "
                                    [attr.marker-end]="
                                        drawn.style.markerEnd ? 'url(#' + drawn.style.markerEnd + ')' : null
                                    "
                                    [style.stroke-dasharray]="drawn.style.dash"
                                ></svg:path>
                                @if (drawn.name) {
                                    <svg:text>
                                        <svg:textPath
                                            class="connection-label"
                                            [attr.href]="'#path-' + drawn.connection.id"
                                            dominant-baseline="ideographic"
                                            startOffset="50%"
                                        >
                                            {{ drawn.name }}
                                        </svg:textPath>
                                    </svg:text>
                                }
                            </svg:g>
                        }
                    }
                </svg:g>
            </svg:g>
        </svg>
    `,
    styles: `
        /* LDG-13/LDG-14/LDG-17/LDG-18: the legacy modelview style block
           (modelview.component.html's <defs><style>) and lineage.scss,
           narrowed to the two lineage fills and the two state strokes. */
        :host {
            display: block;
            width: 100%;
            height: 100%;
        }
        .lineage-svg {
            min-width: 100%;
            min-height: 100%;
            /* DD-408: no font-family — the legacy pinned "Segoe UI" here, which
               set the drawing apart from the rest of the app; the svg now
               inherits the body's stack (the brand's --bulma-family-primary). */
            font-size: 12px;
        }
        .background {
            /* The legacy's backdrop rect: the white ground, dashed at the
               edge, and the pan target (pointer-events). */
            fill: white;
            pointer-events: all;
            stroke: gray;
            stroke-dasharray: 2 2;
            stroke-width: 2px;
        }
        .node-shape {
            stroke: #a0a0a0;
            stroke-width: 2px;
            fill: none;
        }
        .node.dataset .node-shape {
            fill: hsl(240, 100%, 95%);
        }
        .node.process .node-shape {
            fill: hsl(171, 100%, 95%);
        }
        .node.is-highlighted .node-shape {
            stroke: hsl(141, 53%, 53%);
        }
        .node.is-selected .node-shape {
            stroke: #40e0d0;
        }
        .node-content {
            height: 100%;
            line-height: 1.1em;
            padding: 5px;
        }
        .node-icon {
            float: right;
            margin-left: 5px;
            stroke: #000000;
        }
        .node-icon .dataset {
            fill: blue;
            stroke: none;
        }
        .node-icon .process {
            fill: #00d1b2;
            stroke: none;
        }
        .node-text {
            display: block;
            max-height: 100%;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .connection-path {
            fill: none;
            stroke: black;
        }
        .connection-hit {
            /* DD-409: the clickable edge — transparent, wide, stroke-only. */
            fill: none;
            stroke: transparent;
            stroke-width: 10px;
            pointer-events: stroke;
        }
        .connection.is-selected .connection-path {
            stroke: #40e0d0;
        }
        .connection-label {
            text-anchor: middle;
        }
        /* LDG-34/LDG-35 (DD-418): the archimate fills — archimate3.scss's
           node block and archimate-icon.component.scss's glyph block. The
           builder drops an imported constant interpolated into a component's
           styles, so the rules ship as this literal copy; the canvas spec
           pins every line of the AR3_NODE_FILLS/AR3_ICON_FILLS tables into
           the shipped block, so the copy cannot drift. */
        .node.business .node-shape {
            fill: #ffffb5;
        }
        .node.application .node-shape {
            fill: #b5ffff;
        }
        .node.technology .node-shape {
            fill: #c9e7b7;
        }
        .node.physical .node-shape {
            fill: #c9e7b7;
        }
        .node.motivation .node-shape {
            fill: #ccccff;
        }
        .node.implementation .node-shape {
            fill: #ffe0e0;
        }
        .node.strategy .node-shape {
            fill: #f4deaa;
        }
        .node.and .node-shape {
            fill: #000000;
        }
        .node.or .node-shape {
            fill: #ffffff;
        }
        .node.location .node-shape {
            fill: #ff8c00;
        }
        .business {
            fill: #ffffb5;
        }
        .application {
            fill: #b5ffff;
        }
        .technology {
            fill: #c9e7b7;
        }
        .physical {
            fill: #c9e7b7;
        }
        .motivation {
            fill: #ccccff;
        }
        .implementation {
            fill: #ffe0e0;
        }
        .strategy {
            fill: #f4deaa;
        }
        .and {
            fill: #000000;
        }
        .or {
            fill: #ffffff;
        }
        .location {
            fill: #ff8c00;
        }
    `,
})
export class LineageDiagram {
    /** The parsed model the view belongs to (LDG-12/LDG-36): the canvas reads
        the elements' types (a node draws its element's shape) and the
        relations' types (a connection draws its relation's style). */
    readonly model = input<Ar3DiagramModel | null>(null);

    /** The view to draw (LDG-12): the caller resolves which one — the details
        page draws the state's active view, the legacy drew the first. */
    readonly view = input<Ar3View | null>(null);

    /** The selected concept (LDG-17), or null. The caller owns the state;
        this input only styles — the clicked element gains the legacy's
        `.is-selected` stroke. */
    readonly selected = input<string | null>(null);

    /** The page's entity guid (LDG-18): its node gains the highlight stroke. */
    readonly highlightedGuid = input<string | null>(null);

    /** A node or connection was clicked, with the concept it stands for
        (LDG-17: `ref ?? id`). The caller decides what selection means. */
    readonly conceptSelected = output<string>();

    /** The marker set — the legacy defs loop over `ar3RelationDef` (LDG-14/LDG-36). */
    protected readonly markerDefs: readonly Ar3MarkerDef[] = AR3_MARKER_DEFS;

    private readonly svgRef = viewChild.required<ElementRef<SVGSVGElement>>("svg");
    private readonly zoomTarget = viewChild.required<ElementRef<SVGGElement>>("zoomTarget");

    /** The d3 zoom behaviour, attached once the SVG is in the DOM (LDG-16). */
    private zoomBehavior: ZoomBehavior<SVGSVGElement, unknown> | null = null;

    /** The transform d3 currently holds — what `resetZoom()` restores from. */
    private currentTransform: ZoomTransform = zoomIdentity;

    /**
     * The view's bounds (LDG-15): the legacy's minX/minY over all node
     * positions — the group translation that sits the model's top-left node
     * at the drawing area's origin.
     */
    private readonly bounds = computed(() => {
        const nodes = this.view()?.nodes ?? [];
        if (nodes.length === 0) {
            return { minX: 0, minY: 0 };
        }
        return {
            minX: Math.min(...nodes.map((node) => node.x)),
            minY: Math.min(...nodes.map((node) => node.y)),
        };
    });

    /**
     * The bounds group's transform (LDG-15): the legacy's `-minX/-minY` plus
     * the default inset (DD-417) — the model sits `BOUNDS_INSET` px off the
     * drawing's top-left corner instead of flush against it. The inset rides
     * the same group, so pan, zoom, and the caller's save ride over it
     * unchanged.
     */
    protected readonly boundsTransform = computed(
        () => `translate(${BOUNDS_INSET - this.bounds().minX}, ${BOUNDS_INSET - this.bounds().minY})`,
    );

    /** The nodes as drawn (LDG-12/LDG-13/LDG-33..LDG-35). */
    protected readonly nodes = computed<DrawnNode[]>(() => {
        const view = this.view();
        const model = this.model();
        if (view === null || model === null) {
            return [];
        }
        return view.nodes.map((node) => {
            // LDG-13: the type is the referenced element's (the legacy's
            // `modelType ?? viewType`; the reader keeps no node type — LDG-11
            // — so an unreferenced node has none, and the tables' plain
            // fallback draws it).
            const element = node.ref === null ? undefined : model.elements.get(node.ref);
            const type = element?.type ?? "";
            const shape = ar3NodeShape(type);
            const icon = ar3Icon(type);
            return {
                node,
                shape: nodePath(shape.kind, node.width, node.height),
                shapeClass: ar3Class(type),
                showIcon: shape.showIcon,
                showName: shape.showName,
                name: node.displayName,
                icon: icon?.path ?? null,
                iconColor: icon?.color ?? "",
                concept: nodeConceptId(node),
                // LDG-15: the node rides its raw model coordinate; the one
                // bounds normalisation (the -minX/-minY on the group) shifts
                // every node and connection together — subtracting it here
                // too would double it and misalign the nodes from the paths.
                transform: `translate(${node.x}, ${node.y})`,
            };
        });
    });

    /** The connections as drawn (LDG-14/LDG-36), in document order over the nodes. */
    protected readonly connections = computed<DrawnConnection[]>(() => {
        const view = this.view();
        if (view === null) {
            return [];
        }
        const model = this.model();
        const byId = new Map(view.nodes.map((node) => [node.id, node]));
        return view.connections.map((connection) => {
            const source = byId.get(connection.source);
            const target = byId.get(connection.target);
            const surface = (node: Ar3ViewNode): PathSurface => ({
                x: node.x,
                y: node.y,
                width: node.width,
                height: node.height,
            });
            // LDG-36: the style rides the referenced relation (the legacy's
            // `relation?.type ?? connection.type` — the reader gives an
            // unreferenced connection no type, so the plain line draws).
            const relation = model?.relations.get(connection.ref ?? "");
            return {
                connection,
                path:
                    source === undefined || target === undefined
                        ? ""
                        : buildConnectionPath(
                              surface(source),
                              surface(target),
                              connection.bendpoints.map((bendpoint) => ({ x: bendpoint.x, y: bendpoint.y })),
                          ),
                name: connection.displayName,
                style: ar3ConnectionStyle(relation?.type ?? "", relation?.options ?? NO_RELATION_OPTIONS),
                concept: connectionConceptId(connection),
            };
        });
    });

    constructor() {
        // LDG-16: the zoom behaviour attaches once the SVG exists, with the
        // legacy's scale extent; every transform rides the zoom group (the
        // legacy's SVGZoomDirective applied `transform.toString()` to the
        // #zoomTarget element — kept).
        effect((onCleanup) => {
            const svg = this.svgRef().nativeElement;
            const target = this.zoomTarget().nativeElement;
            const container = select(svg);

            const behavior = zoom<SVGSVGElement, unknown>()
                .scaleExtent([...ZOOM_SCALE_EXTENT])
                .on("zoom", (event: { transform: ZoomTransform }) => {
                    this.currentTransform = event.transform;
                    target.setAttribute("transform", event.transform.toString());
                });
            this.zoomBehavior = behavior;
            container.call(behavior);

            onCleanup(() => {
                container.on(".zoom", null);
                this.zoomBehavior = null;
            });
        });
    }

    /**
     * Restore the identity transform (LDG-16): the seam the caller's toolbar
     * reset button calls. The legacy's `resetZoom` returned the transform it
     * replaced; this one does too.
     * @returns the transform that was in place
     */
    resetZoom(): ZoomTransform {
        const previous = this.currentTransform;
        if (this.zoomBehavior !== null) {
            this.zoomBehavior.transform(select(this.svgRef().nativeElement), zoomIdentity);
        }
        this.currentTransform = zoomIdentity;
        this.zoomTarget().nativeElement.setAttribute("transform", zoomIdentity.toString());
        return previous;
    }

    /** The drawing's svg element, for the caller's save flow (LDG-30). */
    svgElement(): SVGSVGElement {
        return this.svgRef().nativeElement;
    }

    /** Whether a drawn element holds the selection (LDG-17). */
    protected isSelected(concept: string): boolean {
        return this.selected() === concept;
    }

    /**
     * LDG-18: the highlight rides the node whose element id equals the
     * opened guid — the legacy's `highlightedEntity === ref || === id`.
     */
    protected isHighlighted(drawn: DrawnNode): boolean {
        const guid = this.highlightedGuid();
        return guid !== null && guid !== "" && (drawn.node.ref === guid || drawn.node.id === guid);
    }
}
