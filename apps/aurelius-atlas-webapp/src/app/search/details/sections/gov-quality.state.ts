import { computed, inject, Injectable, signal } from "@angular/core";
import {
    SearchService,
    ValidateEntityService,
    type EntityValidationResponse,
    type EntityView,
    type GovernanceVerdict,
    type SearchParameters,
} from "aurelius-atlas-data-access";

/** The rule type's own name: the box lists the rules written for a type (DET-42). */
const RULE_TYPE_NAME = "m4i_gov_data_quality";

/**
 * The rule read's page size: the corpus is dozens of rules per type (the
 * demo's largest type carries a few dozen), so one page holds the box
 * (DD-520). No marker walk: a truncated box is an honest partial, and a
 * per-type prefix filter cannot reach one on the demo corpus.
 */
const RULE_LIMIT = 100;

/** The attributes the rule search answers (DET-42): what a row shows. */
const RULE_ATTRIBUTES = ["name", "ruleDescription", "qualityDimension", "active"] as const;

/**
 * One Governance Quality Rules row (DET-42): a rule of the opened entity's
 * type and its verdict for that record. `compliant` is the aux API's
 * verdict — true, false, or null for no verdict at all (the unread rule of
 * VEV-03, which renders no icon).
 */
export interface GovQualityRow {
    /** The rule entity's guid — the title's details link (DET-42). */
    readonly guid: string;
    /** The rule's name: the card title, the legacy card's link text. */
    readonly name: string;
    /** The rule's `ruleDescription`, the body's first line; empty when it stores none. */
    readonly description: string;
    /** The rule's dimension, titlecased by the renderer; empty when it stores none. */
    readonly dimension: string;
    /** The rule's verdict for the opened record; null with no verdict line. */
    readonly compliant: boolean | null;
}

/** The state of one read round: a superseded round's answer paints nothing. */
interface GovQualityRecord {
    /** The entity this round reads for, or null for the cleared box. */
    entity: EntityView | null;
    /** The rules the search answered, sorted by name (DET-42). */
    rules: { guid: string; name: string; description: string; dimension: string }[];
    /** The verdicts by rule guid (the aux API's join key, DD-520). */
    verdicts: Map<string, GovernanceVerdict>;
    /** Whether the rule read is in flight. */
    loading: boolean;
}

/**
 * The Governance Quality Rules box of the details screen (DET-42, DD-520):
 * the rules written for the opened entity's type, each with its verdict for
 * that record.
 *
 * The legacy box read the retired `atlas-dev-gov-quality` engine (DV-155,
 * ADR 060). The store holds the rules — the ACTIVE `m4i_gov_data_quality`
 * entities whose `qualifiedName` starts with `<typeName>--`, the rule→type
 * rule LAS-13 states — and 12.7's verdicts are the product's live answers
 * (VEV-02), so the box reads both: a basic search of the rules, and the
 * editor's own validate call over the opened entity, joined on `ruleGuid`.
 * ACTIVE is 12.2's reading (VEV-03): only a false `active` is not.
 *
 * Both calls fail quietly (DD-521, the EDT-23 swallow): no rules, no lines,
 * no alert. The store is per-screen (provided by `Details`): {@link load}
 * re-runs on every entity arrival, and a superseded round paints nothing
 * (the generation guard, DET-08's sibling).
 */
@Injectable()
export class DetailsGovQualityState {
    private readonly search = inject(SearchService);

    private readonly validateEntity = inject(ValidateEntityService);

    /** The read generation: a re-load drops every in-flight answer. */
    private generation = 0;

    private readonly record = signal<GovQualityRecord>({
        entity: null,
        rules: [],
        verdicts: new Map(),
        loading: false,
    });

    /** The rows the box renders, in name order (DET-42). Empty for no entity. */
    readonly rows = computed<GovQualityRow[]>(() => {
        const { rules, verdicts } = this.record();
        return rules.map((rule) => {
            const verdict = verdicts.get(rule.guid);
            return {
                guid: rule.guid,
                name: rule.name,
                description: rule.description,
                dimension: rule.dimension,
                compliant: verdict === undefined ? null : verdict.compliant === true,
            };
        });
    });

    /** Whether a read is in flight (the box shows nothing while loading, DET-42). */
    readonly loading = computed(() => this.record().loading);

