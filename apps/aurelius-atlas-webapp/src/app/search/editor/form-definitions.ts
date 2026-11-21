/**
 * The legacy editor's forms, one per type (7.35, EDP-05, DD-817): the fields
 * each hand-written form of the Aurelius webapp showed, in its order, with its
 * labels (`apps/atlas/src/app/search/components/editor/<form>/`). A type here
 * shows these fields and no other; a type not here keeps the generic form of
 * EDT-03 (EDP-13, DD-819). `typeAlias` is in no form: every legacy form hid it
 * (EDP-06).
 *
 * Each entry names an attribute, plain or relationship: the editor finds it
 * among the fields the type definition yields and keeps it where the entry
 * stands. A plain attribute renders as a control, a relationship as a picker,
 * as the type definition says. The labels are the legacy dictionary's keys,
 * `search.components.editor.<form>.<field>`; the editor drops their baked-in
 * required star (DD-356).
 */

/** One field of a legacy form: the attribute it writes and its label (EDP-05). */
export type FormEntry = {
    readonly attribute: string;
    readonly label: string;
};

/** One legacy form: its fields in order, and whether it carries the tag box (EDP-11). */
export type FormDefinition = {
    readonly fields: readonly FormEntry[];
    readonly classifications: boolean;
};

const entry = (attribute: string, label: string): FormEntry => ({ attribute, label });

/**
 * The ten legacy forms by type name (EDP-05). `m4i_data_quality` is not here: it
 * keeps 7.27's quality mode (EDP-12, DD-819).
 * @returns the form definition of each type the legacy edited with a form of its own
 */
