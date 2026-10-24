import { CommonModule, DatePipe } from "@angular/common";
import { ChangeDetectionStrategy, Component, computed, inject, input, model, output } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faSearch, type IconDefinition } from "@fortawesome/free-solid-svg-icons";

/** The next select's element-id suffix (label/control pairing, UIC-14). */
let nextSelectId = 0;

/**
 * The legacy Aurelius select field (`models4insight-select`), ported without
 * its reactive form, the `ControlShell` wrapper, or the embedded
 * `SearchModalComponent` (DD-155): the value lives in a `model()`, the shell
 * markup (label, addons, required help) is inlined, and the search button —
 * the Aurelius modal opener — emits `searchRequested` for the app to handle
 * (7.7 wires the repository-fed modal).
 *
 * The legacy `compareWith` default (lodash `isEqual`) becomes strict
 * equality (DD-155): option identity is the option row, so callers pass
 * stable objects. Chrome strings — label, null/no-data messages, required
 * help, search accessible name — are caller-supplied inputs carrying the
 * legacy English defaults (DD-136, UIC-15).
 */
@Component({
    selector: "aurelius-atlas-ui-select",
    imports: [CommonModule, FontAwesomeModule, FormsModule],
    templateUrl: "./select.component.html",
    styleUrl: "./select.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
    providers: [DatePipe],
})
export class Select<T extends Record<string, unknown> = Record<string, unknown>> {
    /**
     * The selected row, two-way bindable; `null` while the placeholder
     * option is active — the legacy control's initial value.
     */
    readonly value = model<T | null>(null);

    /**
     * The rows to choose from. Empty renders the no-data placeholder, as
     * the legacy template's length ternary did.
     */
    readonly options = input<T[]>([]);

    /**
     * The property of a row shown as its option label. Rows without a
     * value for it are skipped, as the legacy `*ngIf="row[displayField]"` did.
     */
    readonly displayField = input<string>("name");

    /**
     * The field's label. The Aurelius default was 'Title'.
     */
    readonly label = input("Title");

    /**
     * The placeholder option's text while rows are available. The Aurelius
     * default was 'Please select a value'.
     */
    readonly nullInputMessage = input("Please select a value");

    /**
     * The placeholder option's text while no rows are available. The
     * Aurelius default was 'No data available'.
     */
    readonly noDataMessage = input("No data available");

    /**
     * The help shown when the field is required and invalid. The Aurelius
     * select's default was 'Please select a value'.
     */
    readonly requiredErrorMessage = input("Please select a value");

    /**
     * Format option labels as timestamps ('dd MMM y, HH:mm:ss'), as the
     * legacy `isTimestamp` context flag did.
     */
    readonly isTimestamp = input(false);

    /**
     * Disable the control, as the legacy `isDisabled` did.
     */
    readonly disabled = input(false);

    /**
     * Paint the control `is-danger` and show the required help — the legacy
     * form's `(dirty || submitted) && invalid` state, projected to an input.
     */
    readonly invalid = input(false);

    /**
     * Whether the search button shows the loading spinner — the legacy
     * modal's `isLoading`. The button is `aria-busy` and inert while set.
     */
    readonly searchLoading = input(false);

    /**
     * Accessible name of the search button. The caller localises it; the
     * Aurelius icon button had none.
     */
    readonly searchLabel = input("Search");

    /**
     * Show the search button — the legacy modal opener, on by default as
     * in Aurelius. Off, the field is a plain labelled dropdown (the
     * settings panel's theme picker, DD-164), and the addons layout
     * collapses with the button.
     */
    readonly searchVisible = input(true);

    /**
     * The field's icon, shown left of the control, as the shell context's
     * `icon` did.
     */
    readonly icon = input<IconDefinition | undefined>(undefined);

    /**
     * Emits when the search button is activated — the legacy
     * `activateSearchModal`, turned into an emit (DD-155).
     */
    readonly searchRequested = output<void>();

    /**
     * The id shared by the label and the control, the legacy
     * `controlLabel`/`aria-labelledby` pair. Angular 22 has no public id
     * generator (`NgId` is 20+), so a module counter pairs the ids.
     */
    protected readonly inputId = `aurelius-atlas-ui-select-${nextSelectId++}`;

    /**
     * The FontAwesome icon used by the search button.
     */
    protected readonly faSearch = faSearch;

    private readonly datePipe = inject(DatePipe);

    /**
     * A row's option label: the display-field value, formatted as a
     * timestamp ('dd MMM y, HH:mm:ss') when `isTimestamp` — the legacy
     * template's date-pipe ternary.
     * @param row The option row.
     * @returns The label text.
     */
    protected displayValue(row: T): string {
        const raw = row[this.displayField()];
        if (this.isTimestamp() && (typeof raw === "string" || typeof raw === "number")) {
            return this.datePipe.transform(raw, "dd MMM y, HH:mm:ss") ?? "";
        }
        if (typeof raw === "string") {
            return raw;
        }
        if (typeof raw === "number" || typeof raw === "boolean") {
            return String(raw);
        }
        return "";
    }

    /**
     * The placeholder option's text: the null-input message when rows exist,
     * the no-data message when they do not — the legacy ternary.
     */
    protected readonly placeholderMessage = computed(() =>
        this.options().length > 0 ? this.nullInputMessage() : this.noDataMessage(),
    );

    /**
     * Handle the control's change: the placeholder option (empty value)
     * clears the model, an option's index selects its row.
     * @param raw The control's raw string value.
     */
    protected onValueChange(raw: string): void {
        this.value.set(raw === "" ? null : (this.options()[Number(raw)] ?? null));
    }

    /**
     * The control's value: the selected row's index as a string, `''` for
     * the placeholder option — the native-select counterpart of the
     * legacy `ngValue`/`compareWith` pair (DD-155).
     * @returns The option value string.
     */
    protected controlValue(): string {
        const value = this.value();
        return value === null ? "" : String(this.options().indexOf(value));
    }

    /**
     * Emit `searchRequested`, as `activateSearchModal` opened the modal.
     */
    protected activateSearch(): void {
        if (!this.disabled() && !this.searchLoading()) {
            this.searchRequested.emit();
        }
    }
}
