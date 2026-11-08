/**
 * The human-readable type names of the lineage model's concept types
 * (LDG-20): the `archimate3` slice of the legacy metamodel
 * (`libs/metamodel/src/lib/metamodel.ts` — `elements.lineage_dataset`,
 * `elements.lineage_process`, `relations_by_tag.lineage_relation`) plus the
 * view type, whose name the legacy parser hardcodes
 * (`parse-view.ts`: type `ar3_View`, human-readable "View").
 *
 * The shipped producer emits exactly these four types (8.2's fixed rule set),
 * so this is the whole table the reader needs — not the legacy's generated
 * megabyte of archimate entries. An unknown type reads as the empty string
 * (the legacy's dictionary lookup answered `undefined`; the panel hides the
 * Type row when its value is empty).
 */
const HUMAN_READABLE_TYPES: Readonly<Record<string, string>> = {
    lineage_dataset: "Dataset",
    lineage_process: "Process",
    lineage_relation: "Data Lineage",
    ar3_View: "View",
};

/**
 * The display name of a concept type (the legacy's `archimate3[...]` lookup).
 * @param type the concept's `@xsi_type` (or parser type, for a view)
 * @returns the human-readable name, or the empty string when unknown
 */
export function humanReadableType(type: string): string {
    return HUMAN_READABLE_TYPES[type] ?? "";
}

/**
 * The relation types' verb phrases (DD-411): the legacy
 * `parsers/archimate3/parse-relation.ts` `humanReadableTypes` table — the
 * `displayName` the relationship row's middle line leads with when the
 * relation carries no name of its own. The shipped chain's one relation type
 * is `lineage_relation`; the rest of the archimate verbs stay with the
 * explorer. An unknown type reads as the empty string (the legacy's
 * dictionary answered `undefined`, and the row hid the span).
 */
const RELATION_VERBS: Readonly<Record<string, string>> = {
    lineage_relation: "Flows into",
};

/**
 * The verb phrase of a relation type (the legacy parser's `displayName`).
 * @param type the relation's `@xsi_type`
 * @returns the verb phrase, or the empty string when unknown
 */
export function relationVerb(type: string): string {
    return RELATION_VERBS[type] ?? "";
}
