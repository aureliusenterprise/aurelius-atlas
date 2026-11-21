import { ChangeDetectionStrategy, Component, computed, effect, input, output, signal } from "@angular/core";

import { ClassificationChip } from "aurelius-atlas-ui";

import { nameDisplay } from "../meta/type-display";

/**
 * The classification box (EDT-05, DD-335, DD-336) as its own component
 * (WFE-03, DD-804): one bordered box holding the chosen chips and the text
 * input, with the applicable types riding a full-width panel above it. The
 * editor owns the chosen set — the box emits `added`/`removed` and the store
 * turns them into the door's one `classifications` body (VDE-03) — and the
 * box owns the typing, the filtering, the keyboard, and the panel.
 *
 * The box is a Bulma dropdown: while it holds focus, the applicable types
 * that match the text ride the panel (the box is the form's last field, so
 * the panel opens upward — Bulma's is-up; the menu's stretch to the box's
 * width is the component's own rule, DD-335). Typed-or-clicked in: clicks
 * commit through mousedown, before the input's blur closes the panel
 * (DD-335 — the pointer path the native datalist took before). The input is
 * the ARIA 1.2 combobox (DD-336): the label names it, Down/Up move the
 * active option (aria-activedescendant), Enter commits it; with nothing
 * applicable left the input disables and says so through the help line, so
 * the box cannot invite typing that matches nothing.
 *
 * Names ride in and out raw (EDT-16): the dictionary display name shows on
 * the chips and the rows (DD-379), and never leaves the template.
 */
