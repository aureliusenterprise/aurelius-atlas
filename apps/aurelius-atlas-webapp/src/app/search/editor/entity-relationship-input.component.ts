import { ChangeDetectionStrategy, Component, computed, inject, input, output, signal } from "@angular/core";
import { Subscription } from "rxjs";
import { ViewSearchService, type EntityCard } from "aurelius-atlas-data-access";
import { TokenPicker, type TokenChip, type TokenRow } from "aurelius-atlas-ui";

import { nameDisplay } from "../meta/type-display";
import { typeIcon } from "../meta/type-icons";
import { trailOf } from "../shared/trail";
import { type RelationshipField, type RelationshipPick, relationshipEntry } from "./form-fields";

/**
 * One relationship-attribute picker (EDT-14 as amended in 7.31, DD-711): the
 * dumb `TokenPicker` box (UIC-44, DD-713) around a view-family search round
 * trip — `POST /api/aurelius/v1/search` narrowed to the target type and its
 * sub types, typed text sent so it matches the beginning of a name and
 * verified prefix-wise client-side, at the stock dashboard's 10 typed /
 * 5 browse limits with its 250 ms debounce. An empty focused box browses up to
 * five candidates of the target type instead (DD-343), so the picker suggests
 * before anything is typed. Each row reads like a search card (EDT-33): the
 * name, its type badge, and the stored trail — names repeat, type and trail
 * do not.
 *
 * This component is the data wiring and nothing else (DD-341 — the ui library
 * never injects an HTTP client): it answers the box's `typed` with rows and
 * turns the box's `picked` back into the saved entry. The box, its chips, its
 * combobox keyboard and its accessible name belong to the picker (UIC-44). The
 * editor holds the value: `selected` seeds and replaces the chips, `changed`
 * carries the full new list on every pick or removal.
 */
