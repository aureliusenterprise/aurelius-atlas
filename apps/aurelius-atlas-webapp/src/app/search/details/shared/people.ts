import type { AtlasEntity, AtlasRelatedEntity } from "aurelius-atlas-data-access";
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
 * The three people rows of one entity, deduped and filtered.
 * @param entity the entity whose `relationshipAttributes` hold the ends
 * @returns the rows, in the DET-23 order; rows may be empty
 */
export function peopleRows(entity: AtlasEntity): PeopleRow[] {
    const stored = entity.relationshipAttributes ?? {};
    return PEOPLE_ENDS.map(({ key, label }) => ({ label, people: dedupeByGuid(stored[key]) }));
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
    if (typeof row.displayText === "string" && row.displayText !== "") {
        return row.displayText;
    }
    if (typeof row.name === "string" && row.name !== "") {
        return row.name;
    }
    return row.guid ?? "";
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
