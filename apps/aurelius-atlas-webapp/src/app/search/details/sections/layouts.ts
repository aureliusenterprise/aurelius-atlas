/**
 * The ten m4i layouts as one config table (DET-16, DD-366; 7.21c's eighth
 * row, DET-33/DD-383; 7.29's tenth, DET-39/DD-518): per type the description
 * box, the People box, the ordered card sections, the stats-bar entries, and
 * the side-navigation entries. The legacy shipped ten copy-pasted layout
 * components (`apps/atlas/src/app/search/details/<type>/` in the Aurelius
 * source); this table is their content, and one renderer draws them all. The
 * person row (7.29) carries the table's three flags: no description box, a
 * grouped stats bar, and the Governance Quality Rules box.
 *
 * Every string is the Aurelius catalogue key it shows (DET-04, SHL-08): the
 * `$localize` id names the key and the fallback text is that key's English
 * source, and both catalogues carry it (checked — `i18n-completeness.spec.ts`
 * stays green untouched). The anchors are the legacy ids
 * (`#related-attributes` and friends) so the navigation's and the stats
 * bar's `#href`s land.
 *
 * 7.22b adds the lineage box's position (LDG-09): the `lineageAfter` anchor
 * names the card box the Lineage Model box follows — the legacy pages put
 * the `#lineage-model` div between two card boxes, and it is no card
 * section, so its place rides the layout row, not the `sections` list.
 *
 * 7.25a adds the Governance Quality Rules box to the list (DET-48, DD-841):
 * the `kind: "gov-quality"` entry every legacy page carried last. It is a
 * card section like the others — the same chrome, the same position rules —
 * but it seeds from its own reads, so it is marked and its own store draws
 * it (DD-841).
 *
 * 7.25c adds the Data Quality score box (DET-56..DET-58, DD-851..DD-853):
 * the `kind: "score"` entry of the seven catalogue pages that drew it, and
 * the `sorts: "score"` flag of the ten card sections that sorted on the
 * score fields (DET-59, DD-854). The score rows themselves ride the view
 * and the cards (AVS-01) — the mapping is the increment's only helper set
 * (DD-852), and since 7.43 it lives in `../../shared/quality-mapping.ts`.
 *
 * 7.43 splits the one file three ways: the shapes live in `section.model.ts`,
 * the score mapping in `../../shared/quality-mapping.ts`, and this file keeps
 * the table and the constants a row's content names. The split moves no row —
 * the eleven layouts render identically, and `search/shared/catalogue-card`
 * stops importing up from `details/` (DD-869).
 */

import {
    type FacetGroupKey,
    type M4iLayoutType,
    type SectionDef,
    type StatDef,
    type TypeLayout,
} from "./section.model";

/**
 * The rules box's two extra sort keys (DET-66): the legacy box's own asks,
 * `['name', 'dataqualityruledimension', 'dqscore']`
 * (`data-quality-cards.component.ts`) — kept raw as DET-59's
 * `qualitySortKey` (in `../../shared/quality-mapping.ts`) keeps the score
 * pages' keys raw.
 */
export const RULE_SORT_KEYS = { dimension: "dataqualityruledimension", score: "dqscore" } as const;

/**
 * The rules box's two extra sort labels (DET-66): the catalogue keys every
 * locale already carries — `dataqualityruledimension` and `dqscore` — so the
 * box needs no new strings (SHL-08).
 */
export const RULE_SORT_LABELS = {
    dimension: $localize`:@@dataqualityruledimension:Dimension`,
    score: $localize`:@@dqscore:Quality Score`,
} as const;

/**
 * The Governance Quality Rules box's title (DET-48): the one key every
 * legacy page drew — nine pages, one unit. Its section entries and the box's
 * own view read this constant, so the string exists once.
 */
export const GOV_QUALITY_TITLE = $localize`:@@search.details.components.governanceQualityCards.title:Governance Quality Rules`;

/**
 * The score box's anchor (DET-56, DET-57): the legacy `#data-quality` div,
 * shared by the box, the stat's link, and the navigation entry — one
 * string so the three can never disagree.
 */
export const SCORE_ANCHOR = "data-quality";

/**
 * The score box's row (DET-56/DET-57, DD-851): the shape stated once, the
 * way `GOV_QUALITY_TITLE` states its title once. Each layout passes its
 * own `...dataQuality` key, so the seven boxes differ only in the label.
 */
const scoreSection = (title: string): SectionDef => ({
    anchor: SCORE_ANCHOR,
    title,
    seedKeys: [],
    facets: [],
    kind: "score",
});

/**
 * The score stat (DET-58, DD-853): the shape stated once. Each layout
 * passes its own `...dataQuality` and word keys — the collection page
 * names a `...dataQualityUnavailable` of its own — so the seven stats
 * differ only in their labels.
 */
const scoreStat = (label: string, unavailable: string): StatDef => ({
    label,
    anchor: SCORE_ANCHOR,
    source: { kind: "score" },
    unavailable,
});