@Component({
    imports: [TokenPicker],
    selector: "aurelius-atlas-webapp-entity-relationship-input",
    template: `
        <aurelius-atlas-ui-token-picker
            [selected]="chips()"
            [rows]="rows()"
            [text]="text()"
            [single]="field().single"
            [invalid]="invalid()"
            [label]="label()"
            [placeholder]="placeholder"
            [singlePlaceholder]="singlePlaceholder"
            [deleteLabel]="deleteLabel()"
            [labelId]="labelId()"
            [errorId]="errorId()"
            [idBase]="idBase()"
            (typed)="onTyped($event)"
            (entered)="onEntered()"
            (picked)="onPicked($event)"
            (removed)="onRemoved($event)"
        />
    `,
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

    private readonly search = inject(ViewSearchService);

    /** The typed text — the box shows it, this component holds it (UIC-44). */
    protected readonly text = signal("");

    /** The found cards awaiting the exclusions (the raw search answer). */
    private readonly found = signal<readonly EntityCard[]>([]);

    /** The in-flight search (a new keystroke drops it — last typed text wins). */
    private pending: Subscription | null = null;

    /** The debounce timer (250 ms, the stock select2's delay — DD-339). */
    private timer: ReturnType<typeof setTimeout> | null = null;

    /** The chips' display labels — the value keeps the raw fields (EDT-15).
     * The lead word is the dictionary display name of the pick's type
     * (DD-379), raw for a name the dictionary never saw. */
    protected readonly chips = computed<TokenChip[]>(() =>
        this.selected().map((pick) => ({
            key: pick.guid,
            label: pick.displayText ?? pick.qualifiedName ?? pick.guid,
            leadLabel: nameDisplay(pick.typeName ?? ""),
        })),
    );

    /** The chosen guids plus the edited entity — the panel drops all of them (EDT-14). */
    private readonly excluded = computed(() => {
        const ids = new Set<string>(this.selected().map((pick) => pick.guid));
        const edited = this.editedGuid();
        if (edited !== "") {
            ids.add(edited);
        }
        return ids;
    });

    /** The panel rows (EDT-14, EDT-33): the found cards minus the excluded.
     * The door matches whole analysed tokens, so typed text also gets the
     * name-prefix check here — the rule the old attribute door applied
     * server-side (DD-711). The card always carries a guid, so every row is
     * pickable; the trail drops the entity's own crumb (VDR-06 appends it,
     * and the row *is* the entity) and rides on as the crumbs the card's own
     * trail carries, so the row prints them with the Breadcrumbs component
     * like every other trail in the product (DD-714). */
    protected readonly rows = computed<TokenRow[]>(() => {
        const excluded = this.excluded();
        const typed = this.text().trim().toLowerCase();

        return this.found()
            .filter((card) => !excluded.has(card.guid))
            .filter((card) => typed === "" || (card.displayText || card.guid).toLowerCase().startsWith(typed))
            .map((card) => {
                const icon = typeIcon(card.typeName);
                const trail = trailOf(card, typeIcon).slice(0, -1);
                return {
                    key: card.guid,
                    name: card.displayText || card.guid,
                    type: nameDisplay(card.typeName),
                    ...(icon !== undefined ? { icon: icon.icon, iconClass: icon.classIcon } : {}),
                    ...(trail.length > 0 ? { trail } : {}),
                };
            });
    });

    /** The ids the combobox wiring (DD-336) names — unique per field. The
     * editor's label and error lines carry the same prefix (EDT-17), so the
     * picker mints its listbox and input under it. */
    protected readonly idBase = computed(() => `editor-relationship-${this.field().name}`);

    protected readonly labelId = computed(() => `${this.idBase()}-label`);

    protected readonly errorId = computed(() => `${this.idBase()}-error`);

    /** The placeholder by cardinality (EDT-17's catalogue keys). */
    protected readonly placeholder = $localize`:@@search.components.editor.components.relationshipsInput.addPlaceholder:Add a relationship...`;

    protected readonly singlePlaceholder = $localize`:@@search.components.editor.components.relationshipsInput.selectPlaceholder:Select a relationship...`;

    /** Typing (EDT-14): non-empty text searches with the typed prefix; empty
     * or whitespace-only text is the browse (DD-343). */
    protected onTyped(value: string): void {
        this.text.set(value);
        this.searchFor(value.trim());
    }

    /** The box was entered with nothing typed (DD-343): browse up to five
     * candidates, so the picker suggests before anything is typed. */
    protected onEntered(): void {
        if (this.text().trim() === "") {
            this.searchFor("");
        }
    }

    /** One debounced round trip (EDT-14 as amended, DD-711): 250 ms, the stock
     * select2's delay; an empty text browses the target type (limit 5), typed
     * text searches it (limit 10, the stock contract). The door matches whole
     * analysed tokens, so the typed text carries a trailing wildcard — the
     * "beginning of the name" half of the stock contract (AVR-04) — with the
     * wildcard characters themselves stripped, since the door would read them
     * as its own syntax. A pending timer or request is dropped — the latest
     * intent wins. */
    private searchFor(text: string): void {
        if (this.timer !== null) {
            clearTimeout(this.timer);
            this.timer = null;
        }
        this.pending?.unsubscribe();
        this.pending = null;
        this.timer = setTimeout(() => {
            this.timer = null;
            const target = this.field().targetType;
            this.pending = this.search
                .search({
                    // The type-narrowing idiom of the search page (VSR-04):
                    // the stored documents carry the whole super chain, so a
                    // sub type's entities answer too.
                    filters: { any: [{ typeName: [target] }, { superTypeNames: [target] }] },
                    limit: text === "" ? 5 : 10,
                    ...(text === "" ? {} : { query: `${text.replace(/[*?]/g, "")}*` }),
                })
                .subscribe({
                    next: (answer) => {
                        this.pending = null;
                        this.found.set(answer.cards ?? []);
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

    /** The box picked a row (EDT-14): append its entry and clear the input.
     * The row's key is the card's guid, so the value keeps the card's own
     * fields and never the row's trail (EDT-15). */
    protected onPicked(row: TokenRow): void {
        const card = this.found().find((candidate) => candidate.guid === row.key);
        if (card === undefined) {
            return;
        }
        const entry = relationshipEntry(card);
        if (entry === null) {
            return;
        }
        const current = this.selected();
        this.changed.emit(current.some((pick) => pick.guid === entry.guid) ? current : [...current, entry]);
        this.text.set("");
        this.found.set([]);
    }

    /** A chip's delete (EDT-14/UIC-24): the picker answers the full new list. */
    protected onRemoved(chip: TokenChip): void {
        this.changed.emit(this.selected().filter((pick) => pick.guid !== chip.key));
    }
}
