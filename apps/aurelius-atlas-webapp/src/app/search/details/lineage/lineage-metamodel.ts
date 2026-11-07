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
