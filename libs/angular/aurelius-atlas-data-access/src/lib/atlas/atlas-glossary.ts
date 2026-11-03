/**
 * Atlas glossary DTOs — the wire shapes of `/api/atlas/v2/glossary/**`
 * (GLS/GTM/GCT/GTA/GIM, APC-03, AGL-*).
 *
 * Field names are the camelCase names the server writes, mirrored from
 * `libs/python/aurelius-atlas-model` (`aurelius_atlas_model/glossary.py` and
 * `instance/related_object_id.py`, ported from Apache Atlas 2.4.0
 * `org.apache.atlas.model.glossary`): keep the two in step when the Python
 * model changes. Every glossary object descends from
 * `AtlasGlossaryBaseObject` — its six fields (guid, qualifiedName, name, the
 * two descriptions, additionalAttributes, classifications) are written into
 * each DTO here, since a TypeScript type has no inheritance. The
 * `AtlasRelatedTermHeader` of a term's relations lives in `atlas-entity.ts`
 * (the entity's meanings use the same wire type, APC-03). The Python twin of
 * this cluster is `AtlasClient.glossary` (CLG-01..CLG-09).
 */

import type {
    AtlasClassification,
    AtlasEntityStatus,
    AtlasObjectId,
    AtlasRelatedTermHeader,
    AtlasTermRelationshipStatus,
} from "./atlas-entity";

/** How a glossary read sorts its page (`GlossarySort`, CLG-02). */
export type GlossarySort = "ASC" | "DESC";

/** A glossary's identity and display text, as a category or term anchors to it (`AtlasGlossaryHeader`). */
export type AtlasGlossaryHeader = {
    glossaryGuid?: string | null;
    relationGuid?: string | null;
    displayText?: string | null;
};

/** A related category, its parent and the relationship's description (`AtlasRelatedCategoryHeader`). */
export type AtlasRelatedCategoryHeader = {
    categoryGuid?: string | null;
    parentCategoryGuid?: string | null;
    relationGuid?: string | null;
    displayText?: string | null;
    description?: string | null;
};

/** A term's category and the categorization's attributes (`AtlasTermCategorizationHeader`). */
export type AtlasTermCategorizationHeader = {
    categoryGuid?: string | null;
    relationGuid?: string | null;
    description?: string | null;
    displayText?: string | null;
    status?: AtlasTermRelationshipStatus | null;
};

/** A related entity as a term assignment shows it (`AtlasRelatedObjectId`, ENT-12). */
export type AtlasRelatedObjectId = AtlasObjectId & {
    entityStatus?: AtlasEntityStatus | null;
    displayText?: string | null;
    relationshipType?: string | null;
    relationshipGuid?: string | null;
    relationshipStatus?: "ACTIVE" | "DELETE_PENDING" | null;
    relationshipAttributes?: Record<string, unknown> | null;
    qualifiedName?: string | null;
};

/** `AtlasGlossary`: a glossary and its terms' and categories' headers (GLS-01). */
export type AtlasGlossary = {
    guid?: string | null;
    qualifiedName?: string | null;
    name?: string | null;
    shortDescription?: string | null;
    longDescription?: string | null;
    additionalAttributes?: Record<string, unknown> | null;
    classifications?: AtlasClassification[] | null;
    language?: string | null;
    usage?: string | null;
    terms?: AtlasRelatedTermHeader[] | null;
    categories?: AtlasRelatedCategoryHeader[] | null;
};

/** `AtlasGlossaryCategory`: its glossary anchor, parent, children and terms (GCT-01). */
export type AtlasGlossaryCategory = {
    guid?: string | null;
    qualifiedName?: string | null;
    name?: string | null;
    shortDescription?: string | null;
    longDescription?: string | null;
    additionalAttributes?: Record<string, unknown> | null;
    classifications?: AtlasClassification[] | null;
    anchor?: AtlasGlossaryHeader | null;
    parentCategory?: AtlasRelatedCategoryHeader | null;
    childrenCategories?: AtlasRelatedCategoryHeader[] | null;
    terms?: AtlasRelatedTermHeader[] | null;
};

/**
 * `AtlasGlossaryTerm`: its glossary anchor, categories, assigned entities and
 * related terms by relation (GTM-01). Each relation attribute holds the terms
 * on that side of the relationship.
 */
export type AtlasGlossaryTerm = {
    guid?: string | null;
    qualifiedName?: string | null;
    name?: string | null;
    shortDescription?: string | null;
    longDescription?: string | null;
    additionalAttributes?: Record<string, unknown> | null;
    classifications?: AtlasClassification[] | null;
    examples?: string[] | null;
    abbreviation?: string | null;
    usage?: string | null;
    anchor?: AtlasGlossaryHeader | null;
    assignedEntities?: AtlasRelatedObjectId[] | null;
    categories?: AtlasTermCategorizationHeader[] | null;
    seeAlso?: AtlasRelatedTermHeader[] | null;
    synonyms?: AtlasRelatedTermHeader[] | null;
    antonyms?: AtlasRelatedTermHeader[] | null;
    preferredTerms?: AtlasRelatedTermHeader[] | null;
    preferredToTerms?: AtlasRelatedTermHeader[] | null;
    replacementTerms?: AtlasRelatedTermHeader[] | null;
    replacedBy?: AtlasRelatedTermHeader[] | null;
    translationTerms?: AtlasRelatedTermHeader[] | null;
    translatedTerms?: AtlasRelatedTermHeader[] | null;
    isA?: AtlasRelatedTermHeader[] | null;
    classifies?: AtlasRelatedTermHeader[] | null;
    validValues?: AtlasRelatedTermHeader[] | null;
    validValuesFor?: AtlasRelatedTermHeader[] | null;
};

/** `AtlasGlossaryExtInfo`: the glossary with its terms and categories by GUID (GLS-06, GTM-07). */
export type AtlasGlossaryExtInfo = AtlasGlossary & {
    termInfo?: Record<string, AtlasGlossaryTerm> | null;
    categoryInfo?: Record<string, AtlasGlossaryCategory> | null;
};
