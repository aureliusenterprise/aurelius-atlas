import {
    ChangeDetectionStrategy,
    Component,
    computed,
    effect,
    inject,
    Injector,
    signal,
    untracked,
} from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { disabled, Field, FieldTree, form, FormField, required, SchemaPathTree } from "@angular/forms/signals";
import { ActivatedRoute, Router } from "@angular/router";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faXmark } from "@fortawesome/free-solid-svg-icons";
import { map } from "rxjs";

import { ClassificationChip, Drawer, Holdable, MarkdownEditor, Select } from "aurelius-atlas-ui";

import { nameDisplay } from "../meta/type-display";
import { canWriteEntities } from "./can-write-entities";
import { EditorState } from "./editor-state";
import { EntityRelationshipInput } from "./entity-relationship-input.component";
import {
    type EditorField,
    type EditorLabels,
    type RelationshipField,
    type RelationshipPick,
    buildFields,
    buildRelationshipFields,
    mergeOntoEntity,
    mergeRelationshipsOntoEntity,
    seedRelationshipValues,
    toFormValues,
} from "./form-fields";

/** A picker row for the ui-lib {@link Select} (its `displayField` is `label`). */
type PickerRow = { name: string; label: string };

/** An enum option row (EDT-03's enum kind — the Select's `displayField`). */
type EnumRow = { value: string };

