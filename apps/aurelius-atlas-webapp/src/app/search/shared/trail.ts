import type { Breadcrumb } from "aurelius-atlas-ui";
import type { EntityCard } from "aurelius-atlas-data-access";

import { typeIcon } from "../meta/type-icons";

/**
 * The trail rule of the view family (VDR-06, DD-606, DD-616): the stored
 * breadcrumb, top down, plus the entity's own crumb. Both the details header
 * and the shared rich card (16.5d) render a trail by this one rule, so a
 * crumb can never read differently on the two screens. Which crumb reads
 * active is the mount's, not this rule's: the header marks the entity's own
 * (VDR-06), a section card marks the entity being viewed (DD-625).
 */

/**
 * The trail of one card or view (VDR-06, DD-606): the stored breadcrumb,
 * top down, plus the entity's own crumb last. Each crumb shows its name,
 * or its type, or its guid — the stored arrays can come apart or lose a
 * name (ASU-02, LAS-04) — and takes its icon from the app's type map, as
 * the badge's does (DET-26).
 * @param card the read door's view or a search card, whichever carries the trail
 * @param icon the type-to-icon resolver, injected to keep this pure
 * @returns the crumbs, the entity's own last
 */
export function trailOf(
    card: Pick<EntityCard, "guid" | "name" | "typeName" | "breadcrumb">,
    icon: (typeName: string) => ReturnType<typeof typeIcon>,
): Breadcrumb[] {
    const crumbs = [
        ...(card.breadcrumb ?? []),
        { guid: card.guid, name: card.name, typeName: card.typeName as string | null | undefined },
    ];
    return crumbs.map((crumb) => {
        const name = crumb.name || crumb.typeName || crumb.guid;
        const typeName = crumb.typeName ?? "";
        const found = icon(typeName);
        return {
            guid: crumb.guid,
            name,
            typeName,
            ...(found !== undefined ? { icon: found.icon, iconClass: found.classIcon } : {}),
        };
    });
}
