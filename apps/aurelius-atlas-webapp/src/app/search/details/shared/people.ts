import type { AtlasEntity, AtlasRelatedEntity, EntityRelation } from "aurelius-atlas-data-access";
import type { PeopleRow, PersonLink } from "aurelius-atlas-ui";

/**
 * The people rows of one entity (DET-23, shared by the People box and the
 * card bodies, DET-19): the three ends in legacy order — Domain Lead(s)
 * (`domainLead`), Data Owner(s) (`businessOwner`), Data Steward(s)
 * (`steward`) — each deduped by guid keeping the first (the legacy
 * `deduplicate`), each entry an ACTIVE edge carrying a guid (EDT-15's
 * rule, shared with the editor's seed). A row with no people stays in the
 * list empty: the box drops empty rows and shows its placeholder when all
 * are (DET-23), the card body renders nothing (the legacy card's people
 * block with `showPlaceholder` off).
 *
 * Domain Lead stays a row of the grouping everywhere — the legacy card
 * body carried the same three-row component; the DET-19 omission named in
 * the spec is only that a person's own card never leads with one.
 */

/** One people end: the `relationshipAttributes` key and the row's label. */
const PEOPLE_ENDS: readonly { key: string; label: string }[] = [
    { key: "domainLead", label: $localize`:@@search.components.people.domainLead:Domain Lead(s)` },
    { key: "businessOwner", label: $localize`:@@search.components.people.dataOwner:Data Owner(s)` },
    { key: "steward", label: $localize`:@@search.components.people.dataSteward:Data Steward(s)` },
];

/**
 * One related end, narrowed to what the EDT-15 rule and a link need: both doors' answers —
 * {@link AtlasRelatedEntity} of a bulk read, a view's `sections` end of the read door (VDR-02) — carry these.
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
 * The three people rows of one bulk-read entity (DET-19's card body, 7.21a kept).
 * @param entity the entity whose `relationshipAttributes` hold the ends
 * @returns the rows, in the DET-23 order; rows may be empty
 */
export function peopleRows(entity: AtlasEntity): PeopleRow[] {
    const stored = entity.relationshipAttributes ?? {};
    return PEOPLE_ENDS.map(({ key, label }) => ({ label, people: dedupeByGuid(stored[key]) }));
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

/**
 * The row's people: ACTIVE entries carrying a guid, deduped by guid
 * keeping the first, each shown by its display text (the guid as the
 * last resort — a link needs a label).
 * @param value the raw `relationshipAttributes` value of one end
 * @returns the person links, in order
 */
function dedupeByGuid(value: unknown): PersonLink[] {
    const rows = asRelatedList(value);
    const seen = new Map<string, PersonLink>();

    for (const row of rows) {
        if (row.relationshipStatus !== undefined && row.relationshipStatus !== "ACTIVE") {
            continue; // EDT-15: a DELETED edge seeds nothing
        }
        if (typeof row.guid !== "string" || row.guid === "") {
            continue;
        }
        if (seen.has(row.guid)) {
            continue; // the legacy deduplicate: the first wins
        }
        seen.set(row.guid, { guid: row.guid, displayText: personText(row) });
    }

    return [...seen.values()];
}

/**
 * A person's display text: the edge's own, else its name, else the guid.
 * @param row the relationship edge
 * @returns the link's label
 */
function personText(row: AtlasRelatedEntity): string {
    return endText(row) || row.guid || "";
}

/** An end's own label: its display text, else its name, else nothing (both doors' shapes). */
function endText(end: { displayText?: string | null; name?: string | null }): string {
    if (typeof end.displayText === "string" && end.displayText !== "") {
        return end.displayText;
    }
    if (typeof end.name === "string" && end.name !== "") {
        return end.name;
    }
    return "";
}

/**
 * A read's `relationshipAttributes` value as a list (the editor's twin:
 * the server answers a SET end as a list and a SINGLE end as one object).
 * @param value the raw value
 * @returns the related entities
 */
function asRelatedList(value: unknown): AtlasRelatedEntity[] {
    if (Array.isArray(value)) {
        return value as AtlasRelatedEntity[];
    }
    if (value !== null && typeof value === "object") {
        return [value as AtlasRelatedEntity];
    }

    return [];
}
