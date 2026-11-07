import { ChangeDetectionStrategy, Component, computed, input, output, signal } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faChevronDown, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { Select } from "aurelius-atlas-ui";

import type { Ar3Organization } from "./parse-ar3";
import type { LineageEntity } from "./lineage-entities";

/** A dropdown row: a view of the model, keyed by id (the ui Select's row). */
type ViewRow = { id: string; name: string; [key: string]: unknown };

/** One visible tree row: a flattened organization node (DD-406). */
type TreeRow = {
    /** The row's path key — the fold toggle's identity. */
    readonly key: string;
    /** The nesting depth — the indent, in em. */
    readonly depth: number;
    /** A folder: renders the toggle; a leaf renders the anchor. */
    readonly folder: boolean;
    /** The text to show: the folder label, or the concept's name. */
    readonly label: string;
    /** A leaf's concept id; null for a folder. */
    readonly conceptId: string | null;
};

/**
 * The Browse tab (LDG-23, DD-406): the legacy `model-browser/browse`
 * component — the view dropdown plus the organization navigation tree. The
 * 7.22c port left the tree out (DD-395: one dropdown reaches the one view);
 * the feedback round brought it back — the tree is how a future model with
 * several diagrams or folders stays navigable, and the legacy's `modelTree`
 * reads as one anyway on the shipped chain (Other / Relations / Views).
 *
 * The dropdown keeps its settings-panel shape (the plain Select, searchVisible
 * off): the drawn view reads back as the control's value (the legacy's
 * `viewId` → control sync) and choosing a row emits it — the viewer re-draws
 * and the panel closes (LDG-25).
 *
 * The tree renders the parsed `ar3_organizations` (folders and `@identifierRef`
 * leaves), each folder openable with a chevron and open by default — the
 * legacy's own default. An unlabeled container (the producer's single root)
 * renders no row of its own: its children sit at the top, as the legacy's
 * tree did. A leaf shows its entity's name (falling back to the id) and marks
 * the current selection; clicking it selects the concept (LDG-25's drawer-side
 * rule) or, for a view, chooses it — draw and close (LDG-23's rule).
 */
@Component({
    selector: "aurelius-atlas-webapp-lineage-browse-tab",
    changeDetection: ChangeDetectionStrategy.OnPush,
    imports: [FontAwesomeModule, Select],
    template: `
        <div class="field aurelius-browse-view-select">
            <aurelius-atlas-ui-select
                [options]="viewRows()"
                displayField="name"
                [value]="selectedRow()"
                [label]="label"
                [nullInputMessage]="nullMessage"
                [noDataMessage]="noDataMessage"
                [searchVisible]="false"
                (valueChange)="onPicked($event)"
            ></aurelius-atlas-ui-select>
        </div>
        @if (treeRows().length > 0) {
            <p class="label aurelius-browse-tree-label">{{ treeLabel }}</p>
            <ul class="aurelius-browse-tree" role="tree">
                @for (row of treeRows(); track row.key) {
                    <li role="treeitem" [attr.aria-selected]="row.conceptId === selectedConcept()">
                        @if (row.folder) {
                            <button
                                type="button"
                                class="aurelius-browse-tree-folder"
                                [style.padding-left.em]="0.5 + row.depth * 1.25"
                                [attr.aria-expanded]="!collapsed().has(row.key)"
                                (click)="toggle(row.key)"
                            >
                                <span class="icon is-small" aria-hidden="true">
                                    <fa-icon
                                        [icon]="collapsed().has(row.key) ? faChevronRight : faChevronDown"
                                    ></fa-icon>
                                </span>
                                <span>{{ row.label }}</span>
                            </button>
                        } @else {
                            <button
                                type="button"
                                class="aurelius-browse-tree-leaf"
                                [class.is-active]="row.conceptId === selectedConcept()"
                                [style.padding-left.em]="1.75 + row.depth * 1.25"
                                [title]="row.label"
                                (click)="onLeafClicked(row)"
                            >
                                {{ row.label }}
                            </button>
                        }
                    </li>
                }
            </ul>
        }
    `,
    styles: `
        .aurelius-browse-tree {
            list-style: none;
            margin: 0;
            padding: 0;
        }
        .aurelius-browse-tree li {
            margin: 0;
        }
        .aurelius-browse-tree-folder,
        .aurelius-browse-tree-leaf {
            align-items: center;
            background: none;
            border: none;
            border-radius: 4px;
            color: inherit;
            cursor: pointer;
            display: flex;
            font-size: 0.9em;
            gap: 0.35em;
            max-width: 100%;
            padding-block: 0.15rem;
            text-align: left;
            width: 100%;
        }
        .aurelius-browse-tree-folder {
            font-weight: 600;
        }
        .aurelius-browse-tree-folder:hover,
        .aurelius-browse-tree-leaf:hover {
            background: hsla(0, 0%, 86%, 0.35);
        }
        .aurelius-browse-tree-leaf {
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .aurelius-browse-tree-leaf.is-active {
            background: hsl(171, 100%, 41%, 0.18);
            font-weight: 600;
        }
    `,
})
export class LineageBrowseTab {
    /** The model's view entities, in document order. */
    readonly views = input<LineageEntity[]>([]);

