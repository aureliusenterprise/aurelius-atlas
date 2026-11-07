/**
 * The eight m4i layouts as one config table (DET-16, DD-366; 7.21c's eighth
 * row, DET-33/DD-383): per type the description box, the People box, the
 * ordered card sections, the stats-bar entries, and the side-navigation
 * entries. The legacy shipped nine copy-pasted layout components
 * (`apps/atlas/src/app/search/details/<type>/` in the Aurelius source); this
 * table is their content, and one renderer draws them all (the person page
 * stays deferred — the last row 7.21c does not take).
 *
 * Every string is the Aurelius catalogue key it shows (DET-04, SHL-08): the
 * `$localize` id names the key and the fallback text is that key's English
 * source, and both catalogues carry it (checked — `i18n-completeness.spec.ts`
 * stays green untouched). The anchors are the legacy ids
 * (`#related-attributes` and friends) so the navigation's and the stats
 * bar's `#href`s land.
 */

/** One card section of a layout (DET-17..DET-22 render it). */
export interface SectionDef {
    /** The box's anchor id without the `#` — the legacy section id. */
    readonly anchor: string;
    /** The box title (the `detailsCards.title` key's text). */
    readonly title: string;
    /** The `relationshipAttributes` keys whose entries seed the section. */
    readonly seedKeys: readonly string[];
}

/** Which count a stat shows: a section's seed count, or the properties rows. */
export type StatSource = { kind: "section"; anchor: string } | { kind: "properties" };

/** One stats-bar entry (DET-24 renders it; Data Quality stays out, DD-369). */
export interface StatDef {
    /** The heading's label (the layout's stat key's text). */
    readonly label: string;
    /** The anchor the heading links to, without the `#`. */
    readonly anchor: string;
    /** Which count the stat shows. */
    readonly source: StatSource;
}

/** One side-navigation entry (DET-25 renders the layout's set). */
export interface NavDef {
    /** The entry's label. */
    readonly label: string;
    /** The anchor, without the `#`. */
    readonly anchor: string;
}

/** One type's layout: everything below the header that differs per type. */
export interface TypeLayout {
    /** The description box's title (the layout's own `description` key). */
    readonly descriptionTitle: string;
    /** Whether the layout renders the People box (DET-23). */
    readonly peopleBox: boolean;
    /** The People box's title, when it has one. */
    readonly peopleTitle: string;
    /** The card sections, in legacy order. */
    readonly sections: readonly SectionDef[];
    /** The stats-bar entries, in legacy order. */
    readonly stats: readonly StatDef[];
    /** The properties accordion's title (the layout's own `properties` key). */
    readonly propertiesTitle: string;
    /** The side-navigation entries, in legacy order. */
    readonly nav: readonly NavDef[];
}

/** The layout key: one of the eight m4i catalogue types. */
export type M4iLayoutType =
    | "m4i_data_domain"
    | "m4i_data_entity"
    | "m4i_data_attribute"
    | "m4i_field"
    | "m4i_dataset"
    | "m4i_collection"
    | "m4i_system"
    | "m4i_generic_process";

/**
 * The eight layouts, key for key the spec's table (DET-16, amended by 7.21c's
 * DET-32/DET-33 rows). The stats and navigation list the rendered boxes only:
 * every deferred section's stat and link stays out (DD-369, and DD-383's
 * lineage-model entries among them — a link to a box that is not rendered
 * would strand the reader). Built once at load; `$localize` resolves per
 * locale at compile time.
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
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.domain.dataEntities:Data Entities`,
                anchor: "related-entities",
                source: { kind: "section", anchor: "related-entities" },
            },
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
            },
            {
                anchor: "related-entities",
                title: $localize`:@@search.details.entity.entitiesCards.title:Child Entities`,
                seedKeys: ["childEntity"],
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
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.attribute.fields:Fields`,
                anchor: "related-fields",
                source: { kind: "section", anchor: "related-fields" },
            },
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
            },
            {
                anchor: "related-fields",
                title: $localize`:@@search.details.field.fieldsCards.title:Child Fields`,
                seedKeys: ["childField"],
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
            { label: $localize`:@@search.details.field.properties:Properties`, anchor: "properties-details" },
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
            },
            {
                anchor: "related-datasets",
                title: $localize`:@@search.details.dataset.datasetsCards.title:Child Datasets`,
                seedKeys: ["childDataset"],
            },
            // DET-32, DD-382: the dataset's own lineage ends — the processes
            // it outputs from (`outputFromProcesses`) and outputs to
            // (`inputToProcesses`) — the demo's Producers and Consumers
            // boxes. 7.21a's deferral misread them as reverse lookups; the
            // legacy components select these very ends off the opened entity.
            {
                anchor: "related-producers",
                title: $localize`:@@search.details.dataset.producersCards.title:Producers`,
                seedKeys: ["outputFromProcesses"],
            },
            {
                anchor: "related-consumers",
                title: $localize`:@@search.details.dataset.consumersCards.title:Consumers`,
                seedKeys: ["inputToProcesses"],
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
            // DET-32: the legacy bar's Producers and Consumers counts (the
            // lineage-model and Data Quality entries stay out, DD-369/DD-383).
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
            // DET-32: the two lineage links in the legacy positions (the
            // deferred lineage-model link stays out, DD-383).
            {
                label: $localize`:@@search.details.dataset.producers:Producers`,
                anchor: "related-producers",
            },
            {
                label: $localize`:@@search.details.dataset.consumers:Consumers`,
                anchor: "related-consumers",
            },
            { label: $localize`:@@search.details.dataset.properties:Properties`, anchor: "properties-details" },
        ],
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
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.collection.datasets:Datasets`,
                anchor: "related-datasets",
                source: { kind: "section", anchor: "related-datasets" },
            },
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
            },
            {
                anchor: "related-systems",
                title: $localize`:@@search.details.system.systemsCards.title:Subsystems`,
                seedKeys: ["childSystem"],
            },
            {
                anchor: "related-processes",
                title: $localize`:@@search.details.system.processesCards.title:Processes`,
                seedKeys: ["processes"],
            },
        ],
        // The legacy systems/processes stats read the systems' governance
        // scores; with no DQ source both stats stay out (DD-369) and the bar
        // keeps Collections and Properties.
        stats: [
            {
                label: $localize`:@@search.details.system.collections:Collections`,
                anchor: "related-collections",
                source: { kind: "section", anchor: "related-collections" },
            },
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
            },
            {
                anchor: "related-inputs",
                title: $localize`:@@search.details.process.inputCards.title:Inputs`,
                seedKeys: ["inputs"],
            },
            {
                anchor: "related-outputs",
                title: $localize`:@@search.details.process.outputCards.title:Outputs`,
                seedKeys: ["outputs"],
            },
        ],
        stats: [
            {
                label: $localize`:@@search.details.process.systems:Systems`,
                anchor: "related-systems",
                source: { kind: "section", anchor: "related-systems" },
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
            { label: $localize`:@@search.details.process.inputs:Inputs`, anchor: "related-inputs" },
            { label: $localize`:@@search.details.process.outputs:Outputs`, anchor: "related-outputs" },
            { label: $localize`:@@search.details.process.properties:Properties`, anchor: "properties-details" },
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
