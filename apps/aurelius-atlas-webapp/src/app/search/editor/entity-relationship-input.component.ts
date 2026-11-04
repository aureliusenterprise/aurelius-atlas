import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal } from "@angular/core";
import { Subscription } from "rxjs";
import { SearchService, type AtlasEntityHeader } from "aurelius-atlas-data-access";
import { ClassificationChip } from "aurelius-atlas-ui";

import { type RelationshipField, type RelationshipPick, relationshipEntry } from "./form-fields";

/** A suggestion row: the found entity, the label, and whether it is pickable. */
type SuggestionRow = { entity: AtlasEntityHeader; label: string; disabled: boolean };

/**
 * One relationship-attribute picker (EDT-14, DD-339): the classification box's
 * anatomy (DD-335/DD-336) around a live `searchUsingAttribute` round trip —
 * the stock dashboard's own contract for these pickers (`typeName`, `attrName`
 * "name", `attrValuePrefix`, `limit` 10, a 250 ms debounce). An empty focused
 * box browses up to five candidates of the target type instead (DD-343), so
 * the picker suggests before anything is typed. The chosen entities ride
 * inside the box as chips (the chip lead is the entity's own `typeName` in the
 * term chip's `is-info`, DD-341); a `SINGLE` picker hides the input while it
 * holds one chip (the change is a delete, then a pick).
 *
 * The component lives in the webapp, not the ui library, because its whole
 * job is data-access wiring (DD-341 — the ui library is the dumb-component
 * contract of 7.2 and never injects an HTTP client). The editor holds the
 * value: `selected` seeds and replaces the chips, `changed` carries the full
 * new list on every pick or removal.
 */
