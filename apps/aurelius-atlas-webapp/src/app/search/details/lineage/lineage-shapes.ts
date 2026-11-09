import type { NavigationBehaviorOptions } from "@angular/router";
import type { IconDefinition, IconName } from "@fortawesome/free-solid-svg-icons";

import { LINEAGE_ICON_PATHS } from "aurelius-atlas-ui";

import type { TypeIconClass } from "../../meta/type-icons";

/**
 * The lineage badge helpers and the drawer's scroll posture (DD-419): what
 * the details page owns of 7.22b's shape module. The drawing's table data —
 * the lineage classes, the icon paths, the arrow, the shape tables, and the
 * zoom constants — moved to `aurelius-atlas-ui`'s `model-viewer` with the
 * canvas itself (DD-419: the renderer of DD-388, ported into the shared
 * lib). This file keeps the card badge (DD-405), which belongs to the app's
 * badge families (`type-icons.ts`), and the router navigation option.
 */

/**
 * The badge icons of the two lineage types (DD-405 amended): the same two
 * legacy paths as the canvas's `LINEAGE_ICON_PATHS`, shaped as FontAwesome
 * icon definitions so the shared card's type badge (`aurelius-atlas-ui-type-name`)
 * can ink them. The legacy badge drew its icon from `iconsByType` — the
 * app's own type index (DD-378) — which never carried the two lineage
 * types; the demo's lineage card badge shows the archimate glyphs
 * (`definitions.ts`, the `lineage_dataset`/`lineage_process` entries), and
 * those are the paths below. FA renders the path with `fill: currentColor`,
 * so the badge's colour class carries the lineage fills: `.technical` is
 * the dataset's blue, `.technical-process` the process's `#00d1b2` — the
 * same two inks the Type row and the diagram nodes use.
 */
export const LINEAGE_BADGE_ICONS: Readonly<Record<"dataset" | "process", IconDefinition>> = {
    dataset: {
        prefix: "fas",
        iconName: "lineage-dataset" as IconName,
        icon: [16, 16, [], "", LINEAGE_ICON_PATHS.dataset],
    },
    process: {
        prefix: "fas",
        iconName: "lineage-process" as IconName,
        icon: [16, 16, [], "", LINEAGE_ICON_PATHS.process],
    },
};

/**
 * The badge's colour class for one lineage type (DD-405 amended): the two
 * shared badge families whose ink is the lineage fill — blue for a dataset,
 * `#00d1b2` for a process (`type-name.component.scss`). No archimate type has
 * a badge, as the legacy's `iconsByType` (DD-378) never carried one either,
 * so every other class answers undefined (7.22e's `ar3BadgeClass` folded into
 * this one here, DD-419).
 * @param cssClass the glyph's fill class, or null for no glyph at all
 * @returns the badge class, or undefined for no badge icon
 */
export function lineageBadgeClass(cssClass: string | null): TypeIconClass | undefined {
    if (cssClass === "dataset") {
        return "technical";
    }
    return cssClass === "process" ? "technical-process" : undefined;
}

/**
 * The quickview drawer's own navigations leave the page's scroll where it
 * is (DD-416): the router's `scrollPositionRestoration: "enabled"` (SHL-06)
 * scrolls every finished navigation to the top, and the drawer is an
 * overlay — opening it, switching its tab, or closing it must not move the
 * details page the reader is reading underneath. `scroll: "manual"` is the
 * router's per-navigation opt-out (NavigationBehaviorOptions).
 */
export const DRAWER_SCROLL: NavigationBehaviorOptions = { scroll: "manual" };
