import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { AbstractControl, FormArray, FormControl, FormGroup, ReactiveFormsModule, Validators } from "@angular/forms";
import { ActivatedRoute, Router } from "@angular/router";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faXmark } from "@fortawesome/free-solid-svg-icons";
import { map } from "rxjs";

import { ClassificationChip, Drawer, Select } from "aurelius-atlas-ui";

import { EditorState } from "./editor-state";
import { type EditorField, type EditorLabels, buildFields, mergeOntoEntity, toFormValues } from "./form-fields";

/** A picker row for the ui-lib {@link Select} (its `displayField` is `label`). */
type PickerRow = { name: string; label: string };

/** An enum option row (EDT-03's enum kind — the Select's `displayField`). */
type EnumRow = { value: string };

/**
 * The entity editor drawer (EDT-01..EDT-08, DD-322): the routed panel in the
 * `drawer` aux outlet beside the settings and alerts panels (the AlertsPanel
 * shape — the open state rides the URL, dismissal navigates the outlet away),
 * reached from the details pencil (`edit/:guid`) and the search hero's
 * `+` (`create`). The editor owns its entity read (EDT-02) and shares
 * no store with the screen underneath (DD-322).
 *
 * The form is generic: one control per attribute the entity's own definition
 * (plus its supertype chain) carries (EDT-03, DD-323); create mode picks the
 * type from a picker over the shipped entity typedefs (EDT-04) — the chosen
 * type rides the route (`create/<type>`, DD-330), so the picker stays
 * above the form as a field and a re-pick switches the type, re-seeding the
 * form. The footer is Save only (EDT-10 — the Delete is 7.9's, and there is
 * no Cancel: dismissal is the drawer's X/backdrop/Escape, EDT-01). Save
 * merges the form onto the entity, POSTs it, then replaces the
 * classifications through the one PUT (EDT-06, DD-326), and lands on the
 * entity's details screen.
 */
