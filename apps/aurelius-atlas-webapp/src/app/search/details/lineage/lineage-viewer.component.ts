import { NgClass } from "@angular/common";
import {
    ChangeDetectionStrategy,
    Component,
    computed,
    effect,
    inject,
    input,
    signal,
    viewChild,
    type ElementRef,
} from "@angular/core";
import { Router } from "@angular/router";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faArrowsAlt, faCamera, faExpand, faInfo, faSearch } from "@fortawesome/free-solid-svg-icons";
import { select } from "d3-selection";
import { zoom, zoomIdentity, type ZoomBehavior, type ZoomTransform } from "d3-zoom";

import { SaveViewAsImage } from "./save-view-as-image";

import type { Ar3View, Ar3ViewConnection, Ar3ViewNode } from "./parse-ar3";
import { connectionConceptId, nodeConceptId } from "./parse-ar3";
import { LineageModelState } from "./lineage-state";
import { buildConnectionPath, type PathSurface } from "./connection-path";
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
import { BOUNDS_INSET, DRAWER_SCROLL, ZOOM_SCALE_EXTENT } from "./lineage-shapes";

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
 * The lineage viewer (LDG-12..LDG-18, DD-388/DD-390): the first view of a
 * parsed ar3 model, drawn as the legacy modelview2 drew it — nodes first,
 * connections on top, every node and connection riding its raw model
 * coordinate under one bounds group shifted by `-minX, -minY` (LDG-15:
 * the legacy `ModelviewService` bounds), each connection the
 * `getShortestLineEndpoints` polyline through the server's bendpoints with
 * its relation type's markers (LDG-14). Since 7.22e (DD-418) the drawing
 * speaks the archimate language too: each node's shape, fill class, and icon
 * come from the ported `ar3Elements`/`ar3Classes`/glyph tables (LDG-33..35)
 * and each connection's markers and dash from `ar3Relations` (LDG-36, the
 * `generic-arrow` end a lineage edge draws is its row). The 7.22b reading of
 * this line — the `generic-arrow` marker end — stays true for the shipped
 * chain's one relation type. The fills, icons, strokes, and the 50vh area are
 * the legacy `lineage.scss` / `archimate3.scss` /
 * `modelview-node.component.scss` / `modelview.component.scss` values
 * (LDG-13/LDG-34/LDG-35).
 *
 * Pan and zoom ride the SVG with d3-zoom at the legacy's [0.5, 3] extent,
 * applied as a transform on the drawing group (LDG-16, the legacy
 * `SVGZoomDirective` ported: the behaviour is attached once, `resetZoom()`
 * returns to the identity — 7.22d's toolbar button calls it).
 *
 * One selected-concept signal holds the selection (LDG-17): a node or
 * connection click selects the concept it references (`ref ?? id`), clicking
 * the same concept again clears it, and the drawn element gains the legacy's
 * `.is-selected` stroke (`#40e0d0`). Since DD-415 the selection is the shared
 * {@link LineageModelState} signal and a click doubles as navigation: the
 * routed quickview drawer opens on the Selection tab at the concept, and a
 * clear routes the drawer away. The `highlightedGuid` input paints the page's
 * own entity with the legacy's `.is-highlighted` stroke (`hsl(141, 53%, 53%)`,
 * LDG-18): the node whose element id equals it.
 *
 * The state is the app's shared signal set (DD-400, DD-415): the legacy's
 * per-node and per-connection `BasicStore` services have no twin here — the
 * shared slices (model, selection, drawn view) sit once in the state, read
 * and written by the box, this viewer, and the routed drawer.
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-viewer",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [FontAwesomeModule, NgClass],
    template: `
        <!-- LDG-28: the drawing region — the element the fullscreen toggle
             fixes to the viewport (the legacy's .modelview [class.is-fullscreen]). -->
        <div class="lineage-drawing" [class.is-fullscreen]="isFullscreen()">
            <!-- LDG-27: the control column (DD-397 — local markup, the
                 legacy's .controls buttons): icon buttons with the named
                 tooltip, the fullscreen-only Browse first, the save last
                 with the legacy's is-loading. -->
            <div class="controls buttons">
                @if (isFullscreen()) {
                    <button
                        type="button"
                        class="button is-info aurelius-lineage-browse"
                        [attr.title]="browseTooltip"
                        [attr.aria-label]="browseTooltip"
                        (click)="openBrowser()"
                    >
                        <span class="icon" aria-hidden="true"><fa-icon [icon]="faSearch"></fa-icon></span>
                    </button>
                }
                <button
                    type="button"
                    class="button aurelius-lineage-view-info"
                    [attr.title]="viewInfoTooltip"
                    [attr.aria-label]="viewInfoTooltip"
                    (click)="openViewInfo()"
                >
                    <span class="icon" aria-hidden="true"><fa-icon [icon]="faInfo"></fa-icon></span>
                </button>
                <button
                    type="button"
                    class="button aurelius-lineage-fullscreen"
                    [attr.title]="fullscreenTooltip"
                    [attr.aria-label]="fullscreenTooltip"
                    (click)="isFullscreen.set(!isFullscreen())"
                >
                    <span class="icon" aria-hidden="true"><fa-icon [icon]="faExpand"></fa-icon></span>
                </button>
                <button
                    type="button"
                    class="button aurelius-lineage-reset-zoom"
                    [attr.title]="resetZoomTooltip"
                    [attr.aria-label]="resetZoomTooltip"
                    (click)="resetZoom()"
                >
                    <span class="icon" aria-hidden="true"><fa-icon [icon]="faArrowsAlt"></fa-icon></span>
                </button>
                <button
                    type="button"
                    class="button aurelius-lineage-save"
                    [class.is-loading]="converting()"
                    [attr.title]="saveTooltip"
                    [attr.aria-label]="saveTooltip"
                    (click)="saveView()"
                >
                    <span class="icon" aria-hidden="true"><fa-icon [icon]="faCamera"></fa-icon></span>
                </button>
            </div>
            <!-- LDG-30: the measured container — the save hands its rect to
                 the converter, and html2canvas draws this element. -->
            <div id="screenshot-container" class="screenshot-container" #screen>
                <svg class="lineage-svg" #svg>
                    <!-- LDG-14/LDG-36: the marker set — the legacy defs loop
                         over ar3RelationDef, each path keeping the legacy's
                         stroke-dasharray="999" so a dashed connection never
                         dashes its own arrowhead. -->
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
                    <!-- The legacy's #modelview-background rect: the white
                         ground the drawing rides (modelview.component.scss's
                         .background) — the fixed fullscreen overlay is only
                         opaque because of it. Excluded from the html2canvas
                         fallback, as in the legacy. -->
                    <svg:rect class="background" width="100%" height="100%" data-html2canvas-ignore></svg:rect>
                    <!-- LDG-15: the bounds group carries the legacy's -minX/-minY
                 translate; LDG-16: the zoom transform rides the parent so
                 pan/zoom and the bounds compose (the legacy applied the
                 transform to the whole #modelview group — same DOM here). -->
                    <svg:g class="lineage-zoom" #zoomTarget>
                        <svg:g class="lineage-bounds" [attr.transform]="boundsTransform()">
                            @for (drawn of nodes(); track drawn.node.id) {
                                <!-- LDG-12/LDG-13: the node — the rectangle path from
                             x,y,w,h translated to the bounds-normalised
                             position, the type-class fill, the 16x16 icon
                             floated right, the clipped name (the legacy's
                             foreignObject label, LDG-13). -->
                                <svg:g
                                    class="node"
                                    [ngClass]="drawn.shapeClass"
                                    [class.is-selected]="isSelected(drawn.concept)"
                                    [class.is-highlighted]="isHighlighted(drawn)"
                                    [attr.transform]="drawn.transform"
                                    [attr.data-concept]="drawn.concept"
                                    (click)="onElementClicked(drawn.concept)"
                                >
                                    <svg:clipPath [attr.id]="'clip-' + drawn.node.id">
                                        <svg:path [attr.d]="drawn.shape"></svg:path>
                                    </svg:clipPath>
                                    <svg:path class="node-shape" [attr.d]="drawn.shape"></svg:path>
                                    <svg:g [attr.clip-path]="'url(#clip-' + drawn.node.id + ')'">
                                        <svg:foreignObject
                                            [attr.width]="drawn.node.width"
                                            [attr.height]="drawn.node.height"
                                        >
                                            <xhtml:div xmlns="http://www.w3.org/1999/xhtml" class="node-content">
                                                @if (drawn.showIcon && drawn.icon) {
                                                    <xhtml:span class="node-icon">
                                                        <svg width="16px" height="16px" viewBox="0 0 16 16">
                                                            <path
                                                                [attr.d]="drawn.icon"
                                                                [class]="drawn.iconColor"
                                                            ></path>
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
                             through the bendpoints, the arrow marker end,
                             the relation name at the path centre. -->
                                @if (drawn.path) {
                                    <svg:g
                                        class="connection"
                                        [class.is-selected]="isSelected(drawn.concept)"
                                        [attr.data-concept]="drawn.concept"
                                        (click)="onElementClicked(drawn.concept)"
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
            </div>
        </div>
    `,
    styles: `
        /* LDG-13/LDG-14/LDG-17/LDG-18: the legacy modelview style block
           (modelview.component.html's <defs><style>) and lineage.scss,
           narrowed to the two lineage fills and the two state strokes. */
        :host {
            display: block;
        }
        .lineage-drawing {
            /* LDG-15: the legacy's 50vh drawing area (.modelview) — the
               svg's own min-size fills it, as in the legacy. */
            height: 50vh;
            display: flex;
            align-items: stretch;
            position: relative;
        }
        .lineage-drawing.is-fullscreen {
            /* LDG-28: the legacy's fixed block. The top is the pinned
               navbar's height — NAVBAR_SCROLL_OFFSET's 68 px (app.config.ts,
               the legacy's 4.25rem measured on the same navbar). */
            position: fixed;
            top: 68px;
            left: 0;
            height: 100vh;
            width: 100%;
            z-index: 5;
        }
        .screenshot-container {
            /* LDG-30: the measured container of the save flow. */
            height: 100%;
            width: 100%;
            display: flex;
            align-items: stretch;
        }
        .controls {
            /* LDG-27: the legacy's top-right control column. */
            flex-direction: column;
            position: absolute;
            right: 0;
            padding: 10px;
            z-index: 1;
        }
        .controls .button {
            margin-right: 0;
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
           styles, so the rules ship as this literal copy; the viewer spec
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
export class LineageViewer {
    /** The page's entity guid (LDG-18): its node gains the highlight stroke. */
    readonly highlightedGuid = input<string | null>(null);

    /** The shared diagram state (DD-415/DD-400): the model the box fetched,
        the selection both surfaces share, and the drawn view. The viewer is
        the diagram's writer; the routed quickview drawer (DD-415) is its
        reader, so neither mounts the other any more. */
    protected readonly state = inject(LineageModelState);

    private readonly router = inject(Router);

    /** The marker set — the legacy defs loop over `ar3RelationDef` (LDG-14/LDG-36). */
    protected readonly markerDefs: readonly Ar3MarkerDef[] = AR3_MARKER_DEFS;

    /** The icons of the control column (LDG-27 — the legacy's five). */
    protected readonly faSearch = faSearch;
    protected readonly faInfo = faInfo;
    protected readonly faExpand = faExpand;
    protected readonly faArrowsAlt = faArrowsAlt;
    protected readonly faCamera = faCamera;

    /** The control column's tooltips (LDG-27 — the legacy's `modelview2.*`). */
    protected readonly browseTooltip = $localize`:@@modelview2.browse:Browse the model`;
    protected readonly viewInfoTooltip = $localize`:@@modelview2.viewInfo:View info`;
    protected readonly fullscreenTooltip = $localize`:@@modelview2.toggleFullscreen:Toggle fullscreen`;
    protected readonly resetZoomTooltip = $localize`:@@modelview2.resetZoom:Reset zoom and pan`;
    protected readonly saveTooltip = $localize`:@@modelview2.saveViewAsImage:Save view as image`;

    /** Whether the drawing is fullscreen (LDG-28 — the legacy's flag). */
    protected readonly isFullscreen = signal(false);

    /** Whether a PNG conversion is in flight (LDG-27's `is-loading`). */
    protected readonly converting = signal(false);

    /** The save flow (LDG-30/31). */
    private readonly saveViewAsImage = inject(SaveViewAsImage);

    private readonly svgRef = viewChild.required<ElementRef<SVGSVGElement>>("svg");
    private readonly zoomTarget = viewChild.required<ElementRef<SVGGElement>>("zoomTarget");
    /** The measured container of the save flow (LDG-30's width/height). */
    private readonly screen = viewChild.required<ElementRef<HTMLDivElement>>("screen");

    /** The d3 zoom behaviour, attached once the SVG is in the DOM (LDG-16). */
    private zoomBehavior: ZoomBehavior<SVGSVGElement, unknown> | null = null;

    /** The transform d3 currently holds — what `resetZoom()` restores from. */
    private currentTransform: ZoomTransform = zoomIdentity;

    /** The view being drawn: the chosen one, else the first (LDG-12/LDG-23,
        DD-415) — resolved once in the shared state, where the drawer reads
        the same answer for its tab conditions. */
    protected readonly drawnView = computed<Ar3View | null>(() => this.state.activeView());

    /**
     * The view's bounds (LDG-15): the legacy's minX/minY over all node
     * positions — the group translation that sits the model's top-left node
     * at the drawing area's origin.
     */
    private readonly bounds = computed(() => {
        const nodes = this.drawnView()?.nodes ?? [];
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
     * the same group, so pan, zoom, and the save ride over it unchanged.
     */
    protected readonly boundsTransform = computed(
        () => `translate(${BOUNDS_INSET - this.bounds().minX}, ${BOUNDS_INSET - this.bounds().minY})`,
    );

    /** The nodes as drawn (LDG-12/LDG-13/LDG-33..LDG-35). */
    protected readonly nodes = computed<DrawnNode[]>(() => {
        const view = this.drawnView();
        const model = this.state.model();
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
        const view = this.drawnView();
        if (view === null) {
            return [];
        }
        const model = this.state.model();
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
     * Restore the identity transform (LDG-16): the seam 7.22d's toolbar
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

    /**
     * LDG-27 (DD-415): open the quickview (legacy `openBrowser`) — now the
     * Browse tab's route, `(drawer:lineage:browse)`. Public because the box
     * header's Browse button sits above the viewer and calls it; the
     * toolbar's fullscreen-only Browse calls the same seam.
     */
    openBrowser(): void {
        void this.router.navigate([{ outlets: { drawer: ["lineage", "browse"] } }], DRAWER_SCROLL);
    }

    /** LDG-27 (DD-415): View-info opens the quickview on the View tab
        (legacy `openViewInfo`) — the View tab's route. */
    protected openViewInfo(): void {
        void this.router.navigate([{ outlets: { drawer: ["lineage", "view"] } }], DRAWER_SCROLL);
    }

    /**
     * LDG-29/LDG-30 (DD-407): save the drawn view (the legacy's
     * `saveViewAsImage`) at the transform the reader is looking at — the
     * legacy reset the zoom to identity around the save and restored it
     * after, which visibly jumps the view twice; here nothing moves. The
     * serialized clone already carries the zoom group's current transform,
     * so the picture matches the screen at the container's measured size.
     * One conversion at a time (the legacy's exhaustMap); a conversion that
     * ends in nothing — both paths failed — saves nothing, as the legacy's
     * empty-PNG skip did.
     */
    protected async saveView(): Promise<void> {
        const view = this.drawnView();
        if (view === null || this.converting()) {
            return;
        }
        this.converting.set(true);
        try {
            const { width, height } = this.screen().nativeElement.getBoundingClientRect();
            await this.saveViewAsImage.save(this.svgRef().nativeElement, width, height, view);
        } catch {
            // Both conversion paths failed — nothing to save (the legacy
            // answered no-PNG and the save was skipped silently).
        } finally {
            this.converting.set(false);
        }
    }

    /**
     * LDG-17/LDG-25 (DD-415): a node or connection click — the same concept
     * clears. The click writes the shared selection and the drawer follows
     * by route: selecting opens the Selection tab at the concept
     * (`drawer:lineage:selection:<concept>` — the legacy's auto-open, now
     * the URL's), clearing navigates the outlet away (the legacy's
     * close-on-deselect). The panel exists only while its route does, so
     * the two surfaces cannot drift.
     */
    protected onElementClicked(concept: string): void {
        const next = this.state.selected() === concept ? null : concept;
        this.state.selected.set(next);
        if (next === null) {
            void this.router.navigate([{ outlets: { drawer: null } }], DRAWER_SCROLL);
        } else {
            void this.router.navigate([{ outlets: { drawer: ["lineage", "selection", next] } }], DRAWER_SCROLL);
        }
    }

    /** Whether a drawn element holds the selection (LDG-17). */
    protected isSelected(concept: string): boolean {
        return this.state.selected() === concept;
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