/**
 * The facet group titles (DD-622): each reuses the Aurelius catalogue key
 * the legacy menu label carried — the dictionary keys every locale already
 * carries (SHL-08), the three role groups the People box's own keys
 * (DET-23, DD-629). The Name group has no key, so it keeps the raw
 * titlecased literal the legacy rendered untranslated — DET-21's precedent
 * for the same value in the sort select.
 */
export const FACET_GROUP_TITLES: Readonly<Record<FacetGroupKey, string>> = {
    m4i_data_domain: $localize`:@@deriveddatadomain:Data Domain`,
    m4i_data_entity: $localize`:@@deriveddataentity:Data Entity`,
    domainLead: $localize`:@@search.components.people.domainLead:Domain Lead(s)`,
    businessOwner: $localize`:@@search.components.people.dataOwner:Data Owner(s)`,
    steward: $localize`:@@search.components.people.dataSteward:Data Steward(s)`,
    m4i_collection: $localize`:@@derivedcollection:Collection`,
    m4i_dataset: $localize`:@@deriveddataset:Dataset`,
    m4i_system: $localize`:@@derivedsystem:System`,
    typeName: $localize`:@@typename:Type Name`,
    // No catalogue key: the legacy option value, titlecased raw (DD-622).
    name: `Name`,
    // The governance box's two groups (DET-46): the rule dimension and rule
    // type, both carried by every locale as the legacy menu label.
    dataqualityruledimension: $localize`:@@dataqualityruledimension:Dimension`,
    dataqualitytype: $localize`:@@dataqualitytype:Rule Type`,
};

/**
 * The three role groups in the People box's order (DET-23): where every
 * layout carried the flat people group, it now asks the roles (VCF-18,
 * DD-629). Each counts the door's role relations (AVS-10), so a card
 * whose document awaits its re-derive round simply draws no role rows
 * (VCF-16's rule, read the same way by the facet's empty-group drop).
 */
const ROLE_FACETS: readonly FacetGroupKey[] = ["domainLead", "businessOwner", "steward"];

/**
 * The ten layouts, key for key the spec's table (DET-16, amended by 7.21c's
 * DET-32/DET-33 rows, 7.22b's LDG-09 box positions, 7.22d's LDG-32 lineage
 * entries, 7.27's DET-38 rule row, and 7.29's DET-39 person row). The stats
 * and navigation list the rendered boxes only: every deferred section's stat
 * and link stays out (DD-369); the lineage box's pair returned with the
 * finished box (DD-383's hold-out, ended). Built once at load; `$localize`
 * resolves per locale at compile time.
 */