export function formDefinitions(): Readonly<Record<string, FormDefinition>> {
    const name = entry("name", $localize`:@@search.components.editor.entity.name:Name*`);
    const definition = entry("definition", $localize`:@@search.components.editor.entity.definition:Definition`);
    return {
        m4i_data_entity: {
            classifications: true,
            fields: [
                name,
                definition,
                entry("dataDomain", $localize`:@@search.components.editor.entity.dataDomain:Data domain`),
                entry("parentEntity", $localize`:@@search.components.editor.entity.parentEntity:Parent entity`),
                entry("childEntity", $localize`:@@search.components.editor.entity.childEntities:Child entities`),
                entry("attributes", $localize`:@@search.components.editor.entity.dataAttributes:Data attributes`),
                entry("businessOwner", $localize`:@@search.components.editor.entity.dataOwners:Data owners`),
                entry("steward", $localize`:@@search.components.editor.entity.dataStewards:Data stewards`),
            ],
        },
        m4i_data_attribute: {
            classifications: true,
            fields: [
                entry("name", $localize`:@@search.components.editor.attribute.name:Name*`),
                entry("definition", $localize`:@@search.components.editor.attribute.definition:Definition`),
                entry("dataEntity", $localize`:@@search.components.editor.attribute.dataentity:Data entity`),
                entry("fields", $localize`:@@search.components.editor.attribute.fields:Fields`),
                entry("businessOwner", $localize`:@@search.components.editor.attribute.dataowners:Data owners`),
                entry("steward", $localize`:@@search.components.editor.attribute.datastewards:Data stewards`),
            ],
        },
        m4i_dataset: {
            classifications: false,
            fields: [
                entry("name", $localize`:@@search.components.editor.dataset.name:Name*`),
                entry("definition", $localize`:@@search.components.editor.dataset.definition:Definition`),
                entry("collections", $localize`:@@search.components.editor.dataset.collection:Collection`),
                entry("parentDataset", $localize`:@@search.components.editor.dataset.parentDataset:Parent dataset`),
                entry("childDataset", $localize`:@@search.components.editor.dataset.childDataset:Child datasets`),
                entry("fields", $localize`:@@search.components.editor.dataset.fields:Fields`),
                entry("outputFromProcesses", $localize`:@@search.components.editor.dataset.producers:Producers`),
                entry("inputToProcesses", $localize`:@@search.components.editor.dataset.consumers:Consumers`),
            ],
        },
        m4i_field: {
            classifications: false,
            fields: [
                entry("name", $localize`:@@search.components.editor.field.name:Name*`),
                entry("definition", $localize`:@@search.components.editor.field.definition:Definition`),
                entry("datasets", $localize`:@@search.components.editor.field.dataset:Dataset`),
                entry("parentField", $localize`:@@search.components.editor.field.parentField:Parent field`),
                entry("childField", $localize`:@@search.components.editor.field.childFields:Child fields`),
                entry("attributes", $localize`:@@search.components.editor.field.dataAttribute:Data attribute`),
            ],
        },
        m4i_collection: {
            classifications: false,
            fields: [
                entry("name", $localize`:@@search.components.editor.collection.name:Name*`),
                entry("definition", $localize`:@@search.components.editor.collection.definition:Definition`),
                entry("systems", $localize`:@@search.components.editor.collection.system:System`),
                entry("datasets", $localize`:@@search.components.editor.collection.datasets:Datasets`),
            ],
        },
        m4i_data_domain: {
            classifications: true,
            fields: [
                entry("name", $localize`:@@search.components.editor.domain.name:Name*`),
                entry("definition", $localize`:@@search.components.editor.domain.definition:Definition`),
                entry("dataEntity", $localize`:@@search.components.editor.domain.dataEntities:Data entities`),
                entry("domainLead", $localize`:@@search.components.editor.domain.domainLeads:Domain leads`),
            ],
        },
        m4i_system: {
            classifications: false,
            fields: [
                entry("name", $localize`:@@search.components.editor.system.name:Name*`),
                entry("definition", $localize`:@@search.components.editor.system.definition:Definition`),
                entry("parentSystem", $localize`:@@search.components.editor.system.parentSystem:Parent system`),
                entry("childSystem", $localize`:@@search.components.editor.system.subSystems:Subsystems`),
                entry("collections", $localize`:@@search.components.editor.system.collections:Collections`),
            ],
        },
        m4i_generic_process: {
            classifications: false,
            fields: [
                entry("name", $localize`:@@search.components.editor.process.name:Name*`),
                entry("definition", $localize`:@@search.components.editor.process.definition:Definition`),
                entry("system", $localize`:@@search.components.editor.process.system:System`),
                entry("inputs", $localize`:@@search.components.editor.process.inputs:Inputs`),
                entry("outputs", $localize`:@@search.components.editor.process.outputs:Outputs`),
            ],
        },
        m4i_person: {
            classifications: false,
            fields: [
                entry("name", $localize`:@@search.components.editor.person.name:Name*`),
                entry("email", $localize`:@@search.components.editor.person.email:Email*`),
                entry("domainLead", $localize`:@@search.components.editor.person.domainLead:Domain lead`),
                entry(
                    "businessOwnerEntity",
                    $localize`:@@search.components.editor.person.dataOwnerEntities:Data owner entities`,
                ),
                entry(
                    "businessOwnerAttribute",
                    $localize`:@@search.components.editor.person.dataOwnerAttributes:Data owner attributes`,
                ),
                entry(
                    "stewardEntity",
                    $localize`:@@search.components.editor.person.stewardEntity:Data steward entities`,
                ),
                entry(
                    "stewardAttribute",
                    $localize`:@@search.components.editor.person.stewardAttribute:Data steward attributes`,
                ),
            ],
        },
        m4i_gov_data_quality: {
            classifications: false,
            fields: [
                entry("name", $localize`:@@search.components.editor.govQuality.name:Name*`),
                entry(
                    "ruleDescription",
                    $localize`:@@search.components.editor.govQuality.ruleDescription:Rule description`,
                ),
                entry("qualityDimension", $localize`:@@search.components.editor.govQuality.dimension:Dimension`),
                entry("ruleType", $localize`:@@search.components.editor.govQuality.ruleType:Rule type`),
                entry(
                    "compliantMessage",
                    $localize`:@@search.components.editor.govQuality.compliantMessage:Compliant message`,
                ),
                entry(
                    "nonCompliantMessage",
                    $localize`:@@search.components.editor.govQuality.nonCompliantMessage:Non-compliant message`,
                ),
                entry("expression", $localize`:@@search.components.editor.govQuality.expression:Expression*`),
            ],
        },
    };
}

/**
 * The fields of a legacy form, in its order (EDP-05): each entry's field from
 * `available`, by name; an entry the type definition has no field for is
 * skipped, and a field no entry names is not shown.
 * @param definition the type's legacy form
 * @param available the fields the type definition yields, keyed by `name`
 * @returns the fields to render, in the form's order
 */
export function inFormOrder<T extends { readonly name: string }>(
    definition: FormDefinition,
    available: readonly T[],
): T[] {
    const byName = new Map(available.map((field) => [field.name, field]));
    return definition.fields.flatMap((field) => {
        const found = byName.get(field.attribute);
        return found ? [found] : [];
    });
}

/**
 * The labels a legacy form gives its fields, by attribute (EDP-05): laid over
 * the editor's catalogue labels, so the form's own wording wins.
 * @param definition the type's legacy form
 * @returns the label of each attribute the form names
 */
export function formLabels(definition: FormDefinition): Record<string, string> {
    return Object.fromEntries(definition.fields.map((field) => [field.attribute, field.label]));
}
