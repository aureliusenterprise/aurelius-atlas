/**
 * The draft both the editor and the governance banner build from a view
 * (VDE-01, DD-608): the shape the form seed, the tag box, the picker seeds,
 * and the governance banner read. `entityFromView` answers the `AtlasEntity`
 * shape from a view — the values as they are, the own tags as
 * `classifications`, and each `sections` end as a `relationshipAttributes`
 * entry the pickers seed from — so every helper keeps working on the view's
 * material unchanged.
 *
 * 7.44 lifted it here from `editor/view-as-entity.ts` so the details screen's
 * governance banner (EDT-23) and the editor name it as a peer rather than one
 * reaching into the other (DD-870). The save body stays with the editor's
 * helpers, built from the view directly by `bodyFromEdits`.
 */

import type { AtlasEntity, EntityView } from "aurelius-atlas-data-access";

/**
 * The editor's draft for a view (VDE-01, DD-608): the shape the form seed,
 * the tag box, the picker seeds, and the governance draft all read. The
 * view's `classificationNames` are its own tags already (VDR-05 — propagated
 * ones never enter, so DD-326's client filter retires); each `sections` end
 * rides `relationshipAttributes` under its attribute name, and the EDT-15
 * seed rule (ACTIVE ends with a guid) applies to it as to an Atlas read.
 * @param view the entity's live view from the read door
 * @returns the Atlas-shaped draft the editor's helpers consume
 */
export function entityFromView(view: EntityView): AtlasEntity {
    const relationshipAttributes: Record<string, unknown> = {};
    for (const section of view.sections ?? []) {
        relationshipAttributes[section.attribute] = (section.entities ?? []).map((end) => ({
            guid: end.guid,
            typeName: end.typeName ?? "",
            displayText: end.name ?? "",
            relationshipStatus: end.status ?? "ACTIVE",
        }));
    }

    return {
        guid: view.guid,
        typeName: view.typeName,
        status: view.status,
        createTime: view.createTime,
        updateTime: view.updateTime,
        createdBy: view.createdBy,
        updatedBy: view.updatedBy,
        attributes: { ...view.attributes, qualifiedName: view.qualifiedName },
        classifications: (view.classificationNames ?? []).map((typeName) => ({ typeName, entityGuid: view.guid })),
        relationshipAttributes,
    };
}
