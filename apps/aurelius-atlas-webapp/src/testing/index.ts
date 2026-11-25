/**
 * The webapp's unit-test harness (public entry: `../../testing` from a spec).
 *
 * Only what two or more specs repeat lives here. A spec's own fake — a
 * `VersionService` stub, one endpoint nobody else calls — stays in the spec,
 * where the reader sees it beside the assertion it serves. The harness is the
 * five providers every routed screen needs, the door URLs the services build,
 * and the fixture builders for the view family's wire shapes.
 *
 * Kept out of the production bundle by never being imported from `src/app`.
 */
export * from "./api";
export * from "./auth";
export * from "./config";
export * from "./dom";
export * from "./providers";
export * from "./view-fixtures";
