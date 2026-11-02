/**
 * Atlas user-profile DTOs — the wire shapes of the saved searches of
 * `/api/atlas/v2/search/saved/**` (SVS-01, APC-03).
 *
 * Field names are the camelCase Java getter names the server writes, mirrored
 * from `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/profile.py`,
 * ported from Apache Atlas 2.4.0 `org.apache.atlas.model.profile`): keep the
 * two in step when the Python model changes. Fields the server leaves out are
 * `undefined` — normalisations the server applies on read are the server's, not
 * the client's (TDM-06..13's rule, applied to profiles). The Python twin of
 * this cluster is the server-client's use of the same models (CSD-02..CSD-05).
 */

import { SearchParameters } from "./atlas-search";

/**
 * How a saved search was asked (`AtlasUserSavedSearch.SavedSearchType`). The
 * server's `to` reads any case and falls back to `BASIC`; the client sends one
 * of the names it writes.
 */
export type SavedSearchType = "BASIC" | "ADVANCED" | "BASIC_RELATIONSHIP";

/**
 * A search its owner saved under a name (`AtlasUserSavedSearch`, SVS-01): the
 * body of `POST`/`PUT /search/saved` and the answer of the saved-search reads.
 * A new object carries a negative `guid` until the server stores it; `name` is
 * unique per owner, and the reads find it by name while the delete finds the
 * stored object by guid (SVS-04, SVS-05).
 */
export type AtlasUserSavedSearch = {
    guid?: string | null;
    ownerName?: string | null;
    name?: string | null;
    searchType?: SavedSearchType | null;
    searchParameters?: SearchParameters | null;
    uiParameters?: string | null;
};
