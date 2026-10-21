import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, input, model, output } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faSearch } from "@fortawesome/free-solid-svg-icons";

/**
 * The legacy Aurelius search box (`models4insight-simple-search-input`),
 * ported without its `ControlShell` wrapper or reactive form (DD-046): the
 * query lives in a `model()` and the Bulma field markup is inlined.
 *
 * The query two-way binds; `querySubmitted` fires on Enter, on the submit
 * button, and on clear (the Aurelius clear path re-submitted, so a caller
 * filtering on submit sees the cleared term immediately).
 *
 * Chrome text — placeholder, submit/clear accessible names — is caller
 * supplied (DD-047): the Aurelius app translated the placeholder itself and
 * carried no string for the icon buttons.
 */
@Component({
    selector: "aurelius-atlas-ui-search-field",
    imports: [CommonModule, FontAwesomeModule, FormsModule],
    templateUrl: "./search-field.component.html",
    styleUrl: "./search-field.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchField {
    /**
     * The current query. Two-way bindable; an empty input reads back as
     * `null`, as the Aurelius control normalised it.
     */
    readonly query = model<string | null>(null);

    /**
     * The input's placeholder. The caller localises it.
     */
    readonly placeholder = input<string>();

    /**
     * Whether to show the submit button, as the Aurelius context's
     * `withSubmitButton` did.
     */
    readonly withSubmitButton = input(true);

    /**
     * Accessible name of the submit button. The caller localises it; the
     * Aurelius icon button had none.
     */
    readonly submitLabel = input("Search");

    /**
     * Accessible name of the clear button. The caller localises it; the
     * Aurelius icon had none.
     */
    readonly clearLabel = input("Clear");

    /**
     * Emits the query when the user submits it (Enter, submit button) or
     * clears it — the Aurelius `querySubmitted` contract, `null` when cleared.
     */
    readonly querySubmitted = output<string | null>();

    /**
     * The FontAwesome icon used by the submit button.
     */
    protected readonly faSearch = faSearch;

    /**
     * Handle input: store the query, normalising the empty string to `null`
     * as the Aurelius valueChanges pipe did.
     * @param value The raw input value.
     */
    protected onQueryChange(value: string): void {
        this.query.set(value ? value : null);
    }

    /**
     * Emit the current query, as `submitQuery` did.
     */
    protected submitQuery(): void {
        this.querySubmitted.emit(this.query());
    }

    /**
     * Clear the query and re-submit, as `clearQuery` did — the Aurelius
     * clear path emitted `querySubmitted` with `null`.
     */
    protected clearQuery(): void {
        this.query.set(null);
        this.querySubmitted.emit(null);
    }
}
