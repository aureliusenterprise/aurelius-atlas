/**
 * The Lineage Model feature's public surface (DD-884).
 *
 * Lineage was promoted out of `search/details/lineage/` to a top-level feature
 * here: its module reaches into `shell/` and `tokens` (the session, the version
 * stamp, the app config), which are app-level services no `search/` feature
 * should own — so the folder is a feature of its own, not a details sub-folder
 * (the architect review's item 7). The barrel names that boundary: `search/`
 * mounts the lineage box and reads its store through these two names, and no
 * deeper.
 *
 * Two exports only, on purpose:
 * - `LineageModel` — the `#lineage-model` box the details screen places between
 *   its card boxes (LDG-09), which owns its own fetch and its three states
 *   (LDG-10).
 * - `LineageModelState` — the root store behind that box (DD-415), injected by
 *   the screen for the box's stat word and the diagram's selection.
 *
 * The routed quickview (`LineageModelBrowser`, LDG-25) is deliberately NOT
 * re-exported: `routes.ts` loads it lazily from its own file, and pulling it
 * through this barrel would fold that route's chunk into every eager importer of
 * the barrel — the code-split the drawer route exists to get. Its component, the
 * diagram, the tabs, and the AR3 parsers are the feature's internals; nothing
 * outside imports them, and nothing outside should.
 */
export { LineageModel } from "./lineage-model.component";
export { LineageModelState } from "./lineage-state";