    /**
     * (Re-)read the box for one entity (DET-42): the rules of its type,
     * then the verdicts over it. A null entity clears the box. Every
     * arrival — the editor's save re-read among them — re-reads from
     * scratch, the sections store's rule (DD-327's sibling). Since 16.5b
     * the opened entity arrives as the view (VDR-01): the rules search
     * reads only its type name, and the aux validate call reads only its
     * attributes (VEV-01), which the view answers as the entity GET did.
     * @param entity the read door's answer for the opened entity, or null
     */
    load(entity: EntityView | null): void {
        this.generation++;
        const generation = this.generation;
        if (entity === null) {
            this.record.set({ entity: null, rules: [], verdicts: new Map(), loading: false });
            return;
        }

        this.record.set({ entity, rules: [], verdicts: new Map(), loading: true });
        this.readRules(entity, generation);
        this.readVerdicts(entity, generation);
    }

    /**
     * The rules of the entity's type (DET-42): one basic search, the
     * qualified-name prefix the server filters (DD-520). A failed answer
     * keeps the box empty and alerts nothing (DD-521); a loading flag
     * clears with the round.
     * @param entity the entity whose type names the prefix
     * @param generation the round the answer belongs to
     */
    private readRules(entity: EntityView, generation: number): void {
        const parameters: SearchParameters = {
            typeName: RULE_TYPE_NAME,
            excludeDeletedEntities: true,
            includeSubTypes: false,
            limit: RULE_LIMIT,
            attributes: [...RULE_ATTRIBUTES],
            entityFilters: {
                attributeName: "qualifiedName",
                operator: "startsWith",
                attributeValue: `${entity.typeName}--`,
            },
        };

        this.search.searchWithParameters(parameters).subscribe({
            next: (answer) => {
                if (this.generation !== generation) {
                    return; // a newer entity superseded this answer
                }
                const rules = (answer.entities ?? [])
                    .filter((header) => typeof header?.guid === "string" && header.guid !== "")
                    .filter((header) => isActive(header.attributes?.["active"]))
                    .map((header) => ({
                        guid: header.guid as string,
                        name: textOf(header.attributes?.["name"]) || textOf(header.displayText),
                        description: textOf(header.attributes?.["ruleDescription"]),
                        dimension: textOf(header.attributes?.["qualityDimension"]),
                    }))
                    // The legacy's first sort option was the name (DET-42).
                    .sort((a, b) => a.name.localeCompare(b.name));
                this.record.update((current) =>
                    this.generation === generation && current.entity?.guid === entity.guid
                        ? { ...current, rules, loading: false }
                        : current,
                );
            },
            error: () => {
                // The quiet swallow (DD-521): an empty box, no alert.
                this.record.update((current) =>
                    this.generation === generation && current.entity?.guid === entity.guid
                        ? { ...current, rules: [], loading: false }
                        : current,
                );
            },
        });
    }

    /**
     * The verdicts over the opened entity (DET-42, DD-520): the editor's
     * call, unchanged (EDT-21's client). Its answer joins the rows on
     * `ruleGuid`; a failure leaves the rules iconless (the same swallow,
     * and the verdicts are the box's decoration, never its data).
     * @param entity the opened entity, sent as the draft (the aux API reads
     *   its attributes only, VEV-01 — a view's carry the same values)
     * @param generation the round the answer belongs to
     */
    private readVerdicts(entity: EntityView, generation: number): void {
        this.validateEntity.validateEntity(entity).subscribe({
            next: (answer: EntityValidationResponse) => {
                if (this.generation !== generation) {
                    return;
                }
                const verdicts = new Map((answer.verdicts ?? []).map((verdict) => [verdict.ruleGuid, verdict]));
                this.record.update((current) =>
                    this.generation === generation && current.entity?.guid === entity.guid
                        ? { ...current, verdicts }
                        : current,
                );
            },
            error: () => {
                // No lines at all (the editor's rule, EDT-23): the box keeps
                // its rows, every one iconless.
                this.record.update((current) =>
                    this.generation === generation && current.entity?.guid === entity.guid
                        ? { ...current, verdicts: new Map() }
                        : current,
                );
            },
        });
    }
}

/**
 * Whether a rule is ACTIVE (VEV-03, 12.2's reading): only a false is not.
 * A missing `active`, or one stored as text, is active.
 * @param value the rule's stored `active` attribute
 */
function isActive(value: unknown): boolean {
    const bare =
        typeof value === "object" && value !== null && "raw" in value ? (value as { raw: unknown }).raw : value;

    return bare !== false;
}

/**
 * A stored text attribute as its string: bare, unwrapped from `{"raw": …}`,
 * or empty for anything else (the editor's `textOf` idiom).
 * @param value the stored attribute value
 */
function textOf(value: unknown): string {
    const bare =
        typeof value === "object" && value !== null && "raw" in value ? (value as { raw: unknown }).raw : value;

    return typeof bare === "string" ? bare : "";
}