@Component({
    imports: [ClassificationChip],
    selector: "aurelius-atlas-webapp-classification-combobox",
    templateUrl: "./classification-combobox.component.html",
    styleUrl: "./classification-combobox.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClassificationCombobox {
    /** The applicable type names the box offers (the chosen ones excluded). */
    readonly suggestions = input<readonly string[]>([]);

    /** The chosen type names, in the store's order. */
    readonly chosen = input<readonly string[]>([]);

    /** Chip tooltips by name — the classification defs' descriptions (UIC-16). */
    readonly tooltips = input<Readonly<Record<string, string | undefined>>>({});

    /** The chip delete's accessible name (the catalogue string, EDT-05). */
    readonly deleteLabel = input("Delete");

    /** A type the person chose (a pick, Enter, or the exact typed name). */
    readonly added = output<string>();

    /** A chip's delete (UIC-24): the tag rides back to the store. */
    readonly removed = output<string>();

    /** The tag box's typed text (EDT-05): typing filters, Enter adds. The
     * box is not a form field — the tags ride the store, not the model —
     * so it is a plain signal, not a control (DD-354). */
    protected readonly classificationText = signal("");

    /** Whether the box holds focus (EDT-05, DD-335). */
    private readonly boxFocused = signal(false);

    /** Whether the panel is open for the current typing run (EDT-05,
     * DD-335): Escape closes it, the next typed character opens it again. */
    private readonly suggestionsOpen = signal(true);

    /** The chosen names the row renders (a stray empty name shows no chip). */
    protected readonly chosenTags = computed(() => this.chosen().filter((name) => name !== ""));

    /** The suggestions the typed text filters (EDT-05, DD-335): a match
     * that starts with the text leads, so Enter (which adds the active
     * option, DD-336) commits the closest name — the old exact-else-first
     * rule kept in the panel order. */
    protected readonly filteredSuggestions = computed(() => {
        const typed = this.classificationText().trim().toLowerCase();
        if (typed === "") {
            return [...this.suggestions()];
        }
        const matches = this.suggestions().filter((name) => name.toLowerCase().includes(typed));

        return [
            ...matches.filter((name) => name.toLowerCase().startsWith(typed)),
            ...matches.filter((name) => !name.toLowerCase().startsWith(typed)),
        ];
    });

    /** Whether the suggestion panel shows (EDT-05, DD-335). */
    protected readonly dropdownShown = computed(
        () => this.boxFocused() && this.suggestionsOpen() && this.filteredSuggestions().length > 0,
    );

    /** The keyboard-active option (DD-336): the panel's first row until
     * Down/Up move it; re-clamped as the filter narrows. */
    private readonly activeSuggestion = signal(0);

    /** The active option's id, for the combobox's aria-activedescendant. */
    protected readonly activeSuggestionId = computed(() =>
        this.dropdownShown() ? `editor-classification-option-${this.activeSuggestion()}` : null,
    );

    /** Whether the box has nothing to offer (DD-336): with no applicable
     * type left to add, the input disables — typing could only match
     * nothing. Chosen tags keep their delete (they ride the chips, not
     * this control), so the field can still hand a tag back. */
    protected readonly classificationDisabled = computed(() => this.suggestions().length === 0);

    /** Whether the "no classifications" help line shows (DD-336): the
     * field explains its disabled state, so a dead input is not a puzzle. */
    protected readonly helpLineShown = computed(() => this.suggestions().length === 0);

    protected readonly classificationsLabel = $localize`:@@search.components.editor.attribute.classifications:Classifications`;

    protected readonly classificationsPlaceholder = $localize`:@@search.components.editor.components.classificationsInput.addPlaceholder:Add a classification...`;

    protected readonly noClassifications = $localize`:@@search.components.editor.components.classificationsInput.noClassificationsAvailable:No classifications available`;

    constructor() {
        // The active option re-clamps as the filter narrows (DD-336): a
        // typed prefix can shrink the list under the current index.
        effect(() => {
            const count = this.filteredSuggestions().length;
            if (count > 0 && this.activeSuggestion() >= count) {
                this.activeSuggestion.set(0);
            }
        });
    }

    /** A type or classification name's display name (EDT-05, DD-379): the
     * legacy `name | translate` — the dictionary display name, raw for a
     * name the dictionary never saw. The values stored and sent keep the
     * raw name (EDT-16). */
    protected display(name: string): string {
        return nameDisplay(name);
    }

    /** Enter (the keyup path): the active option when the panel shows, the
     * exact typed name when it does not (DD-336 keeps exact-name Enter
     * working with the panel shut). Anything else keeps its text. */
    protected addClassification(): void {
        if (this.dropdownShown()) {
            const name = this.filteredSuggestions()[this.activeSuggestion()];
            if (name !== undefined) {
                this.addNamed(name);
            }

            return;
        }
        const typed = this.classificationText().trim();

        if (typed !== "" && this.suggestions().includes(typed)) {
            this.addNamed(typed);
        }
    }

    /** The box gained focus (EDT-05, DD-335): the panel opens for the box. */
    protected onBoxFocusIn(): void {
        this.boxFocused.set(true);
        this.suggestionsOpen.set(true);
        this.activeSuggestion.set(0);
    }

    /** Focus left the box (EDT-05, DD-335): the panel closes. Moving into
     * the panel itself (a keyboard tab) keeps the box focused. */
    protected onBoxFocusOut(event: FocusEvent): void {
        const next = event.relatedTarget as Node | null;
        if (next !== null && (event.currentTarget as Node).contains(next)) {
            return;
        }
        this.boxFocused.set(false);
    }

    /** Pick a suggestion from the panel (EDT-05, DD-335). The click lands
     * on mousedown, before the input's blur closes the panel — the pointer
     * path the native datalist took before (DD-329's note retired here). */
    protected pickSuggestion(event: MouseEvent, name: string): void {
        event.preventDefault();
        this.addNamed(name);
    }

    /**
     * Down/Up move the combobox's active option (DD-336) — the panel is
     * the listbox, the input keeps focus and carries
     * `aria-activedescendant`; Enter (the keyup path above) adds the
     * active option. A closed panel (typed text matching nothing, or a
     * fresh focus) falls through to the old Enter rule (DD-336 keeps
     * exact-name Enter working with the panel shut).
     */
    protected onSuggestionKeys(event: KeyboardEvent): void {
        if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
            return;
        }
        event.preventDefault();
        const count = this.filteredSuggestions().length;
        if (count === 0) {
            return;
        }
        this.suggestionsOpen.set(true);
        const step = event.key === "ArrowDown" ? 1 : -1;
        // A shut panel starts from just before the first row (going down) or
        // just past the last (going up), so the first keypress lands on the
        // near end (DD-336).
        const closedStart = step === 1 ? -1 : count;
        const from = this.dropdownShown() ? this.activeSuggestion() : closedStart;
        const next = (from + step + count) % count;
        this.activeSuggestion.set(next);
    }

    /** Escape inside the box (EDT-05, DD-335): close the panel, keep the
     * drawer open — the panel is the innermost layer, like a menu. */
    protected onSuggestionEscape(event: Event): void {
        if (!this.dropdownShown()) {
            return;
        }
        event.stopPropagation();
        this.suggestionsOpen.set(false);
    }

    /** Add a named tag and clear the input (the pick and Enter path). */
    private addNamed(name: string): void {
        this.added.emit(name);
        this.classificationText.set("");
    }
}
