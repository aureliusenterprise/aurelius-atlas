import type { IconDefinition, IconName } from "@fortawesome/free-solid-svg-icons";

import type { TypeIconClass } from "../../meta/type-icons";

/**
 * The lineage shape table (LDG-13, LDG-14): the legacy
 * `libs/modelview2/src/lib/shapes/languages/lineage.ts` ported to the one
 * thing the details page draws. Both lineage types are plain rectangles
 * (the legacy's `compose(basicShapes.rectangle)` — `basicShapes.rectangle`
 * is `m0,0h{w}v{h}h-{w}z`, kept verbatim below), the two classes carry the
 * two fills (`lineage.scss`), and every connection ends in the one arrow
 * marker (`generic-arrow`, `shapes/languages/archimate3.ts` — the only
 * marker of the archimate set the lineage language names; the rest stays
 * with the explorer, DD-388).
 *
 * The two 16x16 icons are the legacy archimate-icon shapes for the two
 * lineage types (`libs/components/src/lib/archimate-icon/shapes.ts`, the
 * `lineage_dataset`/`lineage_process` paths — the database card and the
 * gear), with the type classes that fill them (LDG-13: blue for a dataset,
 * `#00d1b2` for a process, stroke `#000000` — the legacy
 * `archimate-icon.component.scss`). These are the only two icons of that
 * set the lineage page draws; the rest stays in the legacy.
 */

/** The style class a lineage type draws with (the legacy's `lineageClasses`). */
export type LineageClass = "dataset" | "process";

/**
 * The type-to-class table (the legacy's `lineageClasses`): the two fills of
 * `lineage.scss` hang on these classes (LDG-13).
 */
const LINEAGE_CLASSES: Readonly<Record<string, LineageClass>> = {
    lineage_dataset: "dataset",
    lineage_process: "process",
};

/**
 * The node's shape class (LDG-13), or null for a type the viewer does not
 * know — an unknown type draws its rectangle with no fill, as the legacy's
 * missing dictionary entry did.
 * @param type the element's `@xsi_type`
 */
export function lineageClass(type: string): LineageClass | null {
    return LINEAGE_CLASSES[type] ?? null;
}

/**
 * The node's rectangle path (LDG-12): the legacy `basicShapes.rectangle`,
 * verbatim — `m0,0h{width}v{height}h-{width}z`, drawn from the group's own
 * origin.
 * @param width the node's `@w`
 * @param height the node's `@h`
 */
export function rectanglePath(width: number, height: number): string {
    return `m0,0h${width}v${height}h-${width}z`;
}

