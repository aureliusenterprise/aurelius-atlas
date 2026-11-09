import { ChangeDetectionStrategy, Component, computed, effect, inject, signal, untracked } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { ActivatedRoute, Router } from "@angular/router";
import type { LineageModelMetadata } from "aurelius-atlas-data-access";

import { Drawer } from "aurelius-atlas-ui";

import type { Ar3Organization } from "./parse-ar3";
import type { LineageEntity } from "./lineage-entities";
import { buildEntitiesById } from "./lineage-entities";
import type { LineageIndexes } from "./lineage-indexes";
import { buildIndexes } from "./lineage-indexes";
import { LineageModelState } from "./lineage-state";
import { DRAWER_SCROLL } from "./lineage-shapes";
import { LineageBrowseTab } from "./browse-tab.component";
import { LineageModelTab } from "./model-tab.component";
import { LineageSelectionPanel } from "./selection-panel.component";
import { LineageViewTab } from "./view-tab.component";

/** The drawer's four tabs, in the legacy's order (LDG-19, DD-410: the
 * legacy's `keyvalue` order over the tabs object — browse, model, view,
 * selection). */
type ModelBrowserTab = "browse" | "model" | "view" | "selection";

/** The tab names the route may carry (the matcher's set, DD-415). */
const TAB_NAMES = new Set<string>(["browse", "model", "view", "selection"]);

/** The tab the route names when its segment is absent (the panel's resting
 * tab — the legacy's `openBrowser` default, the Browse the toolbar asks for). */
const DEFAULT_TAB: ModelBrowserTab = "browse";

