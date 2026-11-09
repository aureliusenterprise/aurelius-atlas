/**
 * The colour view (UIC-30/UIC-31, DD-420): the legacy `ColorViewService`
 * mechanism, kept as plain data. The legacy held three stores
 * (`bucketMapping` concept→category, `colorPallette`, `legend` category→hex)
 * and joined them reactively; this module is that join as one pure function,
 * so the canvas stays dumb (the lib's rule) and the caller owns the three
 * values. The caller — a heatmap producer, a violation report — supplies the
 * categories; the drawer's legend table and the canvas both read the
 * function's result, so a picked colour repaints both.
 */

/**
 * The default palette: the twelve Google-Charts-classic qualitative colours.
 * The legacy drew its colours from the `google-palette` package; this is the
 * fixed literal list instead (DD-420's deviation — no new dependency, and
 * the qualitative palette is stable anyway). A thirteenth category reuses
 * the first colour — the legacy generated more; wrapping is the deviation.
 */
export const CATEGORY_PALETTE: readonly string[] = [
    "#3366cc",
    "#dc3912",
    "#ff9900",
    "#109618",
    "#0099c9",
    "#9b06fc",
    "#ff2052",
    "#0034ff",
    "#cc0000",
    "#7a06fc",
    "#006600",
    "#b90099",
];

/** Concept id to category name (the legacy's `bucketMapping`). */
export type CategoryMap = Readonly<Record<string, string>>;

/** Category name to hex colour — the legend (the legacy's `legend`). */
export type CategoryLegend = Readonly<Record<string, string>>;

/**
 * The colour one element draws with, or null when the colour view paints
 * nothing for it (the legacy's `getColorById`, and the caller's own class
 * fill shows through). The legacy looked the element up by its view id first
 * and its model id second (`modelview-node.service.ts`), so this does too.
 * @param legend the category→colour legend
 * @param categories the concept→category map
 * @param viewId the element's view id (placement id)
 * @param conceptId the concept the element stands for (`ref ?? id`)
 */
export function categoryColor(
    legend: CategoryLegend,
    categories: CategoryMap | null,
    viewId: string,
    conceptId: string,
): string | null {
    if (categories === null) {
        return null;
    }
    const category = categories[viewId] ?? categories[conceptId];
    return category === undefined ? null : (legend[category] ?? null);
}

/**
 * Join the categories with the picked overrides into the legend: each
 * distinct category in first-seen order gets an override or the next palette
 * colour (the legacy's `(bucketMapping, palette) → legend` then
 * `(legend, overrides) → colorMapping` chain, run once).
 * @param categories the concept→category map, or null for no colour view
 * @param overrides the picked category→colour overrides (the picker's
 *     writes), or null for none
 * @returns the category→colour legend, empty when there are no categories
 */
export function deriveCategoryLegend(categories: CategoryMap | null, overrides: CategoryMap | null): CategoryLegend {
    if (categories === null) {
        return {};
    }
    const legend: Record<string, string> = {};
    let index = 0;
    for (const category of Object.values(categories)) {
        if (category === "" || category in legend) {
            continue;
        }
        legend[category] = overrides?.[category] ?? CATEGORY_PALETTE[index % CATEGORY_PALETTE.length];
        index += 1;
    }
    return legend;
}