@Component({
    imports: [ClassificationChip, Drawer, FontAwesomeModule, ReactiveFormsModule, Select],
    providers: [EditorState],
    selector: "aurelius-atlas-webapp-entity-editor",
    templateUrl: "./entity-editor.component.html",
    styleUrl: "./entity-editor.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityEditor {
    protected readonly state = inject(EditorState);

    private readonly router = inject(Router);

    /** The drawer's open state — true for the panel's whole life (EDT-01). */
    readonly active = signal(true);

    /** Whether a Save was attempted — shows the notification (EDT-07). */
    protected readonly saveAttempted = signal(false);

    /** Whether the notification's X hid it — until the next Save (DD-331). */
    protected readonly notificationDismissed = signal(false);

    /** The form, a signal so the field-set rebuild repaints (EDT-03). */
    protected readonly form = signal(new FormGroup<Record<string, AbstractControl>>({}));

    private readonly route = inject(ActivatedRoute);

    /** The route's `:guid` (edit mode) — the editor reads its own entity. */
    private readonly guid = toSignal(this.route.paramMap.pipe(map((params) => params.get("guid") ?? "")), {
        initialValue: "",
    });

    /** The route's `:type` (create mode, DD-330) — "" before the first pick. */
    private readonly routeType = toSignal(this.route.paramMap.pipe(map((params) => params.get("type") ?? "")), {
        initialValue: "",
    });

    /** The mode, off the route segment — no store sentinel (EDT-01, DD-325). */
    private readonly isCreate = this.route.routeConfig?.path?.startsWith("create") ?? false;

    /** The fields the form renders (EDT-03), from the store's typedefs. */
    protected readonly fields = computed(() => {
        const typeName = this.state.typeName();
        const defs = this.state.entityDefsByName();
        const def = typeName ? defs.get(typeName) : undefined;

        return def ? buildFields(def, defs, this.state.enumsByName(), this.labels) : [];
    });

    /** The picker rows for the ui-lib Select (EDT-04). The Select's `options`
     * input is a mutable array, so the map yields a fresh one (not readonly). */
    protected readonly pickerRows = computed<PickerRow[]>(() =>
        this.state.pickerTypes().map(({ name, label }) => ({ name, label })),
    );

    /** The classification box's datalist suggestions (EDT-05). */
    protected readonly suggestions = computed(() =>
        this.state.applicableClassifications().map((def) => def.name ?? ""),
    );

    /** The chosen tags that carry a name (EDT-05) — the template's tag row. */
    protected readonly chosenTags = computed(() =>
        this.state
            .chosen()
            .filter((tag) => typeof tag.typeName === "string" && tag.typeName !== "")
            .map((tag) => ({ typeName: tag.typeName as string })),
    );

    /** The create-mode type field: the picker stays above the form (EDT-04, DD-330). */
    protected readonly pickerVisible = computed(() => this.isCreate);

    /** Edit mode's static type text (EDT-04): the type never changes there. */
    protected readonly staticType = computed(() => (!this.isCreate ? (this.state.entity()?.typeName ?? "") : ""));

    /** The picker's selected row, read off the route's type (DD-330). The
     * row must be the pickerRows() array's own object — the Select matches
     * its value by identity. */
    protected readonly pickerSelected = computed<PickerRow | null>(
        () => this.pickerRows().find((row) => row.name === this.routeType()) ?? null,
    );

    /** Whether a create type switch is in flight (the form's loading slot). */
    protected readonly typeSwitching = computed(
        () => this.isCreate && this.routeType() !== "" && this.state.selectedTypeName() !== this.routeType(),
    );

    /** Whether the form renders: create once a type is seeded (not mid-
     * switch), edit once the read answered (EDT-02's loading line). */
    protected readonly formVisible = computed(() =>
        this.isCreate
            ? this.state.typeName() !== null && !this.typeSwitching()
            : !this.state.loading() || this.state.entity() !== null,
    );

    protected readonly drawerTitle = computed(() => (this.isCreate ? this.createTitle : this.editTitle));

    /** The tag box's input: typing filters, Enter adds (EDT-05). */
    protected readonly classificationInput = new FormControl("", { nonNullable: true });

    /** The typed text as a signal (the FormControl is not one) — it drives
     * the panel filter (EDT-05, DD-335). */
    private readonly typedText = toSignal(this.classificationInput.valueChanges, { initialValue: "" });

    /** Whether the classification box holds focus (EDT-05, DD-335). */
    protected readonly boxFocused = signal(false);

    /** Whether the panel is open for the current typing run (EDT-05,
     * DD-335): Escape closes it, the next typed character opens it again. */
    protected readonly suggestionsOpen = signal(true);

    /** The suggestions the typed text filters (EDT-05, DD-335): a match
     * that starts with the text leads, so Enter (which adds the active
     * option, DD-336) commits the closest name — the old exact-else-first
     * rule kept in the panel order. */
    protected readonly filteredSuggestions = computed(() => {
        const typed = this.typedText().trim().toLowerCase();
        if (typed === "") {
            return this.suggestions();
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
    protected readonly activeSuggestion = signal(0);

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

    protected readonly closeLabel = $localize`:@@components.modal.close:Close`;

    protected readonly editTitle = $localize`:@@search.editEntity.editEntity:Edit entity`;

    protected readonly createTitle = $localize`:@@search.createEntity.newEntity:Create new entity`;

    protected readonly pickerLabel = $localize`:@@search.details.typeSelect.label:Entity type`;

    protected readonly classificationsLabel = $localize`:@@search.components.editor.attribute.classifications:Classifications`;

    protected readonly classificationsPlaceholder = $localize`:@@search.components.editor.components.classificationsInput.addPlaceholder:Add a classification...`;

    protected readonly noClassifications = $localize`:@@search.components.editor.components.classificationsInput.noClassificationsAvailable:No classifications available`;

    protected readonly deleteLabel = $localize`:@@search.components.editor.delete:Delete`;

    protected readonly saveLabel = $localize`:@@search.components.editor.save:Save`;

    /** The multi row's delete icon. */
    protected readonly faXmark = faXmark;

    protected readonly nameRequired = $localize`:@@search.components.editor.attribute.nameRequired:Name is required.`;

    protected readonly notificationLine = $localize`:@@search.components.editor.attribute.notification:This entity can't be saved because one or more required fields are missing.`;

    protected readonly loadingLine = $localize`:@@search.services.entityDetails.retrieve:Retrieving the entity details`;

    protected readonly savingLine = $localize`:@@search.services.entityUpdate.save:Saving the entity`;

    private readonly labels: EditorLabels = {
        name: $localize`:@@search.components.editor.attribute.name:Name*`,
        definition: $localize`:@@search.components.editor.attribute.definition:Definition`,
    };

    /** The field-set signature the last build used (the rebuild guard). */
    private builtSignature = "";

    constructor() {
        this.state.mode.set(this.isCreate ? "create" : "edit");
        this.state.loadTypeDefs();

        // The entity read follows the route's guid (EDT-02) — edit mode only.
        effect(() => {
            const guid = this.guid();
            if (!this.isCreate && guid) {
                this.state.loadEntity(guid);
            }
        });

        // Create mode seeds its entity from the route's type (DD-330): the
        // bare `create` shows the picker alone, and every pick or
        // switch lands here through the URL — the same seed path (DD-325),
        // which clears the tag box and the typed fields (EDT-04's switch).
        effect(() => {
            const type = this.routeType();
            if (this.isCreate && type !== "" && this.state.selectedTypeName() !== type) {
                this.state.beginCreate(type);
            }
        });

        // (Re)build the form when the field set changes: create at the type
        // pick or switch, edit once the entity and the typedefs have both
        // answered. The type names the signature (DD-330) so a switch to a
        // field-less type still drops the old form.
        effect(() => {
            const signature = `${this.state.typeName() ?? ""}|${this.fields()
                .map((field) => `${field.name}:${field.kind}`)
                .join(",")}`;
            if (signature !== this.builtSignature) {
                this.builtSignature = signature;
                this.form.set(this.buildForm());
            }
        });

        // The tag input disables with the field (DD-336): nothing applies
        // and nothing is chosen, so typing could only match nothing. Chosen
        // tags keep their delete (they ride the chips, not this control).
        effect(() => {
            if (this.classificationDisabled()) {
                this.classificationInput.disable({ emitEvent: false });
            } else {
                this.classificationInput.enable({ emitEvent: false });
            }
        });

        // The active option re-clamps as the filter narrows (DD-336): a
        // typed prefix can shrink the list under the current index.
        effect(() => {
            const count = this.filteredSuggestions().length;
            if (count > 0 && this.activeSuggestion() >= count) {
                this.activeSuggestion.set(0);
            }
        });
    }

    /** The form for the current field set, seeded from the entity (EDT-02). */
    private buildForm(): FormGroup<Record<string, AbstractControl>> {
        const values = toFormValues(this.state.entity() ?? {}, this.fields());
        const controls: Record<string, AbstractControl> = {};

        for (const field of this.fields()) {
            const validators = field.required ? [Validators.required] : [];
            if (field.kind === "multi") {
                const array = new FormArray<FormControl<string>>(
                    [...((values[field.name] as string[]) ?? []).map(String), ""].map(
                        (row) => new FormControl(row, { nonNullable: true }),
                    ),
                    { validators },
                );
                // The list repeats: the blank trailing row becomes real on
                // typing and a new blank row joins (EDT-03). The valueChanges
                // subscription sees post-update values, unlike a DOM handler.
                array.valueChanges.subscribe(() => {
                    const last = array.at(array.length - 1);

                    if (last !== undefined && String(last.value ?? "").trim() !== "") {
                        array.push(new FormControl("", { nonNullable: true }));
                    }
                });
                controls[field.name] = array;
            } else {
                controls[field.name] = new FormControl(
                    { value: values[field.name], disabled: field.disabled },
                    { validators },
                );
            }
        }

        return new FormGroup(controls);
    }

    /** Whether a control shows its error (touched, or a Save was tried, EDT-07). */
    protected showError(field: EditorField): boolean {
        const control = this.form().get(field.name);

        return control !== null && control.invalid && (control.touched || this.saveAttempted());
    }

    /** The multi field's row controls (EDT-03's repeating text list). */
    protected rowsOf(field: EditorField): readonly FormControl[] {
        const array = this.form().get(field.name);

        return array instanceof FormArray ? (array.controls as unknown as readonly FormControl[]) : [];
    }

    /** Drop one multi row; the list always keeps its blank trailing row. */
    protected removeMultiRow(field: EditorField, index: number): void {
        const array = this.form().get(field.name) as FormArray<FormControl<string>>;

        array.removeAt(index);
        if (array.length === 0) {
            array.push(new FormControl("", { nonNullable: true }));
        }
    }

    /** The enum field's options (EDT-03's enum kind). */
    protected enumRows(field: EditorField): EnumRow[] {
        return (field.enumValues ?? []).map((value) => ({ value }));
    }

    /** The enum field's selected row, read off the control. */
    protected enumSelected(field: EditorField): EnumRow | null {
        const current = String(this.form().get(field.name)?.value ?? "");

        return (field.enumValues ?? []).includes(current) ? { value: current } : null;
    }

    /** Write an enum pick into the control (the Select carries no accessor). */
    protected enumPicked(field: EditorField, row: EnumRow | null): void {
        this.form()
            .get(field.name)
            ?.setValue(row?.value ?? "");
    }

    /**
     * Add the typed classification (EDT-05). With the panel open, Enter
     * commits the active option (DD-336) — the panel is the listbox and
     * Down/Up move what Enter adds. With it shut, the old rule stands: the
     * typed text must name an applicable type exactly. The input clears
     * only on a real add: a miss keeps the text so the user can see what
     * did not apply. (DD-329's `change` commit retired with the datalist,
     * DD-335.)
     */
    protected addClassification(): void {
        if (this.dropdownShown()) {
            const name = this.filteredSuggestions()[this.activeSuggestion()];
            if (name !== undefined) {
                this.addNamed(name);
            }

            return;
        }
        const typed = (this.classificationInput.value ?? "").trim();

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

    /** Add a named tag and clear the input (the pick and Enter path). */
    private addNamed(name: string): void {
        this.state.addClassification(name);
        this.classificationInput.setValue("");
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
        const from = this.dropdownShown() ? this.activeSuggestion() : step === 1 ? -1 : count;
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

    /** The chip's tooltip: the classification def's description (UIC-16). */
    protected chipTooltip(typeName: string): string | undefined {
        return (
            this.state.typedefsDef()?.classificationDefs?.find((def) => def.name === typeName)?.description ?? undefined
        );
    }

    /** Remove a chosen tag (EDT-05). */
    protected removeClassification(typeName: string): void {
        this.state.removeClassification(typeName);
    }

    /**
     * Choose or switch the create-mode type (EDT-04, DD-330): navigate the
     * drawer segment to the new type — the URL is the state, so the seed
     * effect above rebuilds the form. An empty pick (the placeholder) is
     * ignored: there is no type-less form to show.
     */
    protected pickType(row: PickerRow | null): void {
        if (row && row.name !== this.routeType()) {
            void this.router.navigate([{ outlets: { drawer: ["create", row.name] } }]);
        }
    }

    /** Hide the dismissed notification's X; the next Save shows it again. */
    protected dismissNotification(): void {
        this.notificationDismissed.set(true);
    }

    /** Save (EDT-06/07): invalid bails marked-touched; valid merges and saves. */
    protected save(): void {
        this.saveAttempted.set(true);
        this.notificationDismissed.set(false);
        if (this.form().invalid) {
            this.form().markAllAsTouched();

            return;
        }
        const entity = this.state.entity();
        if (!entity?.typeName) {
            return;
        }
        const merged = mergeOntoEntity(entity, this.fields(), this.form().getRawValue() as Record<string, unknown>);

        this.state.save(merged, entity.guid ?? "");
    }

    /** Dismiss (EDT-01): X, backdrop, Escape — navigate the outlet away. */
    protected close(): void {
        this.active.set(false);
        this.router.navigate([{ outlets: { drawer: null } }]);
    }
}
