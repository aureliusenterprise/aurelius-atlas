import type { AtlasEntity, EntityView } from "aurelius-atlas-data-access";

/**
 * The badge alias of a screen's entity (DET-26, DD-371): the header badge
 * of the details screen still reads it from the entity's own attributes.
 * The card bodies read their fields off the view-family card since 16.5d
 * (DD-616 superseded DD-367's field set: the uniform body became the
 * shared rich card, whose description is the card's `definition`, DD-614).
 */

/** What the rule reads: an entity's attribute values, from either door. */
type AttributeRecord = Pick<AtlasEntity, "attributes"> | Pick<EntityView, "attributes">;

/**
 * The details header badge's alias (DET-26): `attributes.typeAlias` when
 * it is a non-empty string, else nothing — the badge then shows the type
 * name alone. No icon (DD-371 keeps DD-341's refusal). The rich card's
 * badge carries no alias: the card shape has no `typeAlias` (DV-167).
 * @param entity the entity whose attributes hold the alias
 * @returns the alias, or undefined
 */
export function cardTypeAlias(entity: AttributeRecord): string | undefined {
    const alias = entity.attributes?.["typeAlias"];
    return typeof alias === "string" && alias !== "" ? alias : undefined;
}