/**
 * The lineage quickview drawer (LDG-19/LDG-25, DD-393/DD-415): the routed
 * panel in the root `drawer` aux outlet — the settings/alerts/editor shape
 * (SPL-14/DD-166, DD-322) applied to the legacy `model-browser` port. The
 * route carries the open state and the reader's place: `(drawer:lineage)`,
 * `(drawer:lineage:<tab>)`, and `(drawer:lineage:selection:<concept>)`
 * (DD-415) — so a reload reopens the same tab, the Selection tab's concept
 * rides the URL, and the tab strip reads the route instead of a signal kept
 * in step with it. The four tabs ride the drawer's sticky subhead strip
 * (DD-180's anatomy, the markdown-editor's tablist roles).
 *
 * The diagram's state is the app-scoped {@link LineageModelState} (DD-415):
 * the parsed model — from which the entity index (LDG-19), the LDG-22 maps,
 * and the organization tree derive here — the metadata rows, the selected
 * concept, and the drawn view, all read by the box and the viewer too. The
 * legacy's auto-open/auto-close subscriptions become navigation: a node
 * click (the viewer) routes to the Selection tab at that concept, and
 * clearing it routes away, so the painted box and the panel always agree
 * with no effect to reconcile them. The legacy's previous-tab restore dies
 * with the local tab signal — the URL's tab is the reader's last place, a
 * reload reads it back.
 *
 * The tabs render by the legacy's conditions (LDG-19): a selected concept
 * for Selection, a drawn view for View. A table row click re-routes the
 * Selection tab to that concept (the legacy's `selectEntity`, LDG-25);
 * choosing a view sets the drawn view and routes away (the legacy's
 * `viewSelected`); dismissal (backdrop, close button, Escape — the drawer's
 * own set, DD-393) clears the selection and routes away, so no box stays
 * painted without its panel (DD-403 — the deliberate departure from the
 * legacy's close, which left the box marked).
 *
 * The legacy quickview's chrome (DD-410): the header reads "Details" — the
 * quickview's own default name, which the model browser never overrode — and
 * the footer holds a Close button. The header's pin toggle is not ported: a
 * pinned panel makes no sense for a diagram overlay whose dismissal also
 * deselects (DD-403), and the drawer has no pin state (the deviation is
 * recorded in the spec).
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-model-browser",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [Drawer, LineageBrowseTab, LineageModelTab, LineageSelectionPanel, LineageViewTab],
    template: `
        <!-- The routed panel is open for its whole life (it exists only
             while its route is active — the settings panel's SPL-14
             posture); the drawer's own focus effect moves the focus into
             the panel on open, and the tabindex makes it a real keyboard
             stop (LDG-27's seam, now the route's arrival). -->
        <aurelius-atlas-ui-drawer
            [(active)]="active"
            [title]="heading"
            [ariaLabel]="closeLabel"
            (cancelRequested)="close()"
        >
            <!-- DD-402: Bulma's is-fullwidth grows the tabs to equal widths
                 across the strip (li flex-grow) and each label centers in its
                 cell — the wide, balanced tab row the reader asked for. -->
            <nav class="tabs is-fullwidth aurelius-model-browser-tabs" drawer-subhead role="tablist">
                <ul>
                    @for (tab of visibleTabs(); track tab.id) {
                        <!-- DD-416: Bulma paints the active tab from its
                             li.is-active a rule (tabs.scss), so the class
                             goes on the li too — on the anchor alone the
                             rule never matched and the tab stayed grey. The
                             anchor keeps it as the reader's selector. -->
                        <li [class.is-active]="currentTab() === tab.id">
                            <a
                                role="tab"
                                tabindex="0"
                                [class.is-active]="currentTab() === tab.id"
                                [attr.aria-selected]="currentTab() === tab.id"
                                class="aurelius-model-browser-tab"
                                (click)="selectTab(tab.id)"
                                (keydown.enter)="selectTab(tab.id)"
                                (keydown.space)="selectTab(tab.id); $event.preventDefault()"
                                >{{ tab.label }}</a
                            >
                        </li>
                    }
                </ul>
            </nav>
            @switch (currentTab()) {
                @case ("browse") {
                    <aurelius-atlas-webapp-lineage-browse-tab
                        [views]="viewEntities()"
                        [entities]="entities()"
                        [organizations]="organizations()"
                        [drawnViewId]="state.activeView()?.id ?? null"
                        [selectedConcept]="state.selected()"
                        (viewChosen)="onViewChosen($event)"
                        (conceptChosen)="chooseConcept($event)"
                    />
                }
                @case ("model") {
                    <aurelius-atlas-webapp-lineage-model-tab
                        [elements]="elementEntities()"
                        [relations]="relationEntities()"
                        [selectedEntity]="selectedEntity()"
                        (conceptChosen)="chooseConcept($event)"
                        (cleared)="clearSelection()"
                    />
                }
                @case ("selection") {
                    <aurelius-atlas-webapp-lineage-selection
                        [entity]="selectedEntity()"
                        [metadata]="metadata()"
                        [indexes]="indexes()"
                        [entities]="entities()"
                        [drawnViewId]="state.activeView()?.id ?? null"
                        (conceptChosen)="chooseConcept($event)"
                        (viewChosen)="onViewChosen($event)"
                    />
                }
                @case ("view") {
                    <aurelius-atlas-webapp-lineage-view-tab
                        [view]="activeViewEntity()"
                        [metadata]="metadata()"
                        [categories]="state.categories()"
                        [categoryColors]="state.categoryColors()"
                        (colorPicked)="onColorPicked($event)"
                    />
                }
            }
            <!-- DD-410: the legacy quickview footer's Close button (its own
                 footer template's literal "Close" — the catalogue carries no
                 key for it, so the shared modal-close string stands in). -->
            <button type="button" class="button aurelius-model-browser-close" drawer-footer (click)="close()">
                <span>{{ closeLabel }}</span>
            </button>
        </aurelius-atlas-ui-drawer>
    `,
    styles: `
        .aurelius-model-browser-tabs {
            /* The drawer panel is a flex column and this strip is its
               flex item (DD-416): with no pin, a long tab body (the Model
               tab's tables) shrinks the strip — Bulma's .tabs overflow
               makes its min-size 0 — the tab row clips and the rule under
               it rises mid-panel while the short tabs keep the full strip.
               The pin is the head's and foot's own flex-shrink: 0. */
            flex-shrink: 0;
            margin-bottom: 0;
        }
    `,
})
export class LineageModelBrowser {
    /** The shared diagram state (DD-415): model, metadata, selection, and
        drawn view — one instance, read by the box and the viewer too. */
    protected readonly state = inject(LineageModelState);

    private readonly router = inject(Router);

    /** The route's `:tab` and `:concept` (DD-415) — the matcher's posParams,
        read as a signal so a tab or concept change re-runs the computed
        views without rebuilding this component (DD-355's one-config rule). */
    private readonly routeParams = toSignal(inject(ActivatedRoute).paramMap, { initialValue: undefined });

    /** Whether the drawer is open: true for the panel's whole life — it
        exists only while its route is active (SPL-14) — and every closing
        path flips it before navigating away (the settings panel's SPL-14
        posture: the exit animation is not awaited; the route owns the
        state). */
    protected readonly active = signal(true);

    constructor() {
        // The URL's concept owns the selection on arrival (DD-415): a reload
        // of `(drawer:lineage:selection:<concept>)` — or a pasted link —
        // reopens the Selection tab on that concept, the way the settings
        // panel's reload keeps it open (SPL-14). A route without a concept
        // (any other tab) leaves the selection as it is: the legacy kept the
        // selected concept while the reader browsed the other tabs, so
        // switching to Browse must not deselect. In-app row clicks set the
        // signal before navigating, so this only fills it when it is not set.
        // The index read makes the page's fetch a dependency: a reload
        // mounts this panel and the page's load together, and load() clears
        // the selection with the old document (DD-415) — so the concept is
        // re-asserted when its model arrives, and a concept the loaded
        // document does not know (a drawer that outlived its page) never
        // paints.
        effect(() => {
            const concept = this.routeParams()?.get("concept") ?? null;
            if (concept !== null && concept !== "" && this.entities().has(concept)) {
                untracked(() => this.state.selected.set(concept));
            }
        });
    }

    /** The entity index (LDG-19's `entitiesById`), derived from the model. */
    protected readonly entities = computed<ReadonlyMap<string, LineageEntity>>(() => {
        const model = this.state.model();
        return model === null ? new Map() : buildEntitiesById(model);
    });

    /** The LDG-22 index maps, derived from the model (LDG-22). */
    protected readonly indexes = computed<LineageIndexes>(() => {
        const model = this.state.model();
        return model === null
            ? { conceptsByRelationId: new Map(), relationsByConceptId: new Map(), viewsByEntityId: new Map() }
            : buildIndexes(model);
    });

    /** The answer's metadata rows (LDG-21's merge input). */
    protected readonly metadata = computed<readonly LineageModelMetadata[]>(() => this.state.metadata());

    /** The Browse tab's folder tree (DD-406): the document's organization items. */
    protected readonly organizations = computed<readonly Ar3Organization[]>(
        () => this.state.model()?.organizations ?? [],
    );

    protected readonly closeLabel = $localize`:@@components.modal.close:Close`;

    /** The drawer's heading (DD-410): the legacy quickview's default name —
        the model browser never passed one, so every legacy panel read
        "Details", whichever concept opened it. */
    protected readonly heading = $localize`:@@search.details.components.navigation.details:Details`;

    /** The tab labels — the four legacy tab names (LDG-19). */
    private readonly labels: Record<ModelBrowserTab, string> = {
        browse: $localize`:@@modelview2.modelBrowser.modelBrowserBrowse:Browse`,
        model: $localize`:@@modelview2.modelBrowser.modelBrowserModel:Model`,
        selection: $localize`:@@modelview2.modelBrowser.modelBrowserSelection:Selection`,
        view: $localize`:@@modelview2.modelBrowser.modelBrowserView:View`,
    };

    /** The tab the route names (DD-415): the `:tab` segment when it names
        one of the four, else Browse (the matcher only lets the four
        through; a bare `lineage` rests here). */
    protected readonly currentTab = computed<ModelBrowserTab>(() => {
        const tab = this.routeParams()?.get("tab") ?? null;
        return tab !== null && TAB_NAMES.has(tab) ? (tab as ModelBrowserTab) : DEFAULT_TAB;
    });

    /** The visible tabs in legacy order (DD-410), minus those whose condition
        fails (LDG-19): a selected concept for Selection, a drawn view for
        View. */
    protected readonly visibleTabs = computed(() =>
        (["browse", "model", "view", "selection"] as const)
            .filter((id) => this.tabVisible(id))
            .map((id) => ({ id, label: this.labels[id] })),
    );

    /** A tab shows when its condition holds (LDG-19): Selection needs a
        selected concept, View a drawn view, the other two always show. */
    private tabVisible(id: ModelBrowserTab): boolean {
        if (id === "selection") {
            return this.state.selected() !== null && this.state.selected() !== "";
        }
        return id === "view" ? this.state.activeView() !== null : true;
    }

    protected readonly selectedEntity = computed(() => {
        const selected = this.state.selected();
        return selected === null || selected === "" ? null : (this.entities().get(selected) ?? null);
    });

    protected readonly elementEntities = computed(() => this.entityList("element"));

    protected readonly relationEntities = computed(() => this.entityList("relation"));

    protected readonly viewEntities = computed(() => this.entityList("view"));

    /** The drawn view's record (the View tab's subject, LDG-19's condition):
        the active view's id resolved through the index — a view entity. */
    protected readonly activeViewEntity = computed(() => {
        const view = this.state.activeView();
        return view === null ? null : (this.entities().get(view.id) ?? null);
    });

    /**
     * Switch the tab (DD-415): navigate the drawer outlet to the tab. The
     * Selection tab keeps carrying the concept so the URL stays whole
     * (`lineage:selection:<concept>`); the others drop it. One matcher
     * config serves every shape, so the component survives the switch and
     * the slide-in never replays (the DD-355 posture). The navigation
     * leaves the page's scroll alone (DD-416): the drawer is an overlay,
     * and its own route must not move the page underneath it.
     * @param id the tab to read
     */
    protected selectTab(id: ModelBrowserTab): void {
        const segments = id === "selection" ? ["lineage", "selection", this.state.selected() ?? ""] : ["lineage", id];
        void this.router.navigate([{ outlets: { drawer: segments } }], DRAWER_SCROLL);
    }

    /**
     * A table row or tree leaf chose a concept (the legacy's `selectEntity`,
     * LDG-25): the shared selection follows and the Selection tab routes to
     * it — the drawer re-reads the new concept in place.
     * @param id the concept to select
     */
    protected chooseConcept(id: string): void {
        this.state.selected.set(id);
        void this.router.navigate([{ outlets: { drawer: ["lineage", "selection", id] } }], DRAWER_SCROLL);
    }

    /**
     * The Model tab's selected row clicked again (LDG-25's deselect): the
     * selection clears and the drawer routes away — the panel closing is
     * the legacy's own deselect behaviour.
     */
    protected clearSelection(): void {
        this.close();
    }

    /**
     * Choosing a view (LDG-23): the shared drawn view follows for the viewer
     * to draw, and the panel closes with the selection (the legacy's rule —
     * a view choice ends the quickview read; DD-403's deselect rides
     * {@link close}).
     * @param id the view to draw
     */
    protected onViewChosen(id: string): void {
        this.state.drawnViewId.set(id);
        this.close();
    }

    /**
     * The View tab's legend picker changed one category's colour (UIC-31,
     * the legacy's `updateLegendColor`): the shared state holds the pick and
     * the canvas repaints every element in that category — the panel stays
     * open so the reader sees the change land.
     * @param picked the category and its new hex
     */
    protected onColorPicked(picked: { category: string; color: string }): void {
        this.state.setCategoryColor(picked.category, picked.color);
    }

    /**
     * Dismiss the panel (DD-410/DD-403/DD-415): the drawer's own set
     * (backdrop, close button, Escape) and the footer's Close all land here.
     * The selection clears so no box stays painted without its panel, and
     * the outlet navigates away — the panel is destroyed with the route and
     * the exit animation is not awaited (the settings panel's accepted cost,
     * SPL-14; the alert drawer's dismissal, DD-166's shape).
     */
    protected close(): void {
        this.state.selected.set(null);
        this.active.set(false);
        void this.router.navigate([{ outlets: { drawer: null } }], DRAWER_SCROLL);
    }

    private entityList(kind: LineageEntity["kind"]): LineageEntity[] {
        return [...this.entities().values()].filter((entity) => entity.kind === kind);
    }
}