/** One model slot: the value a field of any kind holds (DD-354). */
type EditorValue = string | number | boolean | string[] | null;

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
    imports: [
        ClassificationChip,
        Drawer,
        EntityRelationshipInput,
        FontAwesomeModule,
        FormField,
        Holdable,
        MarkdownEditor,
        Select,
    ],
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

    private readonly route = inject(ActivatedRoute);

    /** The route's `:guid` (edit mode) — the editor reads its own entity. */
    private readonly guid = toSignal(this.route.paramMap.pipe(map((params) => params.get("guid") ?? "")), {
        initialValue: "",
    });

    /** The route's `:type` (create mode, DD-330) — "" before the first pick. */
    private readonly routeType = toSignal(this.route.paramMap.pipe(map((params) => params.get("type") ?? "")), {
        initialValue: "",
    });

    /** The mode, off the route's data — no store sentinel (EDT-01, DD-325).
     * DD-355 moved it off the route segment: the segment read worked only
     * while `create` and `create/:type` were two configs, and that split
     * rebuilt this component (and replayed the drawer's slide-in) on the
     * first type pick. One matcher route now serves both URLs, so the mode
     * cannot come from the path anymore. */
    private readonly isCreate = this.route.snapshot.data["editorMode"] === "create";

    private readonly labels: EditorLabels = {
        name: $localize`:@@search.components.editor.attribute.name:Name*`,
        definition: $localize`:@@search.components.editor.attribute.definition:Definition`,
    };

    /** The fields the form renders (EDT-03), from the store's typedefs. */
    protected readonly fields = computed(() => {
        const typeName = this.state.typeName();
        const defs = this.state.entityDefsByName();
        const def = typeName ? defs.get(typeName) : undefined;

        return def ? buildFields(def, defs, this.state.enumsByName(), this.labels) : [];
    });

    // The form trio sits below `fields` on purpose: `form()` compiles the
    // schema eagerly, and the schema pass reads the field set (DD-354).

    /** The form's values, one slot per field — the model {@link form} reads
     * (EDT-02's seed, EDT-06's source, DD-354). */
    protected readonly values = signal<Record<string, EditorValue>>({});

    private readonly injector = inject(Injector);

    /** The signal form over {@link values}. A field-set rebuild replaces it
     * (EDT-03) so a type switch also clears the touched/dirty state, the way
     * the rebuilt group used to (DD-354). */
    protected readonly form = signal(this.newForm());

    /** The relationship pickers the form renders (EDT-13, DD-338), from the
     * def's `relationshipAttributeDefs` and its supertype chain. */
    protected readonly relationshipFields = computed(() => {
        const typeName = this.state.typeName();
        const defs = this.state.entityDefsByName();
        const def = typeName ? defs.get(typeName) : undefined;

        return def ? buildRelationshipFields(def, defs) : [];
    });

    /** The picker values the form holds (EDT-15's seed, EDT-14's edits). They
     * ride their own signal, not the form model: a picker's value is a chip
     * list the save merges separately (EDT-16), not an attribute field. */
    protected readonly relationshipValues = signal<ReadonlyMap<string, readonly RelationshipPick[]>>(new Map());

    /** The picker rows for the ui-lib Select (EDT-04). The Select's `options`
     * input is a mutable array, so the map yields a fresh one (not readonly). */
    protected readonly pickerRows = computed<PickerRow[]>(() =>
        this.state.pickerTypes().map(({ name, label }) => ({ name, label })),
    );

    /** The classification box's datalist suggestions (EDT-05). */
    protected readonly suggestions = computed(() =>
        this.state.applicableClassifications().map((def) => def.name ?? ""),
    );

    /**
     * The chosen tags that carry a name (EDT-05) — the template's tag row.
     * The row keeps the raw `typeName` (the tooltip lookup and the remove
     * emit ride it); the chip's label is the dictionary display name,
     * rendered below (DD-379).
     */
    protected readonly chosenTags = computed(() =>
        this.state
            .chosen()
            .filter((tag) => typeof tag.typeName === "string" && tag.typeName !== "")
            .map((tag) => ({ typeName: tag.typeName as string })),
    );

    /**
     * A type or classification name's display name for the template
     * (EDT-05, DD-379): the legacy `name | translate` — the dictionary
     * display name, raw for a name the dictionary never saw. The tag
     * chips and the suggestion rows render through it; the values stored
     * and sent keep the raw name (EDT-16).
     * @param name the raw classification name
     */
    protected display(name: string): string {
        return nameDisplay(name);
    }

    /** The create-mode type field: the picker stays above the form (EDT-04, DD-330). */
    protected readonly pickerVisible = computed(() => this.isCreate);

    /**
     * Edit mode's static type text (EDT-04, DD-379): the type never
     * changes there. The legacy's type select shows the dictionary
     * display name (`translatedName`, `type-select.component.ts:116`),
     * so the text is `nameDisplay` of the raw name.
     */
    protected readonly staticType = computed(() =>
        !this.isCreate ? nameDisplay(this.state.entity()?.typeName ?? "") : "",
    );

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

    /** Whether the form currently fails its rules (EDT-07) — read through the
     * field-state signals, not the old FormGroup's `invalid` (DD-354). */
    protected readonly formInvalid = computed(() => this.form()().invalid());

    /** The tag box's typed text (EDT-05): typing filters, Enter adds. The
     * box is not a form field — the tags ride the store, not the model —
     * so it is a plain signal, not a control (DD-354). */
    protected readonly classificationText = signal("");

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
        const typed = this.classificationText().trim().toLowerCase();
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

    /** The markdown field's tab pair and placeholder (EDT-20, DD-353): the
     * vendored `components.markdownEditor.*` trio — the ui library's field
     * carries no string of its own (UIC-04, DD-136). */
    protected readonly markdownWriteLabel = $localize`:@@components.markdownEditor.writeLabel:Write`;

    protected readonly markdownPreviewLabel = $localize`:@@components.markdownEditor.previewLabel:Preview`;

    protected readonly markdownPlaceholder = $localize`:@@components.markdownEditor.placeholder:Please type some markdown to get started...`;

    protected readonly notificationLine = $localize`:@@search.components.editor.attribute.notification:This entity can't be saved because one or more required fields are missing.`;

    protected readonly loadingLine = $localize`:@@search.services.entityDetails.retrieve:Retrieving the entity details`;

    protected readonly savingLine = $localize`:@@search.services.entityUpdate.save:Saving the entity`;

    protected readonly deletingLine = $localize`:@@search.services.entityDelete.delete:Deleting the entity`;

    /** Whether the token may write (EDT-09) — the Delete's gate (EDT-19). */
    protected readonly canWrite = canWriteEntities();

    /**
     * Whether the Delete shows (EDT-19): an existing entity (edit mode —
     * create has no guid to delete) that the token may write. The reference
     * gates the same two ways (role, and a guid that is not a create's
     * temporary negative one).
     */
    protected readonly deleteShown = computed(() => !this.isCreate && this.canWrite());

    /**
     * The Delete's hold, in seconds (EDT-19): the reference's hold-to-delete
     * counts three. The same value rides the directive's `holdFor`, the
     * ring's CSS animation duration (`--aurelius-hold-duration`), and the
     * tooltip's number, so the drawing, the clock, and the words can never
     * drift apart. Typed `number`, not the literal, so the tooltip's
     * singular/plural choice (the legacy rule, DD-351) compiles for any
     * count and marks both bridge keys.
     */
    protected readonly deleteHoldSeconds: number = 3;

    /**
     * The Delete's hold instruction (EDT-19, DD-351): the vendored
     * `holdable.tooltip.*` pair, single or plural by the hold's seconds —
     * the legacy directive's own rule. The caller carries it (DD-348 keeps
     * the directive paint- and text-free) as the button's native tooltip.
     */
    protected readonly deleteTooltip =
        this.deleteHoldSeconds === 1
            ? $localize`:@@holdable.tooltip.single:Hold for ${this.deleteHoldSeconds}:seconds: second`
            : $localize`:@@holdable.tooltip.plural:Hold for ${this.deleteHoldSeconds}:seconds: seconds`;

    /** The foot's status line: whichever write is in flight names itself. */
    protected readonly busyLine = computed(() => (this.state.deleting() ? this.deletingLine : this.savingLine));

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
        // field-less type still drops the old form. The model and the form
        // are both replaced, so the touched/dirty state clears with the old
        // field set (DD-354). The pickers re-seed from the entity here too
        // (EDT-15).
        effect(() => {
            const signature = `${this.state.typeName() ?? ""}|${this.fields()
                .map((field) => `${field.name}:${field.kind}`)
                .join(",")}`;
            if (signature !== this.builtSignature) {
                this.builtSignature = signature;
                this.values.set(this.seedValues());
                // `form()` builds its own management effects, which Angular
                // forbids inside a reactive context. The schema's reads need
                // no tracking either — the signature above already names the
                // field set (DD-354).
                untracked(() => this.form.set(this.newForm()));
                this.relationshipValues.set(
                    new Map(
                        Object.entries(seedRelationshipValues(this.state.entity() ?? {}, this.relationshipFields())),
                    ),
                );
            }
        });

        // The multi lists repeat: the blank trailing row becomes real on
        // typing and a new blank row joins (EDT-03). The effect reads the
        // model, so it sees post-update values, unlike a DOM handler.
        effect(() => {
            const values = this.values();
            for (const field of this.fields()) {
                if (field.kind !== "multi") {
                    continue;
                }
                const list = values[field.name] as string[] | undefined;
                if (list !== undefined && list.length > 0 && String(list.at(-1) ?? "").trim() !== "") {
                    this.values.update((current) => ({
                        ...current,
                        [field.name]: [...((current[field.name] as string[]) ?? []), ""],
                    }));
                    return; // one list per pass; the update re-runs the effect
                }
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

    /** A fresh signal form over {@link values}, with the current field set's
     * rules (EDT-03, DD-354). The injector rides because a rebuild calls
     * this outside an injection context. */
    private newForm(): FieldTree<Record<string, EditorValue>> {
        return form(this.values, (path) => this.applyRules(path), { injector: this.injector });
    }

    /** The form's rules, one pass over the rendered fields (DD-354): the
     * required marker of EDT-03 becomes `required`, the unique-attribute
     * lock becomes `disabled`. A boolean skips the rule on purpose: the old
     * control-level required let `false` through (an unchecked box is a
     * value, not a gap), and the library's required calls `false` empty. */
    private applyRules(path: SchemaPathTree<Record<string, EditorValue>>): void {
        for (const field of this.fields()) {
            const fieldPath = path[field.name];
            if (field.required && field.kind !== "boolean") {
                required(fieldPath);
            }
            if (field.disabled) {
                disabled(fieldPath, { when: () => true });
            }
        }
    }

    /** The model for the current field set, seeded from the entity (EDT-02).
     * The number slots seed `null` when empty — the number input's own
     * empty value (DD-354); the multi lists seed with the blank trailing
     * row EDT-03 renders (EDT-02). */
    private seedValues(): Record<string, EditorValue> {
        // The helper writes a string, a boolean, or a string list per kind;
        // the cast states that invariant at the model boundary (DD-354).
        const seeded: Record<string, EditorValue> = {
            ...(toFormValues(this.state.entity() ?? {}, this.fields()) as Record<string, EditorValue>),
        };
        for (const field of this.fields()) {
            if (field.kind === "number" && seeded[field.name] === "") {
                seeded[field.name] = null;
            }
            if (field.kind === "multi") {
                seeded[field.name] = [...((seeded[field.name] as string[]) ?? []), ""];
            }
        }

        return seeded;
    }

    /** The field's node in the tree, typed for its input (the dynamic-record
     * pattern: the binding site restates what the field's kind guarantees). */
    protected fieldOf(name: string): Field<EditorValue> {
        return this.form()[name] as unknown as Field<EditorValue>;
    }

    /** A text/textarea/date slot, typed for the text-like inputs. */
    protected textField(name: string): Field<string> {
        return this.form()[name] as unknown as Field<string>;
    }

    /** A number slot, typed for the number input (`null` is its empty). */
    protected numberField(name: string): Field<number | null> {
        return this.form()[name] as unknown as Field<number | null>;
    }

    /** A boolean slot, typed for the checkbox. */
    protected booleanField(name: string): Field<boolean> {
        return this.form()[name] as unknown as Field<boolean>;
    }

    /** A multi slot's rows (EDT-03's repeating text list) — the iterable
     * tree over the string array. */
    protected multiRows(name: string): FieldTree<string[]> {
        return this.form()[name] as unknown as FieldTree<string[]>;
    }

    /** Whether a control shows its error (touched, or a Save was tried, EDT-07). */
    protected showError(field: EditorField): boolean {
        const state = this.fieldOf(field.name)();

        return state.invalid() && (state.touched() || this.saveAttempted());
    }

    /** Drop one multi row; the list always keeps its blank trailing row. */
    protected removeMultiRow(field: EditorField, index: number): void {
        this.values.update((current) => {
            const list = [...((current[field.name] as string[]) ?? [])];
            list.splice(index, 1);

            return { ...current, [field.name]: list.length === 0 ? [""] : list };
        });
    }

    /** The enum field's options (EDT-03's enum kind). */
    protected enumRows(field: EditorField): EnumRow[] {
        return (field.enumValues ?? []).map((value) => ({ value }));
    }

    /** The enum field's selected row, read off the model. */
    protected enumSelected(field: EditorField): EnumRow | null {
        const current = String(this.values()[field.name] ?? "");

        return (field.enumValues ?? []).includes(current) ? { value: current } : null;
    }

    /** Write an enum pick into the model (the Select carries no accessor). */
    protected enumPicked(field: EditorField, row: EnumRow | null): void {
        this.values.update((current) => ({ ...current, [field.name]: row?.value ?? "" }));
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

    /** Add a named tag and clear the input (the pick and Enter path). */
    private addNamed(name: string): void {
        this.state.addClassification(name);
        this.classificationText.set("");
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

    /** The chips a picker holds (the template's seed + the editor's store). */
    protected picksOf(field: RelationshipField): readonly RelationshipPick[] {
        return this.relationshipValues().get(field.name) ?? [];
    }

    /** A picker answers its full new list (EDT-14): the editor holds the value. */
    protected pickRelationship(field: RelationshipField, picks: readonly RelationshipPick[]): void {
        this.relationshipValues.update((values) => new Map(values).set(field.name, picks));
    }

    /** Whether a required picker is empty (EDT-17): an invalid form, one more way. */
    protected relationshipInvalid(field: RelationshipField): boolean {
        return field.required && this.picksOf(field).length === 0;
    }

    /** Whether a picker shows its error (EDT-17 as EDT-07): after a save
     * attempt only — a fresh empty picker is not yet a mistake. */
    protected relationshipErrorShown(field: RelationshipField): boolean {
        return this.relationshipInvalid(field) && this.saveAttempted();
    }

    /** Whether any required picker is empty — the picker half of the form's validity. */
    private relationshipsMissing(): boolean {
        return this.relationshipFields().some((field) => this.relationshipInvalid(field));
    }

    /** Whether the required-fields notification shows (EDT-07/EDT-17). */
    protected notificationShown(): boolean {
        return (
            this.saveAttempted() && (this.formInvalid() || this.relationshipsMissing()) && !this.notificationDismissed()
        );
    }

    /**
     * Save (EDT-06/07/16): invalid (a control, or a required picker with no
     * chip, EDT-17) bails marked-touched; valid merges the attributes and the
     * pickers' full lists onto the entity, and saves.
     */
    protected save(): void {
        this.saveAttempted.set(true);
        this.notificationDismissed.set(false);
        const formState = this.form()();
        if (formState.invalid() || this.relationshipsMissing()) {
            formState.markAsTouched();

            return;
        }
        const entity = this.state.entity();
        if (!entity?.typeName) {
            return;
        }
        const merged = mergeOntoEntity(entity, this.fields(), this.values() as Record<string, unknown>);
        const withRelationships = mergeRelationshipsOntoEntity(
            merged,
            this.relationshipFields(),
            this.relationshipValues(),
        );

        this.state.save(withRelationships, entity.guid ?? "");
    }

    /**
     * The Delete's hold (EDT-19): the directive fires true only after the
     * three-second hold; a release before that fires false and does nothing
     * — the hold is the confirmation, no dialog. The edit-mode guid is the
     * store's own entity read (EDT-02).
     */
    protected deleteHeld(confirmed: boolean): void {
        const guid = this.state.entity()?.guid;
        if (confirmed && guid) {
            this.state.delete(guid);
        }
    }

    /** Dismiss (EDT-01): X, backdrop, Escape — navigate the outlet away. */
    protected close(): void {
        this.active.set(false);
        void this.router.navigate([{ outlets: { drawer: null } }]);
    }
}
