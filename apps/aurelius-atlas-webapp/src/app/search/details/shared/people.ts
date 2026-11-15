import type { EntityRelation } from "aurelius-atlas-data-access";
import type { PeopleRow } from "aurelius-atlas-ui";

/**
 * The people rows of the opened entity (DET-23, the People box): the three
 * ends in legacy order — Domain Lead(s) (`domainLead`), Data Owner(s)
 * (`businessOwner`), Data Steward(s) (`steward`) — each deduped by guid
 * keeping the first (the legacy `deduplicate`), each entry an ACTIVE edge
 * carrying a guid (EDT-15's rule, shared with the editor's seed). A row
 * with no people stays in the list empty: the box drops empty rows and
 * shows its placeholder when all are (DET-23).
 *
 * Since 16.5f the shared rich card rides the same three ends again, but
 * labelled and from the document (VCF-15, AVS-10, ASD-06): the door answers
 * the role pairs in `relations` under these keys, and the card renders one
 * labelled row per role, the flat row kept only as the fallback for a
 * document still awaiting its re-derive round (VCF-16). The opened entity's
 * box reads them from the view's `sections` (VDR-03 kept).
 */

/** One people end: the `relationshipAttributes` key and the row's label. */
export const PEOPLE_ENDS: readonly { key: string; label: string }[] = [
    { key: "domainLead", label: $localize`:@@search.components.people.domainLead:Domain Lead(s)` },
    { key: "businessOwner", label: $localize`:@@search.components.people.dataOwner:Data Owner(s)` },
    { key: "steward", label: $localize`:@@search.components.people.dataSteward:Data Steward(s)` },
];

/**
 * One related end, narrowed to what the EDT-15 rule and a link need: a view's
 * `sections` end of the read door (VDR-02) carries these.
 */
export interface SectionEnd {
    guid: string;
    name?: string | null;
    typeName?: string | null;
    /** The edge's state (EDT-15): a DELETED end seeds and counts nothing. */
    status?: string | null;
    /** The bulk read's own label, when it has one. */
    displayText?: string | null;
}

/**
 * The three people rows of the opened entity, read off the view's sections (VDR-03, DD-604).
 * @param sections the view's `sections`, or none
 * @returns the rows, in the DET-23 order; rows may be empty
 */
export function peopleRowsOfSections(sections: readonly EntityRelation[] | undefined): PeopleRow[] {
    return PEOPLE_ENDS.map(({ key, label }) => ({
        label,
        people: sectionEnds(sections, [key]).map((end) => ({ guid: end.guid, displayText: endText(end) || end.guid })),
    }));
}

/**
 * The ends of the view's `sections` under any of ``keys``, as the EDT-15 rule reads them (VDR-03):
 * ACTIVE ends carrying a guid, in order, deduped by guid keeping the first. The People box, the person
 * stats' counts and the section seeds all ride this one rule, so a stat and a box never disagree.
 * A DELETED edge answers nothing from either door: the read door already drops it (DD-604), and the
 * client rule stays as the editor's twin (EDT-15) and never fires on a view.
 * @param sections the view's `sections`, or none
 * @param keys the relationship attribute names to read, in order
 * @returns the deduped ACTIVE ends
 */
export function sectionEnds(sections: readonly EntityRelation[] | undefined, keys: readonly string[]): SectionEnd[] {
    const seen = new Map<string, SectionEnd>();
    for (const key of keys) {
        for (const relation of sections ?? []) {
            if (relation.attribute !== key) continue;
            for (const end of relation.entities ?? []) {
                if (end.status !== undefined && end.status !== null && end.status !== "ACTIVE") {
                    continue; // EDT-15: a DELETED end seeds and counts nothing
                }
                if (typeof end.guid !== "string" || end.guid === "") {
                    continue;
                }
                if (!seen.has(end.guid)) {
                    seen.set(end.guid, end); // the legacy deduplicate: the first wins
                }
            }
        }
    }
    return [...seen.values()];
}

/** An end's own label: its display text, else its name, else nothing. */
function endText(end: { displayText?: string | null; name?: string | null }): string {
    if (typeof end.displayText === "string" && end.displayText !== "") {
        return end.displayText;
    }
    if (typeof end.name === "string" && end.name !== "") {
        return end.name;
    }
    return "";
}
