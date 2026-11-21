import {
    ChangeDetectionStrategy,
    Component,
    computed,
    effect,
    inject,
    Injector,
    signal,
    untracked,
    viewChild,
} from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { NgTemplateOutlet } from "@angular/common";
import { disabled, Field, FieldTree, form, FormField, required, SchemaPathTree } from "@angular/forms/signals";
import { ActivatedRoute, Router } from "@angular/router";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faCheckCircle, faExclamationTriangle, faXmark } from "@fortawesome/free-solid-svg-icons";
import { map, Subscription } from "rxjs";

import { ClassificationChip, Drawer, Holdable, MarkdownEditor, Select, TypeName } from "aurelius-atlas-ui";
import {
    QualityRuleService,
    type EntityValidationResponse,
    type GovernanceVerdict,
    ValidateEntityService,
} from "aurelius-atlas-data-access";

import { nameDisplay } from "../meta/type-display";
import { typeIcon } from "../meta/type-icons";
import { cardTypeAlias } from "../details/shared/card";
import { attributeLabels } from "./attribute-labels";
import { canWriteEntities } from "./can-write-entities";
import { EditorState } from "./editor-state";
import { EntityRelationshipInput } from "./entity-relationship-input.component";
import { EntityWritten } from "./entity-written";
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
import { bodyFromEdits, picksAfterConflict, valuesAfterConflict } from "./view-as-entity";
import { QualityFields, QUALITY_FIELDS_RELATIONSHIP, QUALITY_TYPE_NAME, storedCheckKind } from "./quality-fields";

/** A picker row for the ui-lib {@link Select} (its `displayField` is `label`). */
type PickerRow = { name: string; label: string };

/** An enum option row (EDT-03's enum kind — the Select's `displayField`). */
type EnumRow = { value: string };

/** One model slot: the value a field of any kind holds (DD-354). */
type EditorValue = string | number | boolean | string[] | null;

/** The description pair (DET-10, DD-320): the product treats the two keys as
 * one description, and the legacy's types carry `definition` where this
 * catalogue's carry `description`. The alias runs one way, as the legacy's
 * `gov-quality-display` card did (EDT-24 as amended by 12.7a, DD-633): a
 * `definition` verdict names the `description` control; a `description`
 * verdict names only its own (the map keeps its 7.24 name). */
