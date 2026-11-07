import {
    ChangeDetectionStrategy,
    Component,
    computed,
    effect,
    input,
    model,
    output,
    signal,
    untracked,
    viewChild,
    ElementRef,
} from "@angular/core";
import type { LineageModelMetadata } from "aurelius-atlas-data-access";
import { Drawer } from "aurelius-atlas-ui";

import type { LineageEntity } from "./lineage-entities";
import type { LineageIndexes } from "./lineage-indexes";
import { LineageBrowseTab } from "./browse-tab.component";
import { LineageModelTab } from "./model-tab.component";
import { LineageSelectionPanel } from "./selection-panel.component";
import { LineageViewTab } from "./view-tab.component";

/** The drawer's four tabs, in the legacy's order (LDG-19). */
type ModelBrowserTab = "browse" | "model" | "selection" | "view";

/**
 * The lineage quickview (LDG-19/LDG-25): the legacy
 * `model-browser/model-browser.component` ported onto the ui drawer
 * (DD-393) — the four tabs (Browse / Model / Selection / View) ride the
 * drawer's sticky subhead strip (DD-180's anatomy, the markdown-editor's
 * tablist roles), and the legacy's auto-open/auto-close subscriptions become
 * one effect over the shared selection signal:
 *
 * - a concept selection opens the drawer on the Selection tab (the legacy's
 *   `entitySelected` subscription);
 * - clearing it closes the drawer, and a Selection tab left visible by the
 *   close falls back to the previously read tab (the legacy's
 *   `entityDeselected`: `close()` + `selectTab(previousTab)`);
 * - choosing a view closes the drawer and re-emits for the viewer to draw
 *   (the legacy's `viewSelected`).
 *
 * Dismissal (backdrop, close button, Escape — the drawer's own set, DD-393)
 * hides the panel and leaves the selection painted in the diagram, as the
 * legacy's close did. The Selection and View tabs render only while their
 * condition holds (the legacy's `condition` observables): a selected concept,
 * and a selected view — the shipped model's one view counts from the start
 * (the legacy's `handleSelectView` default).
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-model-browser",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [Drawer, LineageBrowseTab, LineageModelTab, LineageSelectionPanel, LineageViewTab],
    template: `
        <!-- The toolbar's Browse focuses this panel on open (LDG-27): the
             drawer element is always in the DOM, so the seam exists; the
             tabindex makes the focus a real keyboard stop. -->
        <aurelius-atlas-ui-drawer #drawer tabindex="-1" [(active)]="active" [title]="title()" [ariaLabel]="closeLabel">
            <nav class="tabs aurelius-model-browser-tabs" drawer-subhead role="tablist">
                <ul>
                    @for (tab of visibleTabs(); track tab.id) {
                        <li>
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
                        [drawnViewId]="activeViewId()"
                        (viewChosen)="onViewChosen($event)"
                    />
                }
                @case ("model") {
                    <aurelius-atlas-webapp-lineage-model-tab
                        [elements]="elementEntities()"
                        [relations]="relationEntities()"
                        [selectedEntity]="selectedEntity()"
                        (conceptChosen)="selection.set($event)"
                        (cleared)="selection.set(null)"
                    />
                }
                @case ("selection") {
                    <aurelius-atlas-webapp-lineage-selection
                        [entity]="selectedEntity()"
                        [metadata]="metadata()"
                        [indexes]="indexes()"
                        [entities]="entities()"
                        [drawnViewId]="activeViewId()"
                        (conceptChosen)="selection.set($event)"
                        (viewChosen)="onViewChosen($event)"
                    />
                }
                @case ("view") {
                    <aurelius-atlas-webapp-lineage-view-tab [view]="activeViewEntity()" [metadata]="metadata()" />
                }
            }
        </aurelius-atlas-ui-drawer>
    `,
    styles: `
        .aurelius-model-browser-tabs {
            margin-bottom: 0;
        }
    `,
})
export class LineageModelBrowser {
    /** The entity index (LDG-19's `entitiesById`). */
    readonly entities = input.required<ReadonlyMap<string, LineageEntity>>();

    /** The LDG-22 index maps. */
    readonly indexes = input.required<LineageIndexes>();

    /** The answer's metadata rows (LDG-21's merge input). */
    readonly metadata = input<readonly LineageModelMetadata[]>([]);

    /** The drawn view's id (LDG-12 with the legacy's first-view default). */
    readonly activeViewId = input<string | null>(null);

    /** The drawer's heading — the model's own name (the box header's rule, LDG-09). */
    readonly title = input("");

    /** The selected concept (LDG-25: the one signal, two-way with the viewer). */
    readonly selection = model<string | null>(null);

    /** A view was chosen: the viewer draws it (LDG-25). */
    readonly viewChosen = output<string>();

    /** Whether the drawer is open — the legacy quickview's own state. */
    protected readonly active = model(false);

    /** The tab strip's selection (the legacy's `currentTab`). */
    protected readonly currentTab = signal<ModelBrowserTab>("browse");

    /** The tab read before the last switch (the legacy's `previousTab`). */
    private previousTab: ModelBrowserTab | null = null;

    /** The legacy's auto-open/auto-close, over the shared selection (LDG-25). */
    constructor() {
        effect(() => {
            const selected = this.selection();
            // Only the selection drives this effect — the legacy's
            // entitySelected fired per selection, not per tab change — so
            // the tab reads/writes below stay untracked: switching tabs
            // while a concept is selected must stick (the reader can leave
            // the Selection tab and the panel stays open).
            untracked(() => {
                if (selected !== null && selected !== "") {
                    this.selectTab("selection");
                    this.active.set(true);
                } else {
                    this.active.set(false);
                    if (this.currentTab() === "selection" && this.previousTab !== null) {
                        this.selectTab(this.previousTab);
                    }
                }
            });
        });
    }

    protected readonly closeLabel = $localize`:@@components.modal.close:Close`;

    /** The tab labels — the four legacy tab names (LDG-19). */
    private readonly labels: Record<ModelBrowserTab, string> = {
        browse: $localize`:@@modelview2.modelBrowser.modelBrowserBrowse:Browse`,
        model: $localize`:@@modelview2.modelBrowser.modelBrowserModel:Model`,
        selection: $localize`:@@modelview2.modelBrowser.modelBrowserSelection:Selection`,
        view: $localize`:@@modelview2.modelBrowser.modelBrowserView:View`,
    };

    /** The visible tabs in legacy order, minus those whose condition fails (LDG-19). */
    protected readonly visibleTabs = computed(() => {
        const hasSelection = this.selection() !== null && this.selection() !== "";
        const hasView = this.activeViewId() !== null;
        return (["browse", "model", "selection", "view"] as const)
            .filter((id) => (id === "selection" ? hasSelection : id === "view" ? hasView : true))
            .map((id) => ({ id, label: this.labels[id] }));
    });

    protected readonly selectedEntity = computed(() => {
        const selected = this.selection();
        return selected === null || selected === "" ? null : (this.entities().get(selected) ?? null);
    });

    protected readonly elementEntities = computed(() => this.entityList("element"));

    protected readonly relationEntities = computed(() => this.entityList("relation"));

    protected readonly viewEntities = computed(() => this.entityList("view"));

    protected readonly activeViewEntity = computed(() => {
        const id = this.activeViewId();
        const entity = id === null ? undefined : this.entities().get(id);
        return entity?.kind === "view" ? entity : null;
    });

    /** The drawer element — the toolbar's open seam focuses it. The ref
        sits on the drawer component's host, so it must be read as the
        element (an unresolved component-host query yields the instance). */
    private readonly drawerRef = viewChild.required("drawer", { read: ElementRef });

    /**
     * Open the panel (the legacy's `openBrowser`, called by 7.22d's toolbar
     * Browse). Focus moves in so the tab strip is one Tab away.
     */
    open(): void {
        this.drawerRef().nativeElement.focus();
        this.active.set(true);
    }

    /**
     * Open on the View tab (the legacy's `openViewInfo`: `selectTab('view')`
     * then `openBrowser()`) — the toolbar's View-info button.
     */
    showView(): void {
        this.selectTab("view");
        this.open();
    }

    /** The legacy's `selectTab`: the switch remembers where the reader was. */
    protected selectTab(id: ModelBrowserTab): void {
        if (this.currentTab() !== id) {
            this.previousTab = this.currentTab();
            this.currentTab.set(id);
        }
    }

    /** Choosing a view closes the panel and re-draws (the legacy's rule). */
    protected onViewChosen(id: string): void {
        this.active.set(false);
        this.viewChosen.emit(id);
    }

    private entityList(kind: LineageEntity["kind"]): LineageEntity[] {
        return [...this.entities().values()].filter((entity) => entity.kind === kind);
    }
}
