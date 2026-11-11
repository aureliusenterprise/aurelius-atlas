import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal } from "@angular/core";
import { Subscription } from "rxjs";

import { ClassificationChip, Select } from "aurelius-atlas-ui";
import { QualityRuleService, type AtlasEntity, type QualityKind, type QualityKinds } from "aurelius-atlas-data-access";

/** The editor drawer this form belongs to (EDT-25): the rule type. */
export const QUALITY_TYPE_NAME = "m4i_data_quality";

/** The rule's relationship to the fields it measures (DET-35's box seeds
 * from its other end): the one picker the quality form renders (EDT-25). */
export const QUALITY_FIELDS_RELATIONSHIP = "fields";

/** One parameter's control kind (EDT-26's map): text, a chips box, a number,
 * a whole number, or a Select over the resource's castable types. */
type ParamKind = "text" | "chips" | "number" | "integer" | "type";

/**
 * The parameter table (EDT-26): the engine's parameter name, the control it
 * rides, and the label the vocabulary patch's attribute definition carries
 * (`001-data_quality_vocabulary.json`). A parameter the table does not name
 * renders as text (DD-478's consequence): a kind added to the engine appears
 * in the form with no webapp change.
 */
const PARAMS: Readonly<Record<string, { kind: ParamKind; label: string; stored: string }>> = {
    column: { kind: "text", label: "Column", stored: "dqcolumn" },
    pattern: { kind: "text", label: "Pattern", stored: "dqpattern" },
    values: { kind: "chips", label: "Values", stored: "dqvalues" },
    columns: { kind: "chips", label: "Columns", stored: "dqcolumns" },
    otherColumn: { kind: "text", label: "Other Column", stored: "dqotherColumn" },
    type: { kind: "type", label: "Type", stored: "dqtype" },
    min: { kind: "number", label: "Minimum", stored: "dqmin" },
    max: { kind: "number", label: "Maximum", stored: "dqmax" },
    maxAgeHours: { kind: "number", label: "Max Age Hours", stored: "dqmaxAgeHours" },
    minColumns: { kind: "integer", label: "Min Columns", stored: "dqminColumns" },
};

/**
 * The human name of each check kind (EDT-31, DD-480): webapp copy in both
 * catalogues, keyed by the engine's name. A kind the table does not name
 * falls back to its raw name (a new engine kind still renders, untranslated).
 * The stored value and the validate body keep the engine's names.
 */
const KIND_NAMES: Readonly<Record<string, string>> = {
    COLUMN_COMPOSITE_UNIQUE: $localize`:@@search.components.editor.dataQualityRule.kind.COLUMN_COMPOSITE_UNIQUE:Composite unique`,
    COLUMN_EQUALS_COLUMN_RATIO: $localize`:@@search.components.editor.dataQualityRule.kind.COLUMN_EQUALS_COLUMN_RATIO:Columns match`,
    COLUMN_IN_SET: $localize`:@@search.components.editor.dataQualityRule.kind.COLUMN_IN_SET:Values from a set`,
    COLUMN_MATCHES_REGEX: $localize`:@@search.components.editor.dataQualityRule.kind.COLUMN_MATCHES_REGEX:Matches a pattern`,
    COLUMN_NOT_NULL_RATIO: $localize`:@@search.components.editor.dataQualityRule.kind.COLUMN_NOT_NULL_RATIO:Not empty`,
    COLUMN_TYPE_CASTABLE: $localize`:@@search.components.editor.dataQualityRule.kind.COLUMN_TYPE_CASTABLE:Convertible type`,
    COLUMN_UNIQUE_RATIO: $localize`:@@search.components.editor.dataQualityRule.kind.COLUMN_UNIQUE_RATIO:No duplicates`,
    COLUMN_WITHIN_RANGE: $localize`:@@search.components.editor.dataQualityRule.kind.COLUMN_WITHIN_RANGE:Within a range`,
    ROW_FRESHNESS_MAX_AGE: $localize`:@@search.components.editor.dataQualityRule.kind.ROW_FRESHNESS_MAX_AGE:Fresh rows`,
    ROW_NOT_EMPTY: $localize`:@@search.components.editor.dataQualityRule.kind.ROW_NOT_EMPTY:Row filled`,
};