const GOV_CARD_KEYS: Readonly<Record<string, readonly string[]>> = {
    description: ["description", "definition"],
};

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
 *
 * Since 7.24 the drawer also carries the governance banner (EDT-23/EDT-24 as
 * amended by 12.7, DD-446/DD-498): the draft rides the validate-entity aux API
 * on open and after every change debounced 200 ms, and the answer's verdicts
 * render as lines under the control their attribute names — failures swallow
 * quietly.
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
        NgTemplateOutlet,
        QualityFields,
        Select,
        TypeName,
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

    private readonly validateEntity = inject(ValidateEntityService);

    private readonly qualityRule = inject(QualityRuleService);

    /** The write-tick bus (DD-327, DD-803): the code that performs a save
     * or a delete fires its outcome here, heard to fill the outcome line
     * (LR-005, WFE-01 — never inferred from the alerts store, DD-802). */
    private readonly entityWritten = inject(EntityWritten);

    /** The quality form, once the quality-mode branch renders it (EDT-25,
     * DD-477). The drawer owns the Save button, so it reads the child's
     * validity and draft body and hands it the engine's verdict line. */
    private readonly qualityForm = viewChild(QualityFields);

    /** The drawer's open state — true for the panel's whole life (EDT-01). */
    readonly active = signal(true);

    /** Whether a Save was attempted — shows the notification (EDT-07). */
    protected readonly saveAttempted = signal(false);

    /** The verdicts of the last validation (EDT-23 as amended by 12.7). */
    private readonly validation = signal<EntityValidationResponse | null>(null);

    /** The in-flight validation (a new draft drops it — the guard, EDT-23). */
    private validationPending: Subscription | null = null;

    /** Whether the open-time validation fired — only the first round is
     * undebounced, the legacy's entityDetails-vs-valueChanges split. */
    private validatedOpen = false;

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

    /** Every field label the catalogue names (EDT-33): one localized string
     * per attribute the shipped metamodel can render (7-33, DD-722). */
    private readonly labels: EditorLabels = attributeLabels();

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
     * def's `relationshipAttributeDefs` and its supertype chain. The
     * relationship defs ride along so a parent-side picker is recognised and
     * can filter its search (RPS-07). */
    protected readonly relationshipFields = computed(() => {
        const typeName = this.state.typeName();
        const defs = this.state.entityDefsByName();
        const def = typeName ? defs.get(typeName) : undefined;

        return def ? buildRelationshipFields(def, defs, this.labels, this.state.relationshipDefs()) : [];
    });

    /** The picker values the form holds (EDT-15's seed, EDT-14's edits). They
     * ride their own signal, not the form model: a picker's value is a chip
     * list the save merges separately (EDT-16), not an attribute field. */
    protected readonly relationshipValues = signal<ReadonlyMap<string, readonly RelationshipPick[]>>(new Map());

    /**
     * Whether the form is the quality rule form (EDT-25, DD-477): the type is
     * the rule type and the rule is a vocabulary one — create mode always,
     * edit mode when the entity names a `dqcheckkind`. A legacy rule without
     * the kind stays in the generic form (EDT-29, DD-492): the quality form
     * offers only kinds, and converting one is a human act, not a rewrite.
     */
    protected readonly qualityMode = computed(
        () =>
            this.state.typeName() === QUALITY_TYPE_NAME &&
            (this.isCreate || storedCheckKind(this.state.entity()) !== ""),
    );

    /**
     * The pickers the template renders: the whole relationship set, or (in
     * quality mode, EDT-25) the rule's own `fields` end alone — the derived
     * typedefs also carry the DataSet/Referenceable lineage ends, which the
     * rule form has no business editing.
     */
    protected readonly renderedRelationshipFields = computed(() => {
        const all = this.relationshipFields();

        return this.qualityMode() ? all.filter((field) => field.name === QUALITY_FIELDS_RELATIONSHIP) : all;
    });

    /**
     * The pickers currently blocked by 18.3's parent choice (PME-10, DD-751):
     * a field of a parent group whose *other* members already hold a value.
     * Filling one member makes the others unfillable — the rule the server
     * enforces on save (PME-07), made impossible in the form instead of
     * reported after the fact. The check rides the picker values, so it moves
     * with the edits, and it never blocks a field that holds a value itself:
     * the one the user filled stays live, so it can be deleted and the choice
     * switched. A field with no parent group is never blocked.
     */
    protected readonly blockedRelationships = computed<ReadonlySet<string>>(() => {
        const held = new Set<string>();
        for (const field of this.relationshipFields()) {
            if (field.parentGroup !== undefined && (this.relationshipValues().get(field.name)?.length ?? 0) > 0) {
                held.add(field.parentGroup);
            }
        }
        if (held.size === 0) {
            return new Set<string>();
        }

        return new Set(
            this.relationshipFields()
                .filter(
                    (field) =>
                        field.parentGroup !== undefined &&
                        held.has(field.parentGroup) &&
                        (this.relationshipValues().get(field.name)?.length ?? 0) === 0,
                )
                .map((field) => field.name),
        );
    });

    /** Whether one picker is blocked by a filled sibling of its parent group
     * (PME-10). The template's disabled input.
     * @param field the picker's field
     */
    protected relationshipBlocked(field: RelationshipField): boolean {
        return this.blockedRelationships().has(field.name);
    }

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
     * The chosen tags (EDT-05, VDE-03) — the template's tag row. The box
     * holds names since 16.5c; the row keeps the raw name (the tooltip
     * lookup and the remove emit ride it); the chip's label is the
     * dictionary display name, rendered below (DD-379).
     */
    protected readonly chosenTags = computed(() =>
        this.state
            .chosen()
            .filter((name) => name !== "")
            .map((name) => ({ typeName: name })),
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
     * Edit mode's static type badge (EDT-04, DD-330): the type never
     * changes there. The badge is the shared type-name part in the details
     * header's shape — the entity's alias when it carries one, the display
     * name beside the raw type, the icon of the raw type (MMS-09, DD-721).
     * The legacy's type select shows the dictionary display name
     * (`translatedName`, `type-select.component.ts:116`), so the name is
     * `nameDisplay` of the raw name.
     */
    protected readonly staticTypeShown = computed(() => !this.isCreate && (this.state.entity()?.typeName ?? "") !== "");

    /** The badge's name: `nameDisplay` of the stored entity's raw type (DD-379). */
    protected readonly staticTypeName = computed(() => nameDisplay(this.state.entity()?.typeName ?? ""));

    /** The badge's alias (MMS-09): `attributes.typeAlias` of the stored entity (DET-26's reader). */
    protected readonly staticTypeAlias = computed(() => {
        const entity = this.state.entity();
        return this.isCreate || entity === null ? undefined : cardTypeAlias(entity);
    });

    /** The badge's icon (DD-378): the app's type map, resolved for the raw type name. */
    protected readonly staticTypeIcon = computed(() => typeIcon(this.state.entity()?.typeName ?? ""));

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

    /** The banner line's verdict icons (EDT-24, the legacy's pair). */
    protected readonly faCheckCircle = faCheckCircle;

    /** The banner line's warning icon (EDT-24). */
    protected readonly faExclamationTriangle = faExclamationTriangle;

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

    /**
     * The loading line's text (LR-002): the live region above the form is
     * always mounted — only its text comes and goes — so a screen reader
     * already watches a region before the line lands in it, instead of one
     * created and filled in the same frame.
     */
    protected readonly loadingText = computed(() =>
        this.state.loading() && this.state.entity() === null ? this.loadingLine : "",
    );

    /**
     * The commit outcome (LR-005): the save/delete success paths fill the
     * editor's persistent status line just before they navigate away, so
     * the outcome is said aloud and not only acted on.
     */
    protected readonly outcomeLine = signal("");

    /** Whether the last Save lost the version race (VDE-07, DD-610): one
     * line above the form says the entity changed since it opened — no
     * alert, no error page (DD-591's reload-and-reedit path). */
    protected readonly conflictShown = signal(false);

    /** The conflict line (VDE-07): the drawer stays open, the edits stay,
     * and a second Save carries the stored version. */
    protected readonly conflictLine = $localize`:@@search.components.editor.conflict:This entity changed since you opened it. Your edits are kept — save again to write them over the stored version.`;

    protected readonly savedLine = $localize`:@@search.components.editor.saved:Entity saved`;

    protected readonly deletedLine = $localize`:@@ENTITY_DELETE:Entity deleted`;

    /** The write-bus sequence last consumed — a tick from an earlier drawer
     * is not this editor's outcome (LR-005). */
    private initialWriteSeq = this.entityWritten.latest()?.seq ?? 0;

    /** The field-set signature the last build used (the rebuild guard). */
    private builtSignature = "";

    constructor() {
        this.state.mode.set(this.isCreate ? "create" : "edit");
        this.state.loadSlices();

        // The entity read follows the route's guid (EDT-02, VDE-01) — edit
        // mode only. The read door's client answers it (DD-608).
        effect(() => {
            const guid = this.guid();
            if (!this.isCreate && guid) {
                this.state.loadEntity(guid);
            }
        });

        // The form's type material follows the rendered type (VDE-02, AVW-11):
        // one chain read per type, cached by the door's client (DD-611). The
        // store guards the repeat, so a re-pick of the same type asks nothing.
        effect(() => {
            const typeName = this.state.typeName();
            if (typeName !== null) {
                this.state.loadChain(typeName);
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
                const seeded = new Map(
                    Object.entries(seedRelationshipValues(this.state.entity() ?? {}, this.relationshipFields())),
                );
                this.relationshipValues.set(seeded);
            }
        });

        // The write's outcome (LR-005, WFE-01, WFE-02): the store fires the
        // write tick with its outcome (DD-327, DD-803) just before it
        // navigates, so the tick is the success signal that reaches the
        // drawer before its view goes away — a refusal rides no tick, so
        // nothing fills the line and the alerts carry the refusal. The
        // sequence guard skips a tick from an earlier drawer. The outcome
        // arrives as data (WFE-01): a reworded delete or save line changes
        // no outcome (DD-802).
        effect(() => {
            const latest = this.entityWritten.latest();
            if (latest && latest.seq > this.initialWriteSeq) {
                this.initialWriteSeq = latest.seq;
                this.outcomeLine.set(latest.outcome === "deleted" ? this.deletedLine : this.savedLine);
            }
        });

        // The conflict's re-edit (VDE-07, DD-610): the store already moved
        // the base to the stored view and re-seeded the tag box; here every
        // control and picker the person never touched answers the stored
        // value, and every one they changed keeps their value — the value
        // comparison runs against the seed the old view gave (the signal
        // form exposes no dirty flag). The line says the entity changed
        // since it opened; the next Save rides the stored updateTime
        // because the body now merges onto the new base. A lost race is
        // not a mistake: no touched marking, no alert (DD-591).
        effect(() => {
            const event = this.state.conflict();
            if (event === null) {
                return;
            }
            this.values.set(valuesAfterConflict(event.from, event.to, this.fields(), this.values()));
            this.relationshipValues.set(
                picksAfterConflict(event.from, event.to, this.relationshipFields(), this.relationshipValues()),
            );
            this.conflictShown.set(true);
            untracked(() => this.state.conflictHandled());
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

        // The governance validation (EDT-23, DD-446): the draft rides the
        // validate-entity aux API when the form opens — the legacy's
        // entityDetails merge, immediate — and after every change debounced
        // 200 ms — the legacy's valueChanges.debounceTime(200). The re-run's
        // cleanup unsubscribes the in-flight request, so an older answer can
        // never land (the generation guard, DET-08's sibling). A failed call
        // renders no lines and alerts nothing (the quiet swallow, the
        // legacy's catchError-to-empty): the validation is advisory while a
        // record is drafted, and the drawer stays usable.
        effect((onCleanup) => {
            if (!this.formVisible()) {
                return;
            }
            // The chain answers first (VDE-02): in edit mode the for-type door
            // is asked from the view's type, so it lands a beat after the read
            // — and the draft's fields ride it. An open round before the chain
            // would validate a field set the form never shows.
            const renderedType = this.state.typeName();
            if (renderedType !== null && !this.state.chainDefs().some((def) => def.name === renderedType)) {
                return;
            }
            // The draft's sources, read so any change re-fires (EDT-23).
            const entity = this.state.entity();
            const fields = this.fields();
            const values = this.values();
            const relationshipFields = this.relationshipFields();
            const relationshipValues = this.relationshipValues();
            if (!entity?.typeName) {
                // Nothing to validate yet (the failed read, the bare create).
                this.validation.set(null);

                return;
            }
            const draft = () =>
                mergeRelationshipsOntoEntity(
                    mergeOntoEntity(entity, fields, values as Record<string, unknown>),
                    relationshipFields,
                    relationshipValues,
                );
            if (!this.validatedOpen) {
                this.validatedOpen = true;
                this.validateDraft(draft);

                return;
            }
            const timer = setTimeout(() => this.validateDraft(draft), 200);
            onCleanup(() => clearTimeout(timer));
        });
    }

    /** One validation round (EDT-23): the draft rides the aux API (EDT-21);
     * its answer replaces the verdicts, a failure clears them (DD-446 — the
     * quiet swallow, no alert). The in-flight subscription rides a field so
     * the effect's cleanup can drop it — the last draft wins. */
    private validateDraft(draft: () => Parameters<ValidateEntityService["validateEntity"]>[0]): void {
        this.validationPending?.unsubscribe();
        this.validationPending = this.validateEntity.validateEntity(draft()).subscribe({
            next: (answer) => {
                this.validationPending = null;
                this.validation.set(answer);
            },
            error: () => {
                this.validationPending = null;
                this.validation.set(null);
            },
        });
    }

    /** The verdicts that measure a rendered control (EDT-24 as amended by
     * 12.7/12.7a/12.7b, DD-498/DD-633/DD-636): the answer's flat array
     * grouped by the names a rule measures. A verdict rides its `attribute`
     * and every `anyOf` alternative (VEV-09), so it paints under each control
     * the rule names — once each, since the filter keeps one copy. The
     * description control borrows the `definition` verdict only while the form
     * has no `definition` control of its own — the legacy's one-way alias, and
     * each verdict sits once on a type that carries both. A control no rule
     * measures renders nothing; `unreadRules` renders no line (VEV-03). */
    protected validationItems(name: string): readonly GovernanceVerdict[] {
        const answer = this.validation();
        if (!answer) {
            return [];
        }
        // While the form has no `definition` control, the description control
        // borrows the `definition` verdict (the legacy's alias). With both
        // controls rendered, each verdict names its own (DD-633).
        const hasDefinitionControl = this.fields().some((field) => field.name === "definition");
        const keys = (GOV_CARD_KEYS[name] ?? [name]).filter(
            (key) => !(name === "description" && hasDefinitionControl && key === "definition"),
        );

        return answer.verdicts.filter((verdict) =>
            [verdict.attribute, ...(verdict.anyOf ?? [])].some((measured) => keys.includes(measured)),
        );
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

    /** The chip's tooltip: the classification def's description (UIC-16),
     * read off the classification slice (VDE-02, DD-612). */
    protected chipTooltip(typeName: string): string | undefined {
        return this.state.classificationDescription(typeName);
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

    /** Whether a required picker is empty (EDT-17): an invalid form, one more
     * way. A picker the parent choice blocks (PME-10) stands down — its
     * emptiness is the rule working, not a missing value, and a disabled
     * control the user cannot fill must never hold the save hostage. */
    protected relationshipInvalid(field: RelationshipField): boolean {
        return field.required && !this.relationshipBlocked(field) && this.picksOf(field).length === 0;
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

    /** Whether the required-fields notification shows (EDT-07/EDT-17). The
     * quality form carries its own notification (EDT-28: the engine's line
     * leads there), so the drawer's stands down in quality mode. */
    protected notificationShown(): boolean {
        return (
            !this.qualityMode() &&
            this.saveAttempted() &&
            (this.formInvalid() || this.relationshipsMissing()) &&
            !this.notificationDismissed()
        );
    }

    /**
     * The door body for the current draft (VDE-03/04/05, DD-609/612): the base
     * view (edit) or null (create), the merged attribute map, the tag box's
     * names, and one `sections` entry per picker this call renders. The quality
     * branch passes its minimal rule body (EDT-27) and only the `fields` end.
     * @param overrides the quality branch's full attribute map and rendered pickers
     */
    private doorBody(overrides: Partial<Parameters<typeof bodyFromEdits>[0]> = {}): ReturnType<typeof bodyFromEdits> {
        const entity = this.state.entity();

        return bodyFromEdits({
            base: this.state.view(),
            entity: entity ?? {},
            typeName: entity?.typeName ?? "",
            fields: this.fields(),
            values: this.values() as Record<string, unknown>,
            relationshipFields: this.relationshipFields(),
            relationshipValues: this.relationshipValues(),
            classifications: this.state.chosen(),
            ...overrides,
        });
    }

    /**
     * Save (EDT-06/07/16, VDE-05): invalid (a control, or a required picker
     * with no chip, EDT-17) bails marked-touched; valid posts one mutation-door
     * body (DD-609) — attributes, tags, ends, and meanings in one request.
     * The quality branch (EDT-28, DD-477) answers first: the draft rides the
     * validate endpoint before the door POST, whose body is the minimal
     * quality body (EDT-27).
     */
    protected save(): void {
        this.saveAttempted.set(true);
        this.notificationDismissed.set(false);
        const qualityForm = this.qualityForm();
        if (this.qualityMode() && qualityForm) {
            this.saveQualityRule(qualityForm);

            return;
        }
        const formState = this.form()();
        if (formState.invalid() || this.relationshipsMissing()) {
            formState.markAsTouched();

            return;
        }
        const entity = this.state.entity();
        if (!entity?.typeName) {
            return;
        }

        this.state.save(this.doorBody());
    }

    /**
     * The quality-mode Save (EDT-28, DD-476/DD-477, VDE-11): the draft's
     * stored-rule attributes ride 12.5's validate call first — a rule never
     * saves unchecked. `{valid: true}` continues with the door save over the
     * minimal body (EDT-27) plus the pickers rendered by quality mode (the
     * `fields` end); `{valid: false}` answers the engine's reason in the
     * child's notification line and does not POST (a later edit clears it,
     * EDT-28); a transport or non-2xx failure answers the generic "could not
     * check" line instead. The form's own completeness (name, kind, the
     * kind's required parameters — EDT-07's rule in quality mode) bails
     * before the call: an incomplete draft has nothing to check.
     */
    private saveQualityRule(qualityForm: QualityFields): void {
        qualityForm.clearEngineError();
        if (!qualityForm.valid()) {
            return;
        }
        const entity = this.state.entity();
        if (!entity?.typeName) {
            return;
        }
        const attributes = qualityForm.draftAttributes();
        this.qualityRule.validateRule(attributes).subscribe({
            next: (answer) => {
                if (answer.valid) {
                    this.state.save(
                        this.doorBody({
                            attributes,
                            relationshipFields: this.renderedRelationshipFields(),
                        }),
                    );
                } else {
                    qualityForm.showEngineReason(answer.reason ?? "");
                }
            },
            error: () => qualityForm.showTransportFailure(),
        });
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
