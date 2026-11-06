import type { AtlasEntity } from "aurelius-atlas-data-access";

/**
 * The uniform card body's facts (DET-19, DD-367): the display text, the
 * description text, and the badge alias, read the one way every card
 * reads them — the same rules the details header already follows
 * (DET-09's title, DET-10/DD-320's definition-else-description, DET-26's
 * `attributes.typeAlias`).
 */

/**
 * A card's display text: the entity's `displayText`-style name — the
 * `name` attribute, else `qualifiedName`, else the guid (the results
 * screen's fallback chain, DET-09's sibling).
 * @param entity the resolved related entity
 * @returns the card title's text
 */
export function cardDisplayText(entity: AtlasEntity): string {
    const attributes = entity.attributes ?? {};
    const name = attributes["name"];
    if (typeof name === "string" && name !== "") {
        return name;
    }
    const qualifiedName = attributes["qualifiedName"];
    if (typeof qualifiedName === "string" && qualifiedName !== "") {
        return qualifiedName;
    }
    return entity.guid ?? "";
}

/**
 * A card's description text (DET-19): `definition` when it is a string,
 * else `description` (the DET-10/DD-320 order), else nothing — the
 * markdown block omits itself when neither is a string.
 * @param entity the resolved related entity
 * @returns the description text, or empty
 */
export function cardDescription(entity: AtlasEntity): string {
    const attributes = entity.attributes ?? {};
    for (const key of ["definition", "description"]) {
        if (typeof attributes[key] === "string") {
            return attributes[key] as string;
        }
    }
    return "";
}

/**
 * A card's badge alias (DET-26): `attributes.typeAlias` when it is a
 * non-empty string, else nothing — the badge then shows the type name
 * alone. No icon (DD-371 keeps DD-341's refusal).
 * @param entity the resolved related entity
 * @returns the alias, or undefined
 */
export function cardTypeAlias(entity: AtlasEntity): string | undefined {
    const alias = entity.attributes?.["typeAlias"];
    return typeof alias === "string" && alias !== "" ? alias : undefined;
}
