import { ChangeDetectionStrategy, Component, computed, effect, input, output, signal } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { type IconDefinition } from "@fortawesome/free-solid-svg-icons";

import { Breadcrumbs, type Breadcrumb } from "../breadcrumbs/breadcrumbs.component";
import { ClassificationChip } from "../classification-chip/classification-chip.component";
import { TypeName } from "../type-name/type-name.component";

/** One chosen token: a chip inside the box. */
export interface TokenChip {
    /** The chip's identity — the row's key. */
    key: string;
    /** The chip's label. */
    label: string;
    /** The lead tag's word, as the term chip's lead (DD-189). Unset draws the
     * classification chip's hashtag glyph instead. */
    leadLabel?: string;
}

/** One suggestion row. Every field is a finished string or icon: the picker
 * resolves nothing, which is what makes it usable outside an Atlas app. */
export interface TokenRow {
    /** The row's identity — the payload of `picked` and the panel's track key. */
    key: string;
    /** The row's name — the first line's text. */
    name: string;
    /** The type badge's text. Unset draws no badge. */
    type?: string;
    /** The type badge's icon. */
    icon?: IconDefinition;
    /** The type badge's colour class (`business`, `technical`, …). */
    iconClass?: string;
    /** The trail under the name: the stored crumbs, oldest first, as the
     * Breadcrumbs component takes them — printed plain, never as links, since
     * the row itself is the option's one action (DD-714). Unset or empty draws
     * no trail. */
    trail?: readonly Breadcrumb[];
}

/**
 * The chip-and-suggest control: a bordered box carrying the chosen tokens as
 * deletable chips, a borderless text input beside them, and a panel of rows
 * that opens while the box holds focus (UIC-44, DD-713). It is the
 * classification box's anatomy (DD-335/DD-336) turned into a component, so
 * the editor's two pickers share one shape instead of one copy each.
 *
 * Everything it shows arrives as an input, and every intent leaves as an
 * output: the caller answers `typed` with rows and sets `selected` to what
 * was chosen, which is where the search, the debounce, the exclusions and the
 * value live. The picker owns only what a text box and its panel own — focus,
 * the open panel, the keyboard-active row, Escape, and the panel's ARIA
 * combobox wiring (DD-336).
 *
 * A `single` box hides its input once it holds one chip: the change is a
 * delete, then a pick. Chrome strings (placeholders, the delete and listbox
 * names) are caller-supplied inputs (DD-136).
 */