/**
 * The one-line description of each check kind (EDT-31): what the check
 * looks for, in plain words, shown when the kind is picked. A kind the
 * table does not name shows no line.
 */
const KIND_DESCRIPTIONS: Readonly<Record<string, string>> = {
    COLUMN_COMPOSITE_UNIQUE: $localize`:@@search.components.editor.dataQualityRule.kindDescription.COLUMN_COMPOSITE_UNIQUE:The chosen columns together never repeat across rows.`,
    COLUMN_EQUALS_COLUMN_RATIO: $localize`:@@search.components.editor.dataQualityRule.kindDescription.COLUMN_EQUALS_COLUMN_RATIO:Two columns hold the same value in at least part of the rows.`,
    COLUMN_IN_SET: $localize`:@@search.components.editor.dataQualityRule.kindDescription.COLUMN_IN_SET:Every value comes from the list you set.`,
    COLUMN_MATCHES_REGEX: $localize`:@@search.components.editor.dataQualityRule.kindDescription.COLUMN_MATCHES_REGEX:Every value follows the text pattern you set.`,
    COLUMN_NOT_NULL_RATIO: $localize`:@@search.components.editor.dataQualityRule.kindDescription.COLUMN_NOT_NULL_RATIO:One column carries a value in at least part of the rows.`,
    COLUMN_TYPE_CASTABLE: $localize`:@@search.components.editor.dataQualityRule.kindDescription.COLUMN_TYPE_CASTABLE:Every value converts to the type you set.`,
    COLUMN_UNIQUE_RATIO: $localize`:@@search.components.editor.dataQualityRule.kindDescription.COLUMN_UNIQUE_RATIO:One column's values repeat no more than the share you set.`,
    COLUMN_WITHIN_RANGE: $localize`:@@search.components.editor.dataQualityRule.kindDescription.COLUMN_WITHIN_RANGE:Every value sits between the minimum and the maximum.`,
    ROW_FRESHNESS_MAX_AGE: $localize`:@@search.components.editor.dataQualityRule.kindDescription.ROW_FRESHNESS_MAX_AGE:Rows were written no longer ago than the age you set.`,
    ROW_NOT_EMPTY: $localize`:@@search.components.editor.dataQualityRule.kindDescription.ROW_NOT_EMPTY:Every row carries all of the chosen columns.`,
};

/**
 * The human name of each dimension (EDT-31): the same copy rule as the
 * kinds, keyed by the engine's name, raw name as the fallback.
 */
const DIMENSION_NAMES: Readonly<Record<string, string>> = {
    ACCURACY: $localize`:@@search.components.editor.dataQualityRule.dimension.ACCURACY:Accuracy`,
    COMPLETENESS: $localize`:@@search.components.editor.dataQualityRule.dimension.COMPLETENESS:Completeness`,
    TIMELINESS: $localize`:@@search.components.editor.dataQualityRule.dimension.TIMELINESS:Timeliness`,
    UNIQUENESS: $localize`:@@search.components.editor.dataQualityRule.dimension.UNIQUENESS:Uniqueness`,
    VALIDITY: $localize`:@@search.components.editor.dataQualityRule.dimension.VALIDITY:Validity`,
};

/** One parameter row for the template: the engine's name and its rendering. */
export type QualityParamField = {
    readonly name: string;
    readonly stored: string;
    readonly label: string;
    readonly kind: ParamKind;
    readonly required: boolean;
};

/** The values the quality form holds (EDT-26/27): the shared fields and the
 * chosen kind's parameters, as the controls hold them (texts and numbers as
 * typed strings, the chips as lists). */
