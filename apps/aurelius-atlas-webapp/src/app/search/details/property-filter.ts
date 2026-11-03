import type { AtlasEntity } from "aurelius-atlas-data-access";
import type { PropertiesItemLink } from "aurelius-atlas-ui";

/**
 * A property value the details table renders: a scalar, or a link array of
 * entity references (the `properties-item` input contract, UIC-13).
 */
export type DetailPropertyValue = string | number | boolean | PropertiesItemLink[];

/** One rendered properties row (DET-11). */
export type DetailProperty = {
    /** The attribute name, the row's Key cell. */
    key: string;
    /** The classified value, the row's Value cell. */
    value: DetailPropertyValue;
};

/**
 * The legacy details-property blacklist, ported verbatim from the Aurelius
 * source (`apps/atlas/src/app/search/services/filtered-properties/
 * blacklist-properties.ts`, clone commit b05738982): the system/child/parent/
 * owner keys the legacy `FilteredPropertiesService` dropped from the details
 * properties table (DET-11).
 */
export const LEGACY_PROPERTY_BLACKLIST: ReadonlySet<string> = new Set([
    "ArchiMateReference",
    "archimateReference",
    "id",
    "attributes",
    "businessOwner",
    "businessOwnerAttribute",
    "businessOwnerEntity",
    "changeLog",
    "childDataset",
    "childEntity",
    "childField",
    "childSystem",
    "collections",
    "dashboards",
    "dataDomain",
    "dataEntity",
    "dataQuality",
    "datasets",
    "definition",
    "domainLead",
    "fields",
    "indexPatterns",
    "inputToProcesses",
    "inputs",
    "isKeyData",
    "meanings",
    "name",
    "outputFromProcesses",
    "outputs",
    "parentDataset",
    "parentEntity",
    "parentField",
    "parentSystem",
    "ProcessOwner",
    "processOwner",
    "qualifiedName",
    "replicatedFrom",
    "replicatedTo",
    "riskClassification",
    "steward",
    "stewardAttribute",
    "stewardEntity",
    "system",
    "systems",
    "visualizations",
    "ruleDescription",
]);

/** One candidate link of a `guid`-bearing array (a collapsed relationship end). */
type LinkCandidate = { guid?: unknown; displayText?: unknown; name?: unknown };

/**
 * The link's label: displayText, else name, else the guid itself — the
 * legacy `properties-item` fallback chain.
 * @param candidate the array entry (its `guid` already checked a string)
 * @returns the label to render
 */
function displayTextOf(candidate: LinkCandidate): string {
    if (typeof candidate.displayText === "string" && candidate.displayText !== "") {
        return candidate.displayText;
    }
    if (typeof candidate.name === "string" && candidate.name !== "") {
        return candidate.name;
    }
    return candidate.guid as string;
}

/**
 * The value as the `properties-item` link array (DET-11): an array whose
 * entries all carry a string `guid` — a collapsed `AtlasRelatedEntity[]` or
 * an `AtlasRelatedObjectId[]` — mapped to `{ guid, displayText }` with the
 * legacy displayText/name fallback, guid as the last resort. Any other value
 * is not a link array.
 * @param value the raw attribute value
 * @returns the links, or null when the value is not a link array
 */
function asLinkArray(value: unknown): PropertiesItemLink[] | null {
    if (!Array.isArray(value) || value.length === 0) {
        return null;
    }
    const links: PropertiesItemLink[] = [];
    for (const entry of value) {
        if (typeof entry !== "object" || entry === null) {
            return null;
        }
        const candidate = entry as LinkCandidate;
        if (typeof candidate.guid !== "string") {
            return null;
        }
        links.push({ guid: candidate.guid, displayText: displayTextOf(candidate) });
    }
    return links;
}

/**
 * The value as a scalar, or null (DET-11): strings, numbers, booleans render
 * through `properties-item`; null/undefined earn no row (the legacy nil
 * drop); any other object shape earns no row (the legacy renderer showed
 * nothing for them, DET-02's no-fake-data rule).
 * @param value the raw attribute value
 * @returns the scalar, or null
 */
function asScalar(value: unknown): string | number | boolean | null {
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
        return value;
    }
    return null;
}

/**
 * The details properties of an entity (DET-11), the legacy
 * `FilteredPropertiesService` port: merge the entity's attributes with its
 * relationship attributes (the relationship value wins a key clash, the
 * legacy `{...attributes, ...relationshipAttributes}` spread order), drop
 * the keys on {@link LEGACY_PROPERTY_BLACKLIST}, the key the description box
 * shows, and the nil values, keep only renderable shapes, and order the rows
 * by key. The description drop (DD-320) is the legacy blacklist's own
 * mechanism: the legacy table drops `definition` because the description box
 * shows it, and this product's box shows `description` for the Atlas model
 * types (DET-10), so the shown key earns no row the same way.
 * @param entity the resolved entity
 * @param shownDescription the attribute the description box shows, or null
 * @returns the rows, sorted by key
 */
export function detailProperties(entity: AtlasEntity, shownDescription: string | null = null): DetailProperty[] {
    const merged: Record<string, unknown> = {
        ...entity.attributes,
        ...entity.relationshipAttributes,
    };
    const rows: DetailProperty[] = [];
    for (const [key, value] of Object.entries(merged)) {
        if (value === null || value === undefined || LEGACY_PROPERTY_BLACKLIST.has(key) || key === shownDescription) {
            continue;
        }
        const scalar = asScalar(value);
        if (scalar !== null) {
            rows.push({ key, value: scalar });
            continue;
        }
        const links = asLinkArray(value);
        if (links !== null) {
            rows.push({ key, value: links });
        }
    }
    return rows.sort((a, b) => a.key.localeCompare(b.key));
}