    /** Every entity record — the tree's leaf labels and kinds (DD-406). */
    readonly entities = input<ReadonlyMap<string, LineageEntity>>(new Map());

    /** The parsed organization tree's roots (DD-406). */
    readonly organizations = input<readonly Ar3Organization[]>([]);

    /** The drawn view id (the legacy's `viewId`, one-way into the control). */
    readonly drawnViewId = input<string | null>(null);

    /** The selected concept — the tree's active leaf. */
    readonly selectedConcept = input<string | null>(null);

    /** A row was chosen: the viewer draws it (LDG-23/LDG-25). */
    readonly viewChosen = output<string>();

    /** A non-view leaf was clicked: select that concept (LDG-25). */
    readonly conceptChosen = output<string>();

    protected readonly label = $localize`:@@modelview2.modelBrowser.browse.viewSelect.label:View`;
    protected readonly nullMessage = $localize`:@@modelview2.modelBrowser.browse.viewSelect.nullInputMessage:No view selected`;
    protected readonly noDataMessage = $localize`:@@modelview2.modelBrowser.browse.viewSelect.noDataMessage:No views available`;
    protected readonly treeLabel = $localize`:@@modelview2.modelBrowser.browse.modelTree:Model tree`;

    protected readonly faChevronRight = faChevronRight;
    protected readonly faChevronDown = faChevronDown;

    /** The folders the reader closed — open by default, the legacy's state. */
    protected readonly collapsed = signal<ReadonlySet<string>>(new Set());

    /** The dropdown rows (the legacy's displayField 'name'). */
    protected readonly viewRows = computed<ViewRow[]>(() =>
        this.views().map((view) => ({ id: view.id, name: view.name })),
    );

    /**
     * The control's row: the drawn view's row, or null for the placeholder.
     * The object identity must be stable across change detection or the
     * select's strict-equality compare loses the value (DD-155) — so the row
     * comes from `viewRows()`, computed once per model, not rebuilt here.
     */
    protected readonly selectedRow = computed(() => {
        const drawn = this.drawnViewId();
        return drawn === null ? null : (this.viewRows().find((row) => row.id === drawn) ?? null);
    });

    /**
     * The visible tree rows: the organization depth-first, a closed folder's
     * whole branch dropped, an unlabeled container replaced by its children,
     * and a leaf labelled through the entity index (the id when no entity or
     * no name exists for it).
     */
    protected readonly treeRows = computed<TreeRow[]>(() => {
        const rows: TreeRow[] = [];
        const collapsed = this.collapsed();
        const entities = this.entities();
        const walk = (nodes: readonly Ar3Organization[], depth: number, parentKey: string): void => {
            nodes.forEach((node, index) => {
                const key = `${parentKey}/${index}`;
                if (node.ref !== null) {
                    const entity = entities.get(node.ref);
                    rows.push({
                        key,
                        depth,
                        folder: false,
                        label: entity === undefined || entity.name === "" ? node.ref : entity.name,
                        conceptId: node.ref,
                    });
                    return;
                }
                // A folder: the row stays while closed (its chevron is the
                // reopen affordance) — only the branch below it disappears.
                const shown = node.label !== "";
                if (shown) {
                    rows.push({ key, depth, folder: true, label: node.label, conceptId: null });
                }
                if (collapsed.has(key)) {
                    return;
                }
                // An unlabeled container (the producer's root) shows no row —
                // its children sit at this depth, like the legacy's tree.
                walk(node.children, shown ? depth + 1 : depth, key);
            });
        };
        walk(this.organizations(), 0, "");
        return rows;
    });

    protected toggle(key: string): void {
        this.collapsed.update((current) => {
            const next = new Set(current);
            if (next.has(key)) {
                next.delete(key);
            } else {
                next.add(key);
            }
            return next;
        });
    }

    /** A leaf click: a view draws (LDG-23's rule), anything else selects (LDG-25). */
    protected onLeafClicked(row: TreeRow): void {
        const id = row.conceptId;
        if (id === null) {
            return;
        }
        if (this.entities().get(id)?.kind === "view") {
            this.viewChosen.emit(id);
        } else {
            this.conceptChosen.emit(id);
        }
    }

    protected onPicked(row: ViewRow | null): void {
        if (row !== null) {
            this.viewChosen.emit(row.id);
        }
    }
}