export const LAYOUTS: Readonly<Record<M4iLayoutType, TypeLayout>> = {
    m4i_data_domain: {
        descriptionTitle: $localize`:@@search.details.domain.description:Description`,
        peopleBox: true,
        peopleTitle: $localize`:@@search.details.domain.people:People`,
        sections: [
            {
                anchor: "related-entities",
                title: $localize`:@@search.details.domain.entityCards.title:Data Entities`,
                seedKeys: ["dataEntity"],
                facets: ROLE_FACETS,
                sorts: "score",
            },
            // DET-56/DET-57 (7.25c, DD-851): the score box in the legacy
            // place — after Data Entities, before the governance box.
            scoreSection($localize`:@@search.details.domain.dataQuality:Data Quality`),
            {
                anchor: "gov-quality",
                title: GOV_QUALITY_TITLE,
                seedKeys: [],
                facets: ["dataqualityruledimension", "dataqualitytype"],
                kind: "gov-quality",
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.domain.dataEntities:Data Entities`,
                anchor: "related-entities",
                source: { kind: "section", anchor: "related-entities" },
            },
            // DET-58 (7.25c, DD-853): the score stat in the legacy place.
            scoreStat(
                $localize`:@@search.details.domain.dataQuality:Data Quality`,
                $localize`:@@search.details.domain.unavailable:Unavailable`,
            ),
            {
                label: $localize`:@@search.details.domain.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.domain.properties:Properties`,
        nav: [
            {
                label: $localize`:@@search.details.domain.description:Description`,
                anchor: "description-details",
            },
            { label: $localize`:@@search.details.domain.people:People`, anchor: "people-details" },
            {
                label: $localize`:@@search.details.domain.dataEntities:Data Entities`,
                anchor: "related-entities",
            },
            { label: $localize`:@@search.details.domain.dataQuality:Data Quality`, anchor: SCORE_ANCHOR },
            {
                label: $localize`:@@search.details.domain.governanceQualityRules:Governance Quality Rules`,
                anchor: "gov-quality",
            },
            { label: $localize`:@@search.details.domain.properties:Properties`, anchor: "properties-details" },
        ],
    },
    m4i_data_entity: {
        descriptionTitle: $localize`:@@search.details.entity.description:Description`,
        peopleBox: true,
        peopleTitle: $localize`:@@search.details.entity.people:People`,
        sections: [
            {
                anchor: "related-attributes",
                title: $localize`:@@search.details.entity.attributesCards.title:Data Attributes`,
                seedKeys: ["attributes"],
                facets: ROLE_FACETS,
                sorts: "score",
            },
            {
                anchor: "related-entities",
                title: $localize`:@@search.details.entity.entitiesCards.title:Child Entities`,
                seedKeys: ["childEntity"],
                facets: ROLE_FACETS,
                sorts: "score",
            },
            // DET-56/DET-57 (7.25c, DD-851): the score box in the legacy
            // place — after Child Entities, before the governance box.
            scoreSection($localize`:@@search.details.entity.dataQuality:Data Quality`),
            {
                anchor: "gov-quality",
                title: GOV_QUALITY_TITLE,
                seedKeys: [],
                facets: ["dataqualityruledimension", "dataqualitytype"],
                kind: "gov-quality",
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.entity.dataAttributes:Data Attributes`,
                anchor: "related-attributes",
                source: { kind: "section", anchor: "related-attributes" },
            },
            {
                label: $localize`:@@search.details.entity.childEntities:Child Entities`,
                anchor: "related-entities",
                source: { kind: "section", anchor: "related-entities" },
            },
            // DET-58 (7.25c, DD-853): the score stat in the legacy place.
            scoreStat(
                $localize`:@@search.details.entity.dataQuality:Data Quality`,
                $localize`:@@search.details.entity.unavailable:Unavailable`,
            ),
            {
                label: $localize`:@@search.details.entity.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.entity.properties:Properties`,
        nav: [
            {
                label: $localize`:@@search.details.entity.description:Description`,
                anchor: "description-details",
            },
            { label: $localize`:@@search.details.entity.people:People`, anchor: "people-details" },
            {
                label: $localize`:@@search.details.entity.dataAttributes:Data Attributes`,
                anchor: "related-attributes",
            },
            {
                label: $localize`:@@search.details.entity.childEntities:Child Entities`,
                anchor: "related-entities",
            },
            { label: $localize`:@@search.details.entity.dataQuality:Data Quality`, anchor: SCORE_ANCHOR },
            {
                label: $localize`:@@search.details.entity.governanceQualityRules:Governance Quality Rules`,
                anchor: "gov-quality",
            },
            { label: $localize`:@@search.details.entity.properties:Properties`, anchor: "properties-details" },
        ],
    },
    m4i_data_attribute: {
        descriptionTitle: $localize`:@@search.details.attribute.description:Description`,
        peopleBox: true,
        peopleTitle: $localize`:@@search.details.attribute.people:People`,
        sections: [
            {
                anchor: "related-fields",
                title: $localize`:@@search.details.attribute.fieldsCards.title:Fields`,
                seedKeys: ["fields"],
                facets: ["m4i_system", "m4i_collection", "m4i_dataset"],
                sorts: "score",
            },
            // DET-56/DET-57 (7.25c, DD-851): the score box in the legacy
            // place — after Fields, before the governance box.
            scoreSection($localize`:@@search.details.attribute.dataQuality:Data Quality`),
            {
                anchor: "gov-quality",
                title: GOV_QUALITY_TITLE,
                seedKeys: [],
                facets: ["dataqualityruledimension", "dataqualitytype"],
                kind: "gov-quality",
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.attribute.fields:Fields`,
                anchor: "related-fields",
                source: { kind: "section", anchor: "related-fields" },
            },
            // DET-58 (7.25c, DD-853): the score stat in the legacy place.
            scoreStat(
                $localize`:@@search.details.attribute.dataQuality:Data Quality`,
                $localize`:@@search.details.attribute.unavailable:Unavailable`,
            ),
            {
                label: $localize`:@@search.details.attribute.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.attribute.properties:Properties`,
        nav: [
            {
                label: $localize`:@@search.details.attribute.description:Description`,
                anchor: "description-details",
            },
            { label: $localize`:@@search.details.attribute.people:People`, anchor: "people-details" },
            { label: $localize`:@@search.details.attribute.fields:Fields`, anchor: "related-fields" },
            { label: $localize`:@@search.details.attribute.dataQuality:Data Quality`, anchor: SCORE_ANCHOR },
            {
                label: $localize`:@@search.details.attribute.governanceQualityRules:Governance Quality Rules`,
                anchor: "gov-quality",
            },
            { label: $localize`:@@search.details.attribute.properties:Properties`, anchor: "properties-details" },
        ],
    },
    m4i_field: {
        descriptionTitle: $localize`:@@search.details.field.description:Description`,
        // The legacy field page carries no People box (DET-23's note: the
        // steward end exists, the box does not).
        peopleBox: false,
        peopleTitle: "",
        sections: [
            {
                anchor: "related-attributes",
                title: $localize`:@@search.details.field.attributesCards.title:Data Attributes`,
                seedKeys: ["attributes"],
                facets: ["m4i_data_domain", "m4i_data_entity", ...ROLE_FACETS],
            },
            {
                anchor: "related-fields",
                title: $localize`:@@search.details.field.fieldsCards.title:Child Fields`,
                seedKeys: ["childField"],
                facets: ["m4i_system", "m4i_collection", "m4i_dataset"],
                sorts: "score",
            },
            // DET-56/DET-57 (7.25c, DD-851): the score box in the legacy
            // place — after Child Fields and before the rules box, the
            // field template's own order (`#data-quality`, then
            // `#related-rules`). DD-369's hold-out ends here: the score
            // rows are the view's own `quality` (AVS-01, 14.5 ASQ-04/05).
            scoreSection($localize`:@@search.details.field.dataQuality:Data Quality`),
            // DET-35 (7.24): the field's own `dataQuality` relationship end seeds
            // the rules box (DD-444). The legacy read the App Search
            // `data_quality` index instead. DET-66 (7.25e, DD-867): the box
            // orders by the score rows the field's view carries, and keeps
            // DET-35's seed — the legacy's unscored-rules drop (DV-207).
            {
                anchor: "related-rules",
                title: $localize`:@@search.details.field.dataQualityCards.title:Data Quality Rules`,
                seedKeys: ["dataQuality"],
                // The legacy asked the rule dimension (DV-168): no card
                // field carries it, so the popover shows the empty line.
                facets: [],
                sorts: "rules",
            },
            {
                anchor: "gov-quality",
                title: GOV_QUALITY_TITLE,
                seedKeys: [],
                facets: ["dataqualityruledimension", "dataqualitytype"],
                kind: "gov-quality",
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.field.dataAttributes:Data Attributes`,
                anchor: "related-attributes",
                source: { kind: "section", anchor: "related-attributes" },
            },
            {
                label: $localize`:@@search.details.field.childFields:Child Fields`,
                anchor: "related-fields",
                source: { kind: "section", anchor: "related-fields" },
            },
            // DET-58 (7.25c, DD-853): the score stat in the legacy place,
            // before the rules stat.
            scoreStat(
                $localize`:@@search.details.field.dataQuality:Data Quality`,
                $localize`:@@search.details.field.unavailable:Unavailable`,
            ),
            // DET-36 (7.24): the rules stat in the legacy place. The legacy
            // showed its `dqscorecnt_overall` here; the value is now the
            // DET-24 section count (DD-444).
            {
                label: $localize`:@@search.details.field.dataQualityRules:Data Quality Rules`,
                anchor: "related-rules",
                source: { kind: "section", anchor: "related-rules" },
            },
            {
                label: $localize`:@@search.details.field.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.field.properties:Properties`,
        nav: [
            { label: $localize`:@@search.details.field.description:Description`, anchor: "description-details" },
            {
                label: $localize`:@@search.details.field.dataAttributes:Data Attributes`,
                anchor: "related-attributes",
            },
            { label: $localize`:@@search.details.field.childFields:Child Fields`, anchor: "related-fields" },
            // DET-58 (7.25c): the score link in the legacy nav place — after
            // Child Fields, and the field page places it before the two
            // rules links (the template's own order).
            { label: $localize`:@@search.details.field.dataQuality:Data Quality`, anchor: SCORE_ANCHOR },
            { label: $localize`:@@search.details.field.dataQualityRules:Data Quality Rules`, anchor: "related-rules" },
            {
                label: $localize`:@@search.details.field.governanceQualityRules:Governance Quality Rules`,
                anchor: "gov-quality",
            },
            { label: $localize`:@@search.details.field.properties:Properties`, anchor: "properties-details" },
        ],
    },
    // DET-50 (7.25b): the governance rule's own page. The legacy dispatches
    // the name `m4i_gov_data_quality` to its governance-quality component,
    // and nothing else carries that name, so the row is a direct hit. The
    // legacy's top-to-bottom order (gov-quality-details.component.html):
    // the description, the three stats, the Compliance Chart, the
    // Non-compliant box, the Compliant box, the properties. The two card
    // boxes seed from the rule's verdicts, not an end (DD-848), so they
    // carry no seed key, and the box draws its rows through the sections
    // store's seed (DET-53). The facet groups are the person box's four —
    // the legacy asked the eight of `ENTITY_SEARCH_FACETS` that Aurelius'
    // catalogue answers (DV-201). Nav in the legacy order: the two boxes,
    // the properties (the description and chart are not nav entries).
    m4i_gov_data_quality: {
        descriptionTitle: $localize`:@@search.details.govQuality.description:Description`,
        peopleBox: false,
        peopleTitle: "",
        sections: [
            {
                anchor: "related-non-compliants",
                title: $localize`:@@search.details.govQuality.nonCompliantCards.title:Non-compliant`,
                seedKeys: [],
                seedFrom: "verdicts",
                facets: ["typeName", "m4i_data_domain", "m4i_data_entity", "name"],
            },
            {
                anchor: "related-compliants",
                title: $localize`:@@search.details.govQuality.compliantCards.title:Compliant`,
                seedKeys: [],
                seedFrom: "verdicts",
                facets: ["typeName", "m4i_data_domain", "m4i_data_entity", "name"],
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.govQuality.nonCompliant:Non-compliant`,
                anchor: "related-non-compliants",
                source: { kind: "section", anchor: "related-non-compliants" },
            },
            {
                label: $localize`:@@search.details.govQuality.compliant:Compliant`,
                anchor: "related-compliants",
                source: { kind: "section", anchor: "related-compliants" },
            },
            {
                label: $localize`:@@search.details.govQuality.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.govQuality.properties:Properties`,
        nav: [
            {
                label: $localize`:@@search.details.govQuality.nonCompliant:Non-compliant`,
                anchor: "related-non-compliants",
            },
            {
                label: $localize`:@@search.details.govQuality.compliant:Compliant`,
                anchor: "related-compliants",
            },
            {
                label: $localize`:@@search.details.govQuality.properties:Properties`,
                anchor: "properties-details",
            },
        ],
        complianceChart: {
            title: $localize`:@@search.details.govQuality.complianceChart:Compliance Chart`,
            nonCompliant: $localize`:@@search.details.govQuality.nonCompliant:Non-compliant`,
            compliant: $localize`:@@search.details.govQuality.compliant:Compliant`,
        },
    },
    // DET-38 (7.27, DD-495): the rule's own page. A rule is defined by the
    // fields it checks, so its page lists them the way every other page
    // lists what it relates to — the rule→field end the editor writes
    // (EDT-25's picker) seeds the box, and the field's rules box (DET-35)
    // reads the same edge from the other side.
    m4i_data_quality: {
        descriptionTitle: $localize`:@@search.details.rule.description:Description`,
        peopleBox: false,
        peopleTitle: "",
        sections: [
            {
                anchor: "related-fields",
                title: $localize`:@@search.details.rule.fieldsCards.title:Fields`,
                seedKeys: ["fields"],
                // The legacy rule page carries no facet ask (DD-619).
                facets: [],
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.rule.fields:Fields`,
                anchor: "related-fields",
                source: { kind: "section", anchor: "related-fields" },
            },
            {
                label: $localize`:@@search.details.rule.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.rule.properties:Properties`,
        nav: [
            {
                label: $localize`:@@search.details.rule.description:Description`,
                anchor: "description-details",
            },
            { label: $localize`:@@search.details.rule.fields:Fields`, anchor: "related-fields" },
            { label: $localize`:@@search.details.rule.properties:Properties`, anchor: "properties-details" },
        ],
    },
    m4i_dataset: {
        descriptionTitle: $localize`:@@search.details.dataset.description:Description`,
        peopleBox: false,
        peopleTitle: "",
        sections: [
            {
                anchor: "related-fields",
                title: $localize`:@@search.details.dataset.fieldsCards.title:Fields`,
                seedKeys: ["fields"],
                facets: ROLE_FACETS,
                sorts: "score",
            },
            {
                anchor: "related-datasets",
                title: $localize`:@@search.details.dataset.datasetsCards.title:Child Datasets`,
                seedKeys: ["childDataset"],
                facets: ROLE_FACETS,
                sorts: "score",
            },
            // LDG-09: the Lineage Model box sits after Child Datasets and
            // before Producers (dataset-details.component.html L115) — the
            // `lineageAfter` row below, not a card section.
            // DET-32, DD-382: the dataset's own lineage ends — the processes
            // it outputs from (`outputFromProcesses`) and outputs to
            // (`inputToProcesses`) — the demo's Producers and Consumers
            // boxes. 7.21a's deferral misread them as reverse lookups; the
            // legacy components select these very ends off the opened entity.
            {
                anchor: "related-producers",
                title: $localize`:@@search.details.dataset.producersCards.title:Producers`,
                seedKeys: ["outputFromProcesses"],
                facets: ["typeName", "m4i_system"],
            },
            {
                anchor: "related-consumers",
                title: $localize`:@@search.details.dataset.consumersCards.title:Consumers`,
                seedKeys: ["inputToProcesses"],
                facets: ["typeName", "m4i_system"],
            },
            // DET-56/DET-57 (7.25c, DD-851): the score box in the legacy
            // place — after Consumers, before the governance box.
            scoreSection($localize`:@@search.details.dataset.dataQuality:Data Quality`),
            {
                anchor: "gov-quality",
                title: GOV_QUALITY_TITLE,
                seedKeys: [],
                facets: ["dataqualityruledimension", "dataqualitytype"],
                kind: "gov-quality",
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.dataset.fields:Fields`,
                anchor: "related-fields",
                source: { kind: "section", anchor: "related-fields" },
            },
            {
                label: $localize`:@@search.details.dataset.childDatasets:Child Datasets`,
                anchor: "related-datasets",
                source: { kind: "section", anchor: "related-datasets" },
            },
            // LDG-32 (DD-383's hold-out returns): the lineage entry reads
            // the page's fetch state (DD-400), in the legacy slot before
            // Producers.
            {
                label: $localize`:@@search.details.dataset.lineageModel:Lineage Model`,
                anchor: "lineage-model",
                source: { kind: "lineage" },
                available: $localize`:@@search.details.dataset.available:Available`,
                unavailable: $localize`:@@search.details.dataset.unavailable:Unavailable`,
            },
            {
                label: $localize`:@@search.details.dataset.producers:Producers`,
                anchor: "related-producers",
                source: { kind: "section", anchor: "related-producers" },
            },
            {
                label: $localize`:@@search.details.dataset.consumers:Consumers`,
                anchor: "related-consumers",
                source: { kind: "section", anchor: "related-consumers" },
            },
            // DET-58 (7.25c, DD-853): the score stat in the legacy place.
            scoreStat(
                $localize`:@@search.details.dataset.dataQuality:Data Quality`,
                $localize`:@@search.details.dataset.unavailable:Unavailable`,
            ),
            {
                label: $localize`:@@search.details.dataset.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.dataset.properties:Properties`,
        nav: [
            { label: $localize`:@@search.details.dataset.description:Description`, anchor: "description-details" },
            { label: $localize`:@@search.details.dataset.fields:Fields`, anchor: "related-fields" },
            {
                label: $localize`:@@search.details.dataset.childDatasets:Child Datasets`,
                anchor: "related-datasets",
            },
            // LDG-32: the lineage link returns to the legacy slot (DD-383's
            // hold-out ends with the finished box).
            {
                label: $localize`:@@search.details.dataset.lineageModel:Lineage Model`,
                anchor: "lineage-model",
            },
            {
                label: $localize`:@@search.details.dataset.producers:Producers`,
                anchor: "related-producers",
            },
            {
                label: $localize`:@@search.details.dataset.consumers:Consumers`,
                anchor: "related-consumers",
            },
            { label: $localize`:@@search.details.dataset.dataQuality:Data Quality`, anchor: SCORE_ANCHOR },
            {
                label: $localize`:@@search.details.dataset.governanceQualityRules:Governance Quality Rules`,
                anchor: "gov-quality",
            },
            { label: $localize`:@@search.details.dataset.properties:Properties`, anchor: "properties-details" },
        ],
        // LDG-09: the Lineage Model box follows Child Datasets (the legacy
        // dataset page's order: datasets, lineage, producers, consumers).
        lineageAfter: "related-datasets",
    },
    m4i_collection: {
        descriptionTitle: $localize`:@@search.details.collection.description:Description`,
        peopleBox: false,
        peopleTitle: "",
        sections: [
            {
                anchor: "related-datasets",
                title: $localize`:@@search.details.collection.datasetsCards.title:Datasets`,
                seedKeys: ["datasets"],
                facets: ROLE_FACETS,
                sorts: "score",
            },
            // DET-56/DET-57 (7.25c, DD-851): the score box in the legacy
            // place — after Datasets, before the governance box.
            scoreSection($localize`:@@search.details.collection.dataQuality:Data Quality`),
            {
                anchor: "gov-quality",
                title: GOV_QUALITY_TITLE,
                seedKeys: [],
                facets: ["dataqualityruledimension", "dataqualitytype"],
                kind: "gov-quality",
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.collection.datasets:Datasets`,
                anchor: "related-datasets",
                source: { kind: "section", anchor: "related-datasets" },
            },
            // DET-58 (7.25c, DD-853): the score stat in the legacy place.
            // The collection page's template names its own word key —
            // `...dataQualityUnavailable`, not the plain `...unavailable`.
            scoreStat(
                $localize`:@@search.details.collection.dataQuality:Data Quality`,
                $localize`:@@search.details.collection.dataQualityUnavailable:Unavailable`,
            ),
            {
                label: $localize`:@@search.details.collection.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.collection.properties:Properties`,
        nav: [
            {
                label: $localize`:@@search.details.collection.description:Description`,
                anchor: "description-details",
            },
            { label: $localize`:@@search.details.collection.datasets:Datasets`, anchor: "related-datasets" },
            { label: $localize`:@@search.details.collection.dataQuality:Data Quality`, anchor: SCORE_ANCHOR },
            {
                label: $localize`:@@search.details.collection.governanceQualityRules:Governance Quality Rules`,
                anchor: "gov-quality",
            },
            { label: $localize`:@@search.details.collection.properties:Properties`, anchor: "properties-details" },
        ],
    },
    m4i_system: {
        descriptionTitle: $localize`:@@search.details.system.description:Description`,
        peopleBox: false,
        peopleTitle: "",
        sections: [
            {
                anchor: "related-collections",
                title: $localize`:@@search.details.system.collectionsCards.title:Collections`,
                seedKeys: ["collections"],
                facets: ROLE_FACETS,
                sorts: "score",
            },
            {
                anchor: "related-systems",
                title: $localize`:@@search.details.system.systemsCards.title:Subsystems`,
                seedKeys: ["childSystem"],
                facets: ROLE_FACETS,
                sorts: "score",
            },
            {
                anchor: "related-processes",
                title: $localize`:@@search.details.system.processesCards.title:Processes`,
                seedKeys: ["processes"],
                facets: ["typeName", "m4i_system"],
            },
            // DET-56/DET-57 (7.25c, DD-851): the score box in the legacy
            // place — after Processes, before the governance box.
            scoreSection($localize`:@@search.details.system.dataQuality:Data Quality`),
            {
                anchor: "gov-quality",
                title: GOV_QUALITY_TITLE,
                seedKeys: [],
                facets: ["dataqualityruledimension", "dataqualitytype"],
                kind: "gov-quality",
            },
        ],
        // The legacy systems/processes stats read the systems' governance
        // scores, which the bar never shows; the bar stays Collections,
        // Data Quality, Properties (DET-58's place, the legacy's).
        stats: [
            {
                label: $localize`:@@search.details.system.collections:Collections`,
                anchor: "related-collections",
                source: { kind: "section", anchor: "related-collections" },
            },
            // DET-58 (7.25c, DD-853): the score stat in the legacy place —
            // the bar holds it after Collections, even though the box list
            // keeps Subsystems and Processes before the score box.
            scoreStat(
                $localize`:@@search.details.system.dataQuality:Data Quality`,
                $localize`:@@search.details.system.unavailable:Unavailable`,
            ),
            {
                label: $localize`:@@search.details.system.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.system.properties:Properties`,
        nav: [
            { label: $localize`:@@search.details.system.description:Description`, anchor: "description-details" },
            { label: $localize`:@@search.details.system.collections:Collections`, anchor: "related-collections" },
            { label: $localize`:@@search.details.system.subSystems:Subsystems`, anchor: "related-systems" },
            { label: $localize`:@@search.details.system.processes:Processes`, anchor: "related-processes" },
            { label: $localize`:@@search.details.system.dataQuality:Data Quality`, anchor: SCORE_ANCHOR },
            {
                label: $localize`:@@search.details.system.governanceQualityRules:Governance Quality Rules`,
                anchor: "gov-quality",
            },
            { label: $localize`:@@search.details.system.properties:Properties`, anchor: "properties-details" },
        ],
    },
    // DET-33, DD-383: the legacy's ninth page enters as the eighth row. The
    // lineage-model box (and its stat and link) stays deferred with the ADR
    // 055 chain's data path; the page carries a `processOwner` end but its
    // legacy box does not exist, so the row has no People box (DET-23's
    // `m4i_field` case).
    m4i_generic_process: {
        descriptionTitle: $localize`:@@search.details.process.description:Description`,
        peopleBox: false,
        peopleTitle: "",
        sections: [
            {
                anchor: "related-systems",
                title: $localize`:@@search.details.process.systemsCards.title:Systems`,
                seedKeys: ["system"],
                facets: ["typeName", "m4i_system"],
            },
            // LDG-09: the Lineage Model box sits after Systems and before
            // Inputs (process-details.component.html L74) — the
            // `lineageAfter` row below, not a card section.
            {
                anchor: "related-inputs",
                title: $localize`:@@search.details.process.inputCards.title:Inputs`,
                seedKeys: ["inputs"],
                facets: ["typeName", "m4i_system", "m4i_collection"],
            },
            {
                anchor: "related-outputs",
                title: $localize`:@@search.details.process.outputCards.title:Outputs`,
                seedKeys: ["outputs"],
                facets: ["typeName", "m4i_system", "m4i_collection"],
            },
            {
                anchor: "gov-quality",
                title: GOV_QUALITY_TITLE,
                seedKeys: [],
                facets: ["dataqualityruledimension", "dataqualitytype"],
                kind: "gov-quality",
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.process.systems:Systems`,
                anchor: "related-systems",
                source: { kind: "section", anchor: "related-systems" },
            },
            // LDG-32: the lineage entry in the legacy slot before Inputs
            // (the process pair's keys, DD-383's hold-out returns).
            {
                label: $localize`:@@search.details.process.lineageModel:Lineage Model`,
                anchor: "lineage-model",
                source: { kind: "lineage" },
                available: $localize`:@@search.details.process.available:Available`,
                unavailable: $localize`:@@search.details.process.unavailable:Unavailable`,
            },
            {
                label: $localize`:@@search.details.process.inputs:Inputs`,
                anchor: "related-inputs",
                source: { kind: "section", anchor: "related-inputs" },
            },
            {
                label: $localize`:@@search.details.process.outputs:Outputs`,
                anchor: "related-outputs",
                source: { kind: "section", anchor: "related-outputs" },
            },
            {
                label: $localize`:@@search.details.process.properties:Properties`,
                anchor: "properties-details",
                source: { kind: "properties" },
            },
        ],
        propertiesTitle: $localize`:@@search.details.process.properties:Properties`,
        nav: [
            { label: $localize`:@@search.details.process.description:Description`, anchor: "description-details" },
            { label: $localize`:@@search.details.process.systems:Systems`, anchor: "related-systems" },
            // LDG-32: the lineage link in the legacy slot (the DD-383
            // hold-out ends with the finished box).
            {
                label: $localize`:@@search.details.process.lineageModel:Lineage Model`,
                anchor: "lineage-model",
            },
            { label: $localize`:@@search.details.process.inputs:Inputs`, anchor: "related-inputs" },
            { label: $localize`:@@search.details.process.outputs:Outputs`, anchor: "related-outputs" },
            {
                label: $localize`:@@search.details.process.governanceQualityRules:Governance Quality Rules`,
                anchor: "gov-quality",
            },
            { label: $localize`:@@search.details.process.properties:Properties`, anchor: "properties-details" },
        ],
        lineageAfter: "related-systems",
    },
    // DET-39 (7.29, DD-518): the person page enters as the tenth row. It is
    // the table's first row without a description box (the legacy's has
    // none), the first with a grouped stats bar (DET-40's four headed
    // boxes), and the first with the Governance Quality Rules box (DET-42,
    // DV-155). The one card section merges the five responsibility ends
    // (DET-41, DD-519); `ProcessOwner` seeds nothing (DV-154), and the box
    // has no People box, no lineage box, and no People title.
    m4i_person: {
        descriptionTitle: "",
        descriptionBox: false,
        peopleBox: false,
        peopleTitle: "",
        sections: [
            {
                anchor: "governance-roles",
                title: $localize`:@@search.details.person.governanceRolesCards.title:Governance Responsibilities`,
                seedKeys: [
                    "domainLead",
                    "businessOwnerEntity",
                    "businessOwnerAttribute",
                    "stewardEntity",
                    "stewardAttribute",
                ],
                facets: ["typeName", "m4i_data_domain", "m4i_data_entity", "name"],
            },
            {
                anchor: "gov-quality",
                title: GOV_QUALITY_TITLE,
                seedKeys: [],
                facets: ["dataqualityruledimension", "dataqualitytype"],
                kind: "gov-quality",
            },
        ],
        // The grouped bar renders these (DET-40); the flat list stays empty
        // because the person page has no flat stats to render.
        stats: [],
        statsGroups: [
            {
                heading: $localize`:@@search.details.person.domainLead:Domain Lead`,
                items: [
                    {
                        label: $localize`:@@search.details.person.dataDomains:Data Domains`,
                        anchor: "governance-roles",
                        source: { kind: "end", key: "domainLead" },
                    },
                ],
            },
            {
                heading: $localize`:@@search.details.person.dataOwner:Data Owner`,
                items: [
                    {
                        label: $localize`:@@search.details.person.dataEntities:Data Entities`,
                        anchor: "governance-roles",
                        source: { kind: "end", key: "businessOwnerEntity" },
                    },
                    {
                        label: $localize`:@@search.details.person.dataAttributes:Data Attributes`,
                        anchor: "governance-roles",
                        source: { kind: "end", key: "businessOwnerAttribute" },
                    },
                ],
            },
            {
                heading: $localize`:@@search.details.person.dataSteward:Data Steward`,
                items: [
                    {
                        label: $localize`:@@search.details.person.dataEntities:Data Entities`,
                        anchor: "governance-roles",
                        source: { kind: "end", key: "stewardEntity" },
                    },
                    {
                        label: $localize`:@@search.details.person.dataAttributes:Data Attributes`,
                        anchor: "governance-roles",
                        source: { kind: "end", key: "stewardAttribute" },
                    },
                ],
            },
            {
                heading: $localize`:@@search.details.person.other:Other`,
                items: [
                    {
                        label: $localize`:@@search.details.person.properties:Properties`,
                        anchor: "properties-details",
                        source: { kind: "properties" },
                    },
                ],
            },
        ],
        propertiesTitle: $localize`:@@search.details.person.properties:Properties`,
        nav: [
            {
                label: $localize`:@@search.details.person.governanceResponsibilities:Governance Responsibilities`,
                anchor: "governance-roles",
            },
            {
                label: $localize`:@@search.details.person.governanceQualityRules:Governance Quality Rules`,
                anchor: "gov-quality",
            },
            { label: $localize`:@@search.details.person.properties:Properties`, anchor: "properties-details" },
        ],
    },
};

/**
 * The layout for one of the seven names, or undefined (DET-15's direct hit;
 * the supertype walk lives with the screen's layout store).
 * @param typeName the entity's type name
 * @returns the layout, or undefined for every other type
 */
export function layoutForTypeName(typeName: string): TypeLayout | undefined {
    return (LAYOUTS as Record<string, TypeLayout | undefined>)[typeName];
}

/**
 * Whether a layout carries the Governance Quality Rules box (DET-48, the
 * nine legacy pages). The section list is the source: the entry's presence
 * is the box's presence, replacing 7.29's `govQualityBox` flag.
 * @param layout the layout, or undefined for the default screen
 */
export function hasGovQualityBox(layout: TypeLayout | undefined): boolean {
    return layout?.sections.some((section) => section.kind === "gov-quality") ?? false;
}

/**
 * The score box's placeholder — `search.components.dataqualitylist.notAvailable`,
 * the legacy list's own `notAvailable` branch (DET-56, DET-63). The card
 * never shows it (DET-60): UIC-37's empty-string rule.
 */
export const DATA_QUALITY_NOT_AVAILABLE = $localize`:@@search.components.dataqualitylist.notAvailable:No data quality results available`;