@Component({
    imports: [ClassificationChip],
    selector: "aurelius-atlas-webapp-entity-relationship-input",
    templateUrl: "./entity-relationship-input.component.html",
    styleUrl: "./entity-relationship-input.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityRelationshipInput {
    /** The field this picker edits (EDT-13's descriptor). */
    readonly field = input.required<RelationshipField>();

    /** The edited entity's guid — never a suggestion of its own picker (EDT-14). */
    readonly editedGuid = input("");

    /** Whether the control shows its required error (EDT-17). */
    readonly invalid = input(false);

    /** The accessible name of the combobox input (the field label). */
    readonly label = input("");

    /** The chip delete's accessible name (the catalogue string, EDT-17). */
    readonly deleteLabel = input("Delete");

    /** The picker's value (EDT-15's seed; the editor holds it, EDT-16 reads it). */
    readonly selected = input<readonly RelationshipPick[]>([]);

    /** The full new value on every pick or removal (EDT-14). */
    readonly changed = output<readonly RelationshipPick[]>();

    private readonly search = inject(SearchService);

    /** The typed text — the input is a plain control; the picker holds no form. */
    private readonly text = signal("");

    /** Whether the box holds focus — the panel opens for the box (DD-335). */
    private readonly focused = signal(false);

    /** Whether the panel is open for the current typing run (DD-335). */
    private readonly panelOpen = signal(true);

    /** The keyboard-active option (DD-336): first row until Down/Up move it. */
    private readonly activeRow = signal(0);

    /** The found entities awaiting the exclusions (the raw search answer). */
    private readonly found = signal<readonly AtlasEntityHeader[]>([]);

    /** The in-flight search (a new keystroke drops it — last typed text wins). */
    private pending: Subscription | null = null;

    /** The debounce timer (250 ms, the stock select2's delay — DD-339). */
    private timer: ReturnType<typeof setTimeout> | null = null;

    /** A pickable suggestion carries a guid (the entry the save writes). */
    private static pickable(entity: AtlasEntityHeader): boolean {
        return typeof entity.guid === "string" && entity.guid !== "";
    }

    /** The chips' display labels — the value keeps the raw fields (EDT-15). */
    protected readonly chips = computed(() =>
        this.selected().map((pick) => ({
            key: pick.guid,
            label: pick.displayText ?? pick.qualifiedName ?? pick.guid,
            lead: pick.typeName ?? "",
        })),
    );

    /** Whether the picker is full: a SINGLE field with one chip hides the input (EDT-14). */
    protected readonly singleFull = computed(() => this.field().single && this.selected().length >= 1);

    /** The chosen guids plus the edited entity — the panel drops all of them (EDT-14). */
    private readonly excluded = computed(() => {
        const ids = new Set<string>(this.selected().map((pick) => pick.guid));
        const edited = this.editedGuid();
        if (edited !== "") {
            ids.add(edited);
        }
        return ids;
    });

    /** The panel rows (EDT-14): the found entities minus the excluded, and a
     * found entity without a guid — nothing to attach — sits disabled. */
    protected readonly suggestions = computed<SuggestionRow[]>(() => {
        const excluded = this.excluded();

        return this.found()
            .filter((entity) => !(typeof entity.guid === "string" && excluded.has(entity.guid)))
            .map((entity) => ({
                entity,
                label: entity.displayText ?? entity.guid ?? "",
                disabled: !EntityRelationshipInput.pickable(entity),
            }));
    });

    /** Whether the panel shows (EDT-14, DD-335): focused, open, and rows to show. */
    protected readonly panelShown = computed(
        () => this.focused() && this.panelOpen() && !this.singleFull() && this.suggestions().length > 0,
    );

    /** The active row's id, for the combobox's aria-activedescendant (DD-336). */
    protected readonly activeRowId = computed(() =>
        this.panelShown() ? `${this.listboxId()}-option-${this.activeRow()}` : null,
    );

    /** The ids the combobox wiring (DD-336) names — unique per field. */
    protected readonly labelId = computed(() => `editor-relationship-${this.field().name}-label`);

    protected readonly listboxId = computed(() => `editor-relationship-${this.field().name}-listbox`);

    protected readonly inputId = computed(() => `editor-relationship-${this.field().name}-input`);

    constructor() {
        // The active row re-clamps as the answer changes (DD-336's rule).
        effect(() => {
            const count = this.suggestions().length;
            if (count > 0 && this.activeRow() >= count) {
                this.activeRow.set(0);
            }
        });
    }

    /** The placeholder by cardinality (EDT-17's catalogue keys). */
    protected readonly placeholder = $localize`:@@search.components.editor.components.relationshipsInput.addPlaceholder:Add a relationship...`;

    protected readonly singlePlaceholder = $localize`:@@search.components.editor.components.relationshipsInput.selectPlaceholder:Select a relationship...`;

    /** The input's `input` event → the typed text (EDT-14). */
    protected onTypedEvent(event: Event): void {
        this.onTyped((event.target as HTMLInputElement).value);
    }

    /** Typing (EDT-14): non-empty text searches with the typed prefix; empty
     * or whitespace-only text is the browse (DD-343). */
    private onTyped(value: string): void {
        this.text.set(value);
        this.searchFor(value.trim());
    }

    /** One debounced round trip (EDT-14, DD-343): 250 ms, the stock select2's
     * delay; an empty prefix browses the target type (limit 5), typed text
     * searches it (limit 10, the stock contract). A pending timer or request
     * is dropped — the latest intent wins. */
    private searchFor(prefix: string): void {
        if (this.timer !== null) {
            clearTimeout(this.timer);
            this.timer = null;
        }
        this.pending?.unsubscribe();
        this.pending = null;
        this.timer = setTimeout(() => {
            this.timer = null;
            this.pending = this.search
                .searchUsingAttribute({
                    typeName: this.field().targetType,
                    attrName: "name",
                    attrValuePrefix: prefix,
                    limit: prefix === "" ? 5 : 10,
                })
                .subscribe({
                    next: (answer) => {
                        this.pending = null;
                        this.found.set(answer.entities ?? []);
                        this.activeRow.set(0);
                    },
                    error: () => {
                        // A failed search leaves the panel as it was (EDT-14):
                        // the field alerts nothing — typing continues.
                        this.pending = null;
                        this.found.set([]);
                    },
                });
        }, 250);
    }

    /** The box gained focus (DD-335): the panel opens for the box, and an
     * empty box browses up to five candidates (DD-343). Moves within the box
     * (chip → its delete button) do not re-browse — one list per entry. */
    protected onBoxFocusIn(): void {
        const entering = !this.focused();
        this.focused.set(true);
        this.panelOpen.set(true);
        this.activeRow.set(0);
        if (entering && this.text().trim() === "") {
            this.searchFor("");
        }
    }

    /** Focus left the box (DD-335): the panel closes; a tab into it keeps it open. */
    protected onBoxFocusOut(event: FocusEvent): void {
        const next = event.relatedTarget as Node | null;
        if (next !== null && (event.currentTarget as Node).contains(next)) {
            return;
        }
        this.focused.set(false);
    }

    /** Escape inside the box (DD-335): close the panel only, keep the text. */
    protected onEscape(event: Event): void {
        if (!this.panelShown()) {
            return;
        }
        event.stopPropagation();
        this.panelOpen.set(false);
    }

    /** Down/Up move the active row (DD-336): the input keeps focus. */
    protected onRowKeys(event: KeyboardEvent): void {
        if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
            return;
        }
        event.preventDefault();
        const count = this.suggestions().length;
        if (count === 0) {
            return;
        }
        this.panelOpen.set(true);
        const step = event.key === "ArrowDown" ? 1 : -1;
        const from = this.panelShown() ? this.activeRow() : step === 1 ? -1 : count;
        this.activeRow.set((from + step + count) % count);
    }

    /** Enter commits the active row (DD-336); with the panel shut, nothing. */
    protected onEnter(): void {
        if (!this.panelShown()) {
            return;
        }
        const row = this.suggestions()[this.activeRow()];
        if (row !== undefined && !row.disabled) {
            this.pick(row.entity);
        }
    }

    /** A panel click commits (mousedown — the click never lands, DD-335). */
    protected onRowMousedown(event: MouseEvent, row: SuggestionRow): void {
        event.preventDefault();
        if (!row.disabled) {
            this.pick(row.entity);
        }
    }

    /** Commit a pick (EDT-14): append it, clear the input, keep focus in the box. */
    private pick(entity: AtlasEntityHeader): void {
        const entry = relationshipEntry(entity);
        if (entry === null) {
            return;
        }
        const current = this.selected();
        this.changed.emit(current.some((pick) => pick.guid === entry.guid) ? current : [...current, entry]);
        this.text.set("");
        this.found.set([]);
        this.activeRow.set(0);
    }

    /** A chip's delete (EDT-14/UIC-24): the picker answers the full new list. */
    protected removeAt(index: number): void {
        this.changed.emit(this.selected().filter((_, at) => at !== index));
    }

    /** Whether a panel row is the keyboard-active one (DD-336). */
    protected isActive(index: number): boolean {
        return this.panelShown() && index === this.activeRow();
    }

    /** The current text, for the input's value binding. */
    protected typedText(): string {
        return this.text();
    }
}
