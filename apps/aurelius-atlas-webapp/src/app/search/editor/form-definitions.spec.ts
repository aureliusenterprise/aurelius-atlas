import { FormDefinition, formDefinitions, formLabels, inFormOrder } from "./form-definitions";

/**
 * The legacy forms (EDP-05, EDP-06, EDP-11, EDP-12): each of the ten types
 * names exactly its legacy fields, in the legacy order — the tables of the
 * 7.35 spec, read from `apps/atlas/src/app/search/components/editor/<form>/`.
 */

const FORMS: Record<string, readonly string[]> = {
    m4i_data_entity: [
        "name",
        "definition",
        "dataDomain",
        "parentEntity",
        "childEntity",
        "attributes",
        "businessOwner",
        "steward",
    ],
    m4i_data_attribute: ["name", "definition", "dataEntity", "fields", "businessOwner", "steward"],
    m4i_dataset: [
        "name",
        "definition",
        "collections",
        "parentDataset",
        "childDataset",
        "fields",
        "outputFromProcesses",
        "inputToProcesses",
    ],
    m4i_field: ["name", "definition", "datasets", "parentField", "childField", "attributes"],
    m4i_collection: ["name", "definition", "systems", "datasets"],
    m4i_data_domain: ["name", "definition", "dataEntity", "domainLead"],
    m4i_system: ["name", "definition", "parentSystem", "childSystem", "collections"],
    m4i_generic_process: ["name", "definition", "system", "inputs", "outputs"],
    m4i_person: [
        "name",
        "email",
        "domainLead",
        "businessOwnerEntity",
        "businessOwnerAttribute",
        "stewardEntity",
        "stewardAttribute",
    ],
    m4i_gov_data_quality: [
        "name",
        "ruleDescription",
        "qualityDimension",
        "ruleType",
        "compliantMessage",
        "nonCompliantMessage",
        "expression",
    ],
};

describe("formDefinitions (EDP-05, EDP-06, EDP-11, EDP-12)", () => {
    const definitions = formDefinitions();

    it("EDP-05: the ten legacy types, and no other", () => {
        expect(Object.keys(definitions).sort()).toEqual(Object.keys(FORMS).sort());
    });

    for (const [typeName, fields] of Object.entries(FORMS)) {
        it(`EDP-05: ${typeName} names its legacy fields in their legacy order`, () => {
            expect(definitions[typeName].fields.map((field) => field.attribute)).toEqual(fields);
        });
    }

    it("EDP-06: no form shows typeAlias", () => {
        const named = Object.values(definitions).flatMap((form) => form.fields.map((field) => field.attribute));
        expect(named).not.toContain("typeAlias");
    });

    it("EDP-11: the tag box rides the data entity, data attribute and data domain forms alone", () => {
        const withTags = Object.entries(definitions)
            .filter(([, form]) => form.classifications)
            .map(([typeName]) => typeName)
            .sort();
        expect(withTags).toEqual(["m4i_data_attribute", "m4i_data_domain", "m4i_data_entity"]);
    });

    it("EDP-12: the data quality rule keeps 7.27's quality mode — it has no legacy form here", () => {
        expect(definitions["m4i_data_quality"]).toBeUndefined();
    });

    it("EDP-05: the labels are the legacy dictionary's", () => {
        const labels = formLabels(definitions["m4i_data_entity"]);
        expect(labels["dataDomain"]).toBe("Data domain");
        expect(labels["businessOwner"]).toBe("Data owners");
        expect(formLabels(definitions["m4i_dataset"])["outputFromProcesses"]).toBe("Producers");
    });
});

describe("inFormOrder (EDP-05)", () => {
    const form: FormDefinition = {
        classifications: false,
        fields: [
            { attribute: "name", label: "Name" },
            { attribute: "definition", label: "Definition" },
            { attribute: "missing", label: "Missing" },
        ],
    };

    it("keeps the form's fields in its order, drops the rest, and skips what the type lacks", () => {
        const available = [{ name: "typeAlias" }, { name: "definition" }, { name: "qualifiedName" }, { name: "name" }];
        expect(inFormOrder(form, available).map((field) => field.name)).toEqual(["name", "definition"]);
    });
});
