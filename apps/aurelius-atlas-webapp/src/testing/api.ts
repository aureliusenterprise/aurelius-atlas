/**
 * The door URLs every webapp spec asserts on — one home for the thirteen
 * constants specs used to each re-declare (APC-10's surface, ADR 064).
 *
 * The paths are the nginx-composed ones (`/api` prefix composed by the
 * client, DD-139), so a spec reading `VIEW_URL` asserts the same string the
 * data-access service builds. Change a path here, never in a spec.
 */

/** The read door (VDE-01, DD-608): `GET /api/aurelius/v1/entity/guid/{guid}`. */
export const VIEW_URL = "/api/aurelius/v1/entity/guid/";

/** The mutation door (VDE-05, DD-609): `POST /api/aurelius/v1/entity`. */
export const VIEW_POST_URL = "/api/aurelius/v1/entity";

/** The form-slice door (VDE-02, AVW-11): `GET /api/aurelius/v1/types/for-type/{name}`. */
export const CHAIN_URL = "/api/aurelius/v1/types/for-type/";

/** The Atlas typedef door the small slices ride (VDE-02, DD-611). */
export const TYPEDEFS_URL = "/api/atlas/v2/types/typedefs";

/** The tag box's classification slice (VDE-02, DD-611). */
export const CLASSIFICATION_SLICE_URL = `${TYPEDEFS_URL}?type=CLASSIFICATION`;

/** The form's enum slice (VDE-02, DD-611). */
export const ENUM_SLICE_URL = `${TYPEDEFS_URL}?type=ENUM`;

/** The pickers' relationship slice (RPS-07). */
export const RELATIONSHIP_SLICE_URL = `${TYPEDEFS_URL}?type=RELATIONSHIP`;

/** The create picker's entity typedef headers (VDE-02). */
export const ENTITY_HEADERS_URL = `${TYPEDEFS_URL}/headers?type=ENTITY`;

/** The layout walk's single-typedef read (DET-15): `/v2/types/typedef/name/{name}`. */
export const TYPEDEF_URL = "/api/atlas/v2/types/typedef/name/";

/** The delete stays Atlas's (VDE-11): `DELETE /api/atlas/v2/entity/guid/{guid}`. */
export const ATLAS_ENTITY_URL = "/api/atlas/v2/entity/guid/";

/** The write door the editor used to know (7.x's Atlas entity POST). */
export const ATLAS_ENTITY_POST_URL = "/api/atlas/v2/entity";

/** The audit trail read (HST-08): `GET /api/atlas/v2/entity/{guid}/audit`. */
export function auditUrl(guid: string, count?: number): string {
    const base = `/api/atlas/v2/entity/${guid}/audit`;
    return count === undefined ? base : `${base}?count=${count}`;
}

/** The words search door (VSR-*). */
export const ATLAS_SEARCH_URL = "/api/atlas/v2/search/basic";

/** The view-family search door (VSR-01, ADR 064). */
export const SEARCH_URL = "/api/aurelius/v1/search";

/** The server's tenancy answer (TNW-01). */
export const TENANCY_URL = "/api/aurelius/v1/tenancy";

/** The tenant's dashboards (TDL-01). */
export const DASHBOARDS_URL = "/api/aurelius/v1/tenancy/dashboards";

/** The live governance verdicts (VEV-01). */
export const VERDICTS_URL = "/api/aurelius/v1/rule/verdicts";

/** The rule vocabulary kinds (12.5). */
export const KINDS_URL = "/api/aurelius/v1/quality/kinds";

/** The rule validate door (12.5). */
export const RULE_VALIDATE_URL = "/api/aurelius/v1/quality/rules/validate";

/** The validate-entity aux API (EDT-22, DV-144). */
export const VALIDATE_URL = "/validate-entity/";

/** The lineage-model aux API (LDG-07, DD-139). */
export const LINEAGE_MODEL_URL = "/lineage-model";

/** The server version the footer and the lineage PNG read (VER-01, DD-725). */
export const VERSION_URL = "/api/atlas/admin/version";