/** The 16x16 icon paths of the two lineage classes (LDG-13, vendored). */
export const LINEAGE_ICON_PATHS: Readonly<Record<LineageClass, string>> = {
    dataset:
        "M 14.492 1 h -12.9927 c -0.828 0 -1.4992 0.6712 -1.4992 1.4991 v 10.9939 c 0 0.828 0.6712 1.4992 1.4992 1.4992 h 12.9927 c 0.8279 0 1.4991 -0.6712 1.4991 -1.4992 v -10.9939 c 0 -0.8279 -0.6712 -1.4991 -1.4991 -1.4991 z m -7.4959 11.9932 h -4.9972 v -2.9983 h 4.9972 v 2.9983 z m 0 -4.9971 h -4.9972 v -2.9984 h 4.9972 v 2.9984 z m 6.9961 4.9971 h -4.9972 v -2.9983 h 4.9972 v 2.9983 z m 0 -4.9971 h -4.9972 v -2.9984 h 4.9972 v 2.9984 z",
    process:
        "M 15.4545 10.0102 l -1.3508 -0.78 c 0.1363 -0.7356 0.1363 -1.4903 0 -2.2259 l 1.3508 -0.78 c 0.1554 -0.0888 0.2251 -0.2727 0.1744 -0.4439 c -0.352 -1.1288 -0.9512 -2.1498 -1.7344 -2.9996 c -0.1205 -0.13 -0.3171 -0.1617 -0.4693 -0.0729 L 12.0744 3.4879 c -0.5676 -0.4883 -1.2208 -0.8656 -1.9279 -1.113 V 0.8181 c 0 -0.1776 -0.1237 -0.3329 -0.2981 -0.371 c -1.1637 -0.26 -2.3559 -0.2473 -3.4625 0 c -0.1744 0.038 -0.2981 0.1934 -0.2981 0.371 V 2.3781 c -0.7039 0.2505 -1.3571 0.6278 -1.9279 1.113 L 2.8125 2.711 c -0.1554 -0.0888 -0.3488 -0.0602 -0.4693 0.0729 c -0.7832 0.8466 -1.3825 1.8676 -1.7344 2.9996 c -0.0539 0.1712 0.019 0.3551 0.1744 0.4439 L 2.134 7.0075 c -0.1363 0.7356 -0.1363 1.4903 0 2.2259 l -1.3508 0.78 c -0.1554 0.0888 -0.2251 0.2727 -0.1744 0.4439 c 0.352 1.1288 0.9512 2.1498 1.7344 2.9996 c 0.1205 0.13 0.3171 0.1617 0.4693 0.0729 l 1.3508 -0.78 c 0.5676 0.4883 1.2208 0.8656 1.9279 1.113 v 1.56 c 0 0.1776 0.1237 0.3329 0.2981 0.371 c 1.1637 0.26 2.3559 0.2473 3.4625 0 c 0.1744 -0.038 0.2981 -0.1934 0.2981 -0.371 v -1.56 c 0.7039 -0.2505 1.3571 -0.6278 1.9279 -1.113 l 1.3508 0.78 c 0.1554 0.0888 0.3488 0.0602 0.4693 -0.0729 c 0.7832 -0.8466 1.3825 -1.8676 1.7344 -2.9996 c 0.0476 -0.1744 -0.0222 -0.3583 -0.1776 -0.4471 z M 8.1173 10.6539 c -1.3983 0 -2.5366 -1.1383 -2.5366 -2.5366 s 1.1383 -2.5366 2.5366 -2.5366 s 2.5366 1.1383 2.5366 2.5366 s -1.1383 2.5366 -2.5366 2.5366 z",
};

/**
 * The badge icons of the two lineage types (DD-405 amended): the same two
 * legacy paths as {@link LINEAGE_ICON_PATHS}, shaped as FontAwesome icon
 * definitions so the shared card's type badge (`aurelius-atlas-ui-type-name`)
 * can ink them. The legacy badge drew its icon from `iconsByType` — the
 * app's own type index (DD-378) — which never carried the two lineage
 * types; the demo's lineage card badge shows the archimate glyphs
 * (`definitions.ts`, the `lineage_dataset`/`lineage_process` entries), and
 * those are the paths below. FA renders the path with `fill: currentColor`,
 * so the badge's colour class carries the lineage fills: `.technical` is
 * the dataset's blue, `.technical-process` the process's `#00d1b2` — the
 * same two inks the Type row and the diagram nodes use.
 */
export const LINEAGE_BADGE_ICONS: Readonly<Record<LineageClass, IconDefinition>> = {
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
 * shared badge families whose ink is the lineage fill — blue for a
 * dataset, `#00d1b2` for a process (`type-name.component.scss`).
 * @param cssClass the lineage class, or null for an unknown type
 * @returns the badge class, or undefined for no icon at all
 */
export function lineageBadgeClass(cssClass: LineageClass | null): TypeIconClass | undefined {
    if (cssClass === "dataset") {
        return "technical";
    }
    return cssClass === "process" ? "technical-process" : undefined;
}

/**
 * The arrow marker (LDG-14): the legacy defs' `generic-arrow` — the one
 * marker the lineage language names (`marker-end: 'generic-arrow'`), ported
 * field for field; the archimate marker set stays with the explorer.
 */
export const GENERIC_ARROW = {
    refX: 7,
    refY: 3,
    markerWidth: 6,
    markerHeight: 7,
    path: "M0,0l7,3l-7,3z",
} as const;

/** The viewer's pan/zoom scale extent (LDG-16): the legacy's verbatim. */
export const ZOOM_SCALE_EXTENT: readonly [number, number] = [0.5, 3];