@Component({
    imports: [Breadcrumbs, ClassificationChip, FontAwesomeModule, TypeName],
    selector: "aurelius-atlas-ui-token-picker",
    templateUrl: "./token-picker.component.html",
    styleUrl: "./token-picker.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TokenPicker {
    /** The chips the box holds, in order. */
    readonly selected = input<readonly TokenChip[]>([]);

    /** The rows the panel shows, in order. Empty keeps the panel shut. */
    readonly rows = input<readonly TokenRow[]>([]);

    /** Whether the box holds one token only — a full single box hides its input. */
    readonly single = input(false);

    /** Paint the box `is-danger` and mark the input invalid (the caller's rule). */
    readonly invalid = input(false);

    /** The text in the input, caller-held so it survives a re-render. */
    readonly text = input("");

    /** The accessible name of the input. */
    readonly label = input("");

    /** The placeholder while more tokens may be added. The caller localises it. */
    readonly placeholder = input("");

    /** The placeholder of a single box with nothing chosen. The caller localises it. */
    readonly singlePlaceholder = input("");

    /** The delete button's accessible name. The caller localises it. */
    readonly deleteLabel = input("Delete");

    /** The id of the element naming the control, for the input's labelledby. */
    readonly labelId = input<string | undefined>(undefined);

    /** The id of the error line under the box, named while `invalid` shows. */
    readonly errorId = input<string | undefined>(undefined);

    /** The prefix the picker numbers its ids with. Unique per control on a page. */
    readonly idBase = input("token-picker");

    /** Emits the row a pick chose (a click, or Enter on the active row). */
    readonly picked = output<TokenRow>();

    /** Emits the chip whose delete was clicked. */
    readonly removed = output<TokenChip>();

    /** Emits the input's new text on every keystroke. */
    readonly typed = output<string>();

    /** Emits when focus moves into the box from outside it. The caller uses it
     * to offer suggestions before anything is typed; moves within the box
     * (chip → its delete button) never emit it. */
    readonly entered = output<void>();

    /** Whether the box holds focus — the panel opens for the box (DD-335). */
    private readonly focused = signal(false);

    /** Whether the panel is open for the current typing run (DD-335). */
    private readonly panelOpen = signal(true);

    /** The keyboard-active row (DD-336): first row until Down/Up move it. */
    private readonly activeRow = signal(0);

    /** The picker's element ids — the combobox wiring names them. */
    protected readonly listboxId = computed(() => `${this.idBase()}-listbox`);

    protected readonly inputId = computed(() => `${this.idBase()}-input`);

    /** The active row's id, for the combobox's aria-activedescendant (DD-336). */
    protected readonly activeRowId = computed(() =>
        this.panelShown() ? `${this.listboxId()}-option-${this.activeRow()}` : null,
    );

    /** Whether the single box is full: its input hides (the change is delete, then pick). */
    protected readonly singleFull = computed(() => this.single() && this.selected().length >= 1);

    /** Whether the panel shows (DD-335): focused, open, and rows to show. */
    protected readonly panelShown = computed(() => this.focused() && this.panelOpen() && this.rows().length > 0);

    /** The placeholder the input shows, by cardinality and fullness. */
    protected readonly shownPlaceholder = computed(() =>
        this.single() && !this.singleFull() ? this.singlePlaceholder() : this.placeholder(),
    );

    constructor() {
        // The highlight returns to the first row whenever the rows change: a
        // new list makes the old active row meaningless, and it can no longer
        // point inside the list at all (DD-336).
        effect(() => {
            this.rows();
            this.activeRow.set(0);
        });
    }

    /** The box gained focus (DD-335): the panel opens for the box. Moves within
     * the box (chip → its delete button) do not re-open anything, and do not
     * emit `entered` either — one list per entry. */
    protected onBoxFocusIn(): void {
        const entering = !this.focused();
        this.focused.set(true);
        this.panelOpen.set(true);
        this.activeRow.set(0);
        if (entering) {
            this.entered.emit();
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
        const count = this.rows().length;
        if (count === 0) {
            return;
        }
        this.panelOpen.set(true);
        const step = event.key === "ArrowDown" ? 1 : -1;
        // A shut panel starts from just before the first row (going down) or
        // just past the last (going up), so the first keypress lands on the
        // near end (DD-336).
        const closedStart = step === 1 ? -1 : count;
        const from = this.panelShown() ? this.activeRow() : closedStart;
        this.activeRow.set((from + step + count) % count);
    }

    /** Enter commits the active row (DD-336); with the panel shut, nothing. */
    protected onEnter(): void {
        if (!this.panelShown()) {
            return;
        }
        const row = this.rows()[this.activeRow()];
        if (row !== undefined) {
            this.picked.emit(row);
        }
    }

    /** The input's `input` event → `typed`. */
    protected onTypedEvent(event: Event): void {
        this.typed.emit((event.target as HTMLInputElement).value);
    }

    /** A panel click commits (mousedown — the click never lands, DD-335). */
    protected onRowMousedown(event: MouseEvent, row: TokenRow): void {
        event.preventDefault();
        this.picked.emit(row);
    }

    /** A chip's delete (UIC-24): the caller answers the removal. */
    protected onChipRemove(chip: TokenChip): void {
        this.removed.emit(chip);
    }

    /** Whether a panel row is the keyboard-active one (DD-336). */
    protected isActive(index: number): boolean {
        return this.panelShown() && index === this.activeRow();
    }
}
