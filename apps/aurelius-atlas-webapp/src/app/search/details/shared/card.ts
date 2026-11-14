import type { AtlasEntity, EntityView } from "aurelius-atlas-data-access";

/**
 * The uniform card body's facts (DET-19, DD-367): the display text, the
 * description text, and the badge alias, read the one way every card
 * reads them — the same rules the details header already follows
 * (DET-09's title, DET-10/DD-320's definition-else-description, DET-26's
 * `attributes.typeAlias`).
 *
 * The helpers take either door's shape — the bulk-read {@link AtlasEntity}
 * a card body resolves (7.21a kept, VDR-03) or the read door's
 * {@link EntityView} the details header answers (16.5b) — because every
 * rule reads only the guid and the attribute values, which both carry.
 */

/** What the rules read: an entity's guid and its attribute values, from either door. */
export type CardRecord = Pick<AtlasEntity, "guid" | "attributes"> | Pick<EntityView, "guid" | "attributes">;

/**
 * A card's display text: the entity's `displayText`-style name — the
 * `name` attribute, else `qualifiedName`, else the guid (the results
 * screen's fallback chain, DET-09's sibling).
 * @param entity the resolved related entity
 * @returns the card title's text
 */
export function cardDisplayText(entity: CardRecord): string {
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
export function cardDescription(entity: CardRecord): string {
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
export function cardTypeAlias(entity: CardRecord): string | undefined {
    const alias = entity.attributes?.["typeAlias"];
    return typeof alias === "string" && alias !== "" ? alias : undefined;
}