type QualityValues = {
    readonly name: string;
    readonly ruleDescription: string;
    readonly kind: string;
    readonly active: boolean;
    readonly threshold: string;
    readonly params: Readonly<Record<string, string | string[]>>;
};

/** A Select row over a string (the kinds, the castable types). */
type Row = { name: string; label: string };

/** Whether a stored attribute value is a usable vocabulary kind name (EDT-25/29). */
export function storedCheckKind(entity: AtlasEntity | null): string {
    const raw = entity?.attributes?.["dqcheckkind"];

    return typeof raw === "string" && raw !== "" ? raw : "";
}

/**
 * The quality rule form (EDT-25..EDT-27/29, DD-477/DD-478): the drawer's
 * branch for `m4i_data_quality`. It replaces the generic attribute form —
 * the field set would draw all twelve `dq` attributes for every kind and
 * accept a shape the engine rejects (DQS-08). The kind list, the dimension,
 * and the parameter set come from the served vocabulary (QRE-01 through
 * {@link QualityRuleService}, the only caller of the route); the typedefs
 * draw nothing here (DD-478). The editor drawer owns the Save button: this
 * component answers {@link valid} and {@link draftAttributes}, and renders
 * the engine's verdict line the drawer hands it (EDT-28).
 *
 * The values ride one signal record and plain handlers, not the signals
 * schema (DD-478): the field set changes with every kind switch, which a
 * static schema cannot express. The Save's required rule (EDT-07's, shared):
 * a name, a kind, and every required parameter of that kind.
 */
