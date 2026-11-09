import {
    ChangeDetectionStrategy,
    Component,
    computed,
    inject,
    input,
    signal,
    viewChild,
    type ElementRef,
} from "@angular/core";
import { Router } from "@angular/router";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faArrowsAlt, faCamera, faExpand, faInfo, faSearch } from "@fortawesome/free-solid-svg-icons";
import { ModelViewer } from "aurelius-atlas-ui";

import type { Ar3View } from "./parse-ar3";
import { SaveViewAsImage } from "./save-view-as-image";

import { LineageModelState } from "./lineage-state";
import { DRAWER_SCROLL } from "./lineage-shapes";

/**
 * The lineage box's diagram state (LDG-12..18, LDG-27..31, DD-388/DD-390,
 * amended by DD-419): the details page's chrome around the shared
 * {@link ModelViewer} canvas. The canvas (the UI lib since DD-419) draws
 * the model and answers clicks; this shell owns what the page owns: the
 * shared state (the model the box fetched, the selection both surfaces read,
 * the drawn view — DD-400/DD-415), the routed drawer the clicks drive
 * (LDG-17/LDG-25), 7.22d's control column (LDG-27), the fullscreen toggle
 * (LDG-28), the reset-zoom button (LDG-29, forwarded to the canvas), and the
 * save-as-PNG flow (LDG-30/LDG-31), which reads the canvas's svg.
 *
 * The view drawn is the state's active one, else the first (LDG-12) —
 * resolved here, where the drawer reads the same answer.
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-viewer",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [FontAwesomeModule, ModelViewer],
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
                <aurelius-atlas-ui-model-viewer
                    [model]="state.model()"
                    [view]="drawnView()"
                    [selected]="state.selected()"
                    [highlightedGuid]="highlightedGuid()"
                    [categories]="state.categories()"
                    [categoryColors]="state.categoryColors()"
                    (conceptSelected)="onElementClicked($event)"
                />
            </div>
        </div>
    `,
    styles: `
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

    /** The shared canvas (DD-419): the save reads its svg, the reset button
        forwards to it. */
    private readonly diagram = viewChild.required(ModelViewer);

    /** The measured container of the save flow (LDG-30's width/height). */
    private readonly screen = viewChild.required<ElementRef<HTMLDivElement>>("screen");

    /**
     * The view being drawn: the chosen one, else the first (LDG-12/LDG-23,
     * DD-415) — resolved once in the shared state, where the drawer reads
     * the same answer for its tab conditions.
     */
    protected readonly drawnView = computed<Ar3View | null>(() => this.state.activeView());

    /**
     * Restore the identity transform (LDG-16): the seam 7.22d's toolbar
     * reset button calls, forwarded to the canvas.
     */
    resetZoom(): void {
        this.diagram().resetZoom();
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
            await this.saveViewAsImage.save(this.diagram().svgElement(), width, height, view);
        } catch {
            // Both conversion paths failed — nothing to save (the legacy
            // answered no-PNG and the save was skipped silently).
        } finally {
            this.converting.set(false);
        }
    }

    /**
     * LDG-17/LDG-25 (DD-415): a node or connection click (the canvas's
     * emit) — the same concept clears. The click writes the shared selection
     * and the drawer follows by route: selecting opens the Selection tab at
     * the concept (`drawer:lineage:selection:<concept>` — the legacy's
     * auto-open, now the URL's), clearing navigates the outlet away (the
     * legacy's close-on-deselect). The panel exists only while its route
     * does, so the two surfaces cannot drift.
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
}
