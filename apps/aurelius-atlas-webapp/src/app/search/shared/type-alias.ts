import type { AtlasEntity, EntityView } from "aurelius-atlas-data-access";

/**
 * The badge alias of a screen's entity (DET-26, DD-371): the header badge
 * of the details screen and the editor's static badge read it from the
 * entity's own attributes. The card bodies read their fields off the
 * view-family card since 16.5d (DD-616 superseded DD-367's field set: the
 * uniform body became the shared rich card, whose description is the
 * card's `definition`, DD-614), and a card badge reads the card shape's
 * own `typeAlias` field since 18.1 (MMS-09, DD-721).
 *
 * It lives in `search/shared/` because both screens own it (WFE-06, DD-807):
 * it started life in the details feature and the editor reached across for
 * it, which let a details refactor break the editor over a display rule
 * neither feature owns alone.
 */

/** What the rule reads: an entity's attribute values, from either door. */
type AttributeRecord = Pick<AtlasEntity, "attributes"> | Pick<EntityView, "attributes">;

/**
 * The badge's alias (DET-26): `attributes.typeAlias` when it is a
 * non-empty string, else nothing — the badge then shows the type
 * name alone. No icon (DD-371 keeps DD-341's refusal).
 * @param entity the entity whose attributes hold the alias
 * @returns the alias, or undefined
 */
export function cardTypeAlias(entity: AttributeRecord): string | undefined {
    const alias = entity.attributes?.["typeAlias"];
    return typeof alias === "string" && alias !== "" ? alias : undefined;
}
