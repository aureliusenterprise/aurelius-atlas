/**
 * The shared chrome labels of the `search` screens (DD-883).
 *
 * These are the words the paged card lists, the facet menus, and the filter
 * popovers print, taken from the ui components' caller-supplied-string contract
 * (UIC-21, UIC-34, VCF-10): the ui parts take their copy as inputs, so every
 * screen that mounts one names the same four strings. They lived as members on
 * each screen, which meant the same `$localize` site in two or three files, and
 * editing one wording meant remembering where the twins were.
 *
 * They are module constants, not a service: a label is fixed copy, never state
 * (SPL-10's rule for the settings facade — nothing here owns a value). The
 * ids stay exactly where they were, so the catalogue and both locale fixtures
 * are unchanged (SHL-08); the screens keep their own member names and simply
 * read the constant, so the templates and every test pin are untouched.
 */

/** The facet menu's show-more label — `search.components.filter.facet.showMore` (UIC-34). */
export const FACET_SHOW_MORE = $localize`:@@search.components.filter.facet.showMore:Show more`;

/** The facet menu's show-less label — `search.components.filter.facet.showLess` (UIC-34). */
export const FACET_SHOW_LESS = $localize`:@@search.components.filter.facet.showLess:Show less`;

/** The scroll container's next-page label — `search.components.infiniteScrollContainer.loadNextPage` (UIC-21, SRH-04, HST-08). */
export const LOAD_NEXT_PAGE = $localize`:@@search.components.infiniteScrollContainer.loadNextPage:Load next page...`;

/** The filter popover's empty line — `search.components.filter.notAvailable` (VCF-10, SRH-07). */
export const FILTER_NOT_AVAILABLE = $localize`:@@search.components.filter.notAvailable:No filters available.`;