@Component({
    imports: [ClassificationChip, Select],
    selector: "aurelius-atlas-webapp-quality-fields",
    templateUrl: "./quality-fields.html",
    styleUrl: "./quality-fields.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QualityFields {
    /** The entity being edited (edit mode) — the seed source (EDT-29);
     * create passes the seeded entity for its `qualifiedName` and `id`. */
    readonly entity = input.required<AtlasEntity | null>();

    /** The drawer's mode: create defaults `active` to checked (EDT-27). */
    readonly mode = input.required<"create" | "edit">();

    /** Whether a Save was attempted — shows the required line (EDT-07). */
    readonly saveAttempted = input(false);

    /** Whether the notification's X hid it (DD-331, the drawer's state). */
    readonly notificationDismissed = input(false);

    /** The loading line's text, the drawer's (EDT-25's "the drawer's loading line"). */
    readonly loadingLabel = input("");

    /** The notification's X (the drawer's dismissal, DD-331). */
    readonly dismissed = output<void>();

    private readonly qualityRule = inject(QualityRuleService);

    /** The vocabulary's load state (EDT-25): while it loads the form is the
     * loading line; a failure says so and offers nothing (the save stays
     * closed — there is no kind to draft without it). */
    protected readonly kindsState = signal<"loading" | "failed" | "ready">("loading");

    /** The vocabulary answer once loaded (the kind rows, the castable types). */
    private readonly vocabulary = signal<QualityKinds | null>(null);

    /** The kinds call (the drawer's dismissal cannot cancel it; the service
     * caches the answer for every later open, EDT-30). */
    private kindsSubscription: Subscription | null = null;

    /** The form's values (EDT-26/27). */
    protected readonly values = signal<QualityValues>({
        name: "",
        ruleDescription: "",
        kind: "",
        active: true,
        threshold: "",
        params: {},
    });

    /** The engine's or the transport's line (EDT-28): set by the drawer after
     * the validate call, cleared by any edit (EDT-28's "a later edit") and
     * by the next Save. */
    readonly engineError = signal<string | null>(null);

    /** The chips box's typed text (one box is ever on screen: a kind carries
     * `values` or `columns`, never both). */
    protected readonly chipText = signal("");

    /** The entity guid the values were seeded from (the seed runs once). */
    private seededFrom: string | null = null;

    constructor() {
        // The vocabulary loads on open (EDT-25); the service caches after its
        // first success, so a second drawer open answers without a call.
        this.kindsSubscription = this.qualityRule.kinds().subscribe({
            next: (answer) => {
                this.kindsSubscription = null;
                this.vocabulary.set(answer);
                this.kindsState.set("ready");
            },
            error: () => {
                this.kindsSubscription = null;
                this.kindsState.set("failed");
            },
        });

        // The seed (EDT-29): an existing rule opens with its kind, the kind's
        // parameters, its `active` and `threshold` — under the EDT-26 names,
        // foreign stored `dq` attributes ignored (only the kind's own render,
        // and DD-461 keeps them out of the engine's draft).
        effect(() => {
            const entity = this.entity();
            const guid = entity?.guid ?? null;
            if (entity === null || guid === null || guid === this.seededFrom || this.kindsState() === "loading") {
                return;
            }
            this.seededFrom = guid;
            const kind = storedCheckKind(entity);
            const attributes = entity.attributes ?? {};
            const params: Record<string, string | string[]> = {};
            for (const name of this.paramNamesOf(kind)) {
                const raw = attributes[PARAMS[name]?.stored ?? ""];
                if (typeof raw === "string") {
                    params[name] = raw;
                } else if (Array.isArray(raw)) {
                    params[name] = raw.map((value) => String(value ?? ""));
                } else if (typeof raw === "number") {
                    params[name] = String(raw);
                }
            }
            const threshold = attributes["threshold"];
            this.values.set({
                name: typeof attributes["name"] === "string" ? (attributes["name"] as string) : "",
                ruleDescription:
                    typeof attributes["ruleDescription"] === "string" ? (attributes["ruleDescription"] as string) : "",
                kind,
                active: this.mode() === "create" ? true : attributes["active"] === true,
                threshold: typeof threshold === "number" ? String(threshold) : "",
                params,
            });
        });
    }

    /** The kind rows (EDT-25, EDT-31): the resource's order, each labelled
     * by its human name — the raw engine name is never shown. Rebuilt per
     * answer; the Select matches its value by identity. */
    protected readonly kindRows = computed<Row[]>(() =>
        (this.vocabulary()?.kinds ?? []).map((kind) => ({
            name: kind.name,
            label: KIND_NAMES[kind.name] ?? kind.name,
        })),
    );

    /** The chosen kind's description line (EDT-31): shown between the kind
     * and the dimension, empty for a kind the catalogue does not name. */
    protected readonly kindDescription = computed<string>(() => KIND_DESCRIPTIONS[this.values().kind] ?? "");

    /** The kind Select's selected row, off the values (identity match). */
    protected readonly kindSelected = computed<Row | null>(
        () => this.kindRows().find((row) => row.name === this.values().kind) ?? null,
    );

    /** The chosen kind's resource entry, or null before the first pick. */
    protected readonly selectedKind = computed<QualityKind | null>(
        () => (this.vocabulary()?.kinds ?? []).find((kind) => kind.name === this.values().kind) ?? null,
    );

    /** The parameter controls (EDT-25/26): the chosen kind's required then
     * optional parameters, in the order the resource lists them. */
    protected readonly paramFields = computed<QualityParamField[]>(() => {
        const kind = this.selectedKind();
        if (kind === null) {
            return [];
        }

        return [
            ...kind.required.map((name) => this.paramFieldOf(name, true)),
            ...kind.optional.map((name) => this.paramFieldOf(name, false)),
        ];
    });

    /** The castable-types rows for the `type` parameter (EDT-26). */
    protected readonly typeRows = computed<Row[]>(() =>
        (this.vocabulary()?.castableTypes ?? []).map((value) => ({ name: value, label: value })),
    );

    /** The `type` Select's selected row, off the values (identity match). */
    protected readonly typeSelected = computed<Row | null>(() => {
        const current = this.values().params["type"];
        const text = typeof current === "string" ? current : "";

        return this.typeRows().find((row) => row.name === text) ?? null;
    });

    /** The read-only dimension line (EDT-25, EDT-31): the kind's own
     * dimension, in its human name (raw engine name as the fallback). */
    protected readonly dimensionText = computed(() => {
        const dimension = this.selectedKind()?.dimension ?? "";

        return DIMENSION_NAMES[dimension] ?? dimension;
    });

    /** The slider's low bound (EDT-32, DD-481): the served
     * `thresholdMin` (QRE-01), 0 before the vocabulary loads. */
    protected readonly thresholdMin = computed(() => this.vocabulary()?.thresholdMin ?? 0);

    /** The slider's high bound (EDT-32): the served `thresholdMax`, 1
     * before the vocabulary loads. */
    protected readonly thresholdMax = computed(() => this.vocabulary()?.thresholdMax ?? 1);

    /** The slider's position (EDT-32): the typed threshold, or the engine's
     * default 1.0 while the number field is empty — the resting place the
     * default shows without writing a value (EDT-27's empty rule). */
    protected readonly thresholdSliderValue = computed(() => {
        const text = this.values().threshold.trim();
        const parsed = text === "" ? Number.NaN : Number(text);
        const value = Number.isNaN(parsed) ? 1.0 : parsed;

        return Math.min(Math.max(value, this.thresholdMin()), this.thresholdMax());
    });

    /** Whether the kind is chosen (a required half of EDT-07's rule here). */
    protected readonly kindMissing = computed(() => this.values().kind === "");

    /** Whether the form can draft a rule the engine could read (EDT-07's
     * quality-mode shape): a name, a kind, and every required parameter. */
    valid(): boolean {
        const values = this.values();

        return (
            values.name.trim() !== "" &&
            values.kind !== "" &&
            this.paramFields()
                .filter((field) => field.required)
                .every((field) => this.paramFilled(field.name))
        );
    }

    /**
     * The draft's stored-rule attributes for the validate call and the save
     * (EDT-27): the shared fields, `active`, `threshold`, `dqcheckkind`, and
     * only the chosen kind's `dq` parameters — never an attribute the kind
     * does not name, so no foreign or stale parameter rides a rule (DD-461
     * keeps the stored ones out of the engine anyway). The mandatory
     * `qualifiedName` and `id` ride the entity (EVL-02: a full update demands
     * them; the legacy editor's create seeds `id` -1, the same idiom,
     * `gov-quality-editor.component.ts:67`). An empty threshold means the
     * engine's default 1.0 — sent as 1.0, because the store would otherwise
     * materialize the omitted double to 0.0 (EWR-09).
     * @returns the attributes, in the names the store keeps (DQ-01)
     */
    draftAttributes(): Record<string, unknown> {
        const values = this.values();
        const entity = this.entity();
        const attributes: Record<string, unknown> = {
            name: values.name.trim(),
            id: this.mode() === "create" ? -1 : (entity?.attributes?.["id"] ?? -1),
            active: values.active,
            threshold: values.threshold.trim() === "" ? 1.0 : Number(values.threshold),
            dqcheckkind: values.kind,
        };
        const qualifiedName = entity?.attributes?.["qualifiedName"];
        if (typeof qualifiedName === "string" && qualifiedName !== "") {
            attributes["qualifiedName"] = qualifiedName;
        }
        if (values.ruleDescription.trim() !== "") {
            attributes["ruleDescription"] = values.ruleDescription.trim();
        }

        return Object.assign(attributes, this.paramAttributes());
    }

    /** The chosen kind's `dq` parameters as stored attributes: only the kind
     * names (EDT-27), empty controls absent. A number parses; an unparsed
     * number text never reaches the body (the engine reads numbers). */
    private paramAttributes(): Record<string, unknown> {
        const attributes: Record<string, unknown> = {};
        for (const field of this.paramFields()) {
            const raw = this.values().params[field.name];
            if (typeof raw === "string") {
                const text = raw.trim();
                const numeric = field.kind === "number" || field.kind === "integer";
                if (text !== "" && !(numeric && Number.isNaN(Number(text)))) {
                    attributes[field.stored] = numeric ? Number(text) : text;
                }
            } else if (Array.isArray(raw) && raw.length > 0) {
                attributes[field.stored] = raw;
            }
        }

        return attributes;
    }

    /** The engine's verdict line (EDT-28): the drawer hands it the reason. */
    showEngineReason(reason: string): void {
        this.engineError.set(reason);
    }

    /** The generic "could not check" line (EDT-28): a validate call that
     * failed on transport or a non-2xx. The string rides the catalogue. */
    showTransportFailure(): void {
        this.engineError.set(
            $localize`:@@search.components.editor.dataQualityRule.couldNotCheck:The rule could not be checked against the server. Try again.`,
        );
    }

    /** The next Save re-arms the line (EDT-28: the line answers the last try). */
    clearEngineError(): void {
        this.engineError.set(null);
    }

    /** The name field's text (EDT-27). */
    protected nameChanged(text: string): void {
        this.touch((current) => ({ ...current, name: text }));
    }

    /** The rule-description field's text (EDT-27, the legacy's
     * `ruleDescription`, label carried from `govQuality.ruleDescription`). */
    protected ruleDescriptionChanged(text: string): void {
        this.touch((current) => ({ ...current, ruleDescription: text }));
    }

    /** Choose or switch the kind (EDT-26): the old kind's parameters clear,
     * the same switch EDT-04's type pick does. */
    protected kindPicked(row: Row | null): void {
        this.touch((current) => ({ ...current, kind: row?.name ?? "", params: {} }));
    }

    /** The `active` checkbox (EDT-27). */
    protected activeChanged(checked: boolean): void {
        this.touch((current) => ({ ...current, active: checked }));
    }

    /** The threshold field's text (EDT-27: 0..1, empty is the engine's 1.0).
     * The slider and the number field both ride it (EDT-32: one value, both
     * move). */
    protected thresholdChanged(text: string): void {
        this.touch((current) => ({ ...current, threshold: text }));
    }

    /** A text/number parameter field's text (EDT-26). */
    protected paramChanged(name: string, text: string): void {
        this.touch((current) => ({ ...current, params: { ...current.params, [name]: text } }));
    }

    /** The `type` Select's pick (EDT-26). */
    protected typePicked(row: Row | null): void {
        this.touch((current) => ({ ...current, params: { ...current.params, type: row?.name ?? "" } }));
    }

    /** The chips box's typed text (EDT-26's list control). */
    protected chipTextChanged(text: string): void {
        this.chipText.set(text);
    }

    /** Enter commits the typed value as a chip (the classification box's
     * rule, DD-335): trimmed, non-empty, never a duplicate of a chip the
     * box already holds. The text clears only on a real add. */
    protected addChip(name: string): void {
        const text = this.chipText().trim();
        if (text === "") {
            return;
        }
        const current = this.values().params[name];
        const list = Array.isArray(current) ? current : [];
        if (list.includes(text)) {
            this.chipText.set("");

            return;
        }
        this.touch((values) => ({ ...values, params: { ...values.params, [name]: [...list, text] } }));
        this.chipText.set("");
    }

    /** Remove one chip (the value list is the field's full value). */
    protected removeChip(name: string, index: number): void {
        const current = this.values().params[name];
        const list = Array.isArray(current) ? current : [];
        this.touch((values) => ({
            ...values,
            params: { ...values.params, [name]: list.filter((_, i) => i !== index) },
        }));
    }

    /** The chips a parameter box holds (EDT-26). */
    protected chipsOf(name: string): readonly string[] {
        const current = this.values().params[name];

        return Array.isArray(current) ? current : [];
    }

    /** A text/number parameter's value as text (the input's own value). */
    protected paramText(name: string): string {
        const current = this.values().params[name];

        return typeof current === "string" ? current : "";
    }

    /** Whether the notification shows (EDT-07 as DD-331): the engine line, or
     * a Save tried over an incomplete form, until the X hides it. */
    protected notificationShown(): boolean {
        if (this.notificationDismissed()) {
            return false;
        }

        return this.engineError() !== null || (this.saveAttempted() && !this.valid());
    }

    /** The notification's line: the engine's answer leads, the required
     * line answers a Save over the incomplete form. */
    protected notificationLine(): string {
        return this.engineError() ?? this.requiredLine;
    }

    /** The required-fields line (EDT-07's, the drawer's key: the quality
     * form's gaps are the same kind of gap). */
    protected readonly requiredLine = $localize`:@@search.components.editor.attribute.notification:This entity can't be saved because one or more required fields are missing.`;

    /** The shared-field labels (DV-148: the legacy's quality keys carry
     * over). The trailing star the catalogue bakes into `govQuality.name`
     * drops — the template paints its own red one (DD-356). */
    protected readonly nameLabel = $localize`:@@search.components.editor.govQuality.name:Name`;

    protected readonly ruleDescriptionLabel = $localize`:@@search.components.editor.govQuality.ruleDescription:Rule description`;

    protected readonly dimensionLabel = $localize`:@@search.components.editor.govQuality.dimension:Dimension`;

    /** The vocabulary's own labels (EDT-25/27). */
    protected readonly kindLabel = $localize`:@@search.components.editor.dataQualityRule.checkKind:Check kind`;

    protected readonly activeLabel = $localize`:@@search.components.editor.dataQualityRule.active:Active`;

    protected readonly thresholdLabel = $localize`:@@search.components.editor.dataQualityRule.threshold:Threshold`;

    /** The chips box's placeholder (EDT-26, the classification box's shape). */
    protected readonly addValueLabel = $localize`:@@search.components.editor.dataQualityRule.addValue:Add a value...`;

    /** The kinds load failed (EDT-25): the form says so and offers nothing. */
    protected readonly kindsFailedLine = $localize`:@@search.components.editor.dataQualityRule.kindsFailed:The rule kinds could not be loaded.`;

    /** The notification's X label (the drawer's, DD-331). */
    protected readonly closeLabel = $localize`:@@components.modal.close:Close`;

    /** The chips' delete label (the drawer's, UIC-24). */
    protected readonly deleteLabel = $localize`:@@search.components.editor.delete:Delete`;

    /** The name label without the catalogue's baked-in star (DD-356): the
     * backward scan of `form-fields.ts`, no regex (S5852). */
    protected readonly nameLabelStripped = computed(() => {
        const trimmed = this.nameLabel.trimEnd();
        let end = trimmed.length;
        while (end > 0 && (trimmed.charAt(end - 1) === "*" || trimmed.charAt(end - 1) === " ")) {
            end -= 1;
        }

        return trimmed.slice(0, end);
    });

    /** One edit: write the values and drop the verdict line (EDT-28's
     * "a later edit clears the line"). */
    private touch(edit: (current: QualityValues) => QualityValues): void {
        this.values.update(edit);
        this.engineError.set(null);
    }

    /** The chosen kind's parameter names (required then optional). */
    private paramNamesOf(kindName: string): readonly string[] {
        const kind = (this.vocabulary()?.kinds ?? []).find((entry) => entry.name === kindName);

        return kind === undefined ? [] : [...kind.required, ...kind.optional];
    }

    /** Whether a required parameter carries a value (EDT-07's check). */
    private paramFilled(name: string): boolean {
        const raw = this.values().params[name];
        if (typeof raw === "string") {
            return raw.trim() !== "";
        }

        return Array.isArray(raw) && raw.length > 0;
    }

    /** The parameter row: the table's entry, or a text row for a parameter
     * the table never saw (DD-478's consequence: a new kind still renders). */
    private paramFieldOf(name: string, required: boolean): QualityParamField {
        const known = PARAMS[name];

        return known === undefined
            ? { name, stored: `dq${name}`, label: name, kind: "text", required }
            : { name, stored: known.stored, label: known.label, kind: known.kind, required };
    }
}
