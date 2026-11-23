import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import type { EntityView } from "aurelius-atlas-data-access";

import { type GovSectionView, DetailsGovQualityState } from "./gov-quality.state";

/**
 * The Governance Quality Rules store (DET-42, DD-520/DD-521): the rule read
 * is one basic search with the type's qualified-name prefix; the verdict
 * read is the editor's own validate call over the opened entity, joined on
 * `ruleGuid`. Both failures swallow quietly. Specs ride the sections
 * store's idiom — `provideHttpClientTesting`, `expectOne` + `flush`.
 */
const SEARCH_URL = "/api/atlas/v2/search/basic";
const VALIDATE_URL = "/validate-entity/";

/** The opened person, as the read door answers it (VDR-01): the prefix and the validate body both read it. */
const PERSON: EntityView = {
    guid: "pe-1",
    typeName: "m4i_person",
    displayText: "Ada",
    status: "ACTIVE",
    stale: false,
    attributes: { name: "Ada" },
};

/** A rule header of the search answer. */
function rule(guid: string, name: string, extra: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        guid,
        typeName: "m4i_gov_data_quality",
        displayText: name,
        attributes: { name, qualityDimension: "COMPLETENESS", ...extra },
    };
}

function setup() {
    TestBed.configureTestingModule({
        providers: [DetailsGovQualityState, provideHttpClient(), provideHttpClientTesting()],
    });
    const store = TestBed.inject(DetailsGovQualityState);
    const httpMock = TestBed.inject(HttpTestingController);
    return { store, httpMock };
}

/** Deliver the in-flight rule search. */
function flushRules(
    httpMock: HttpTestingController,
    entities: Record<string, unknown>[],
    status?: { status: number; statusText: string },
) {
    const request = httpMock.expectOne(SEARCH_URL);
    request.flush(status ? {} : { entities }, status);
    return request;
}

/** Deliver the in-flight verdict read. */
function flushVerdicts(
    httpMock: HttpTestingController,
    body: Record<string, unknown>,
    status?: { status: number; statusText: string },
) {
    const request = httpMock.expectOne(VALIDATE_URL);
    request.flush(status ? {} : body, status);
    return request;
}

describe("Gov-quality store (DET-42)", () => {
    it("loads no calls for no entity (DET-42)", () => {
        const { store, httpMock } = setup();
        store.load(null);
        expect(store.rows()).toEqual([]);
        expect(store.loading()).toBe(false);
        httpMock.verify();
    });

    it("searches the type's rules with the prefix and the header attributes (DET-42, DD-520)", () => {
        const { store, httpMock } = setup();
        store.load(PERSON);

        const request = httpMock.expectOne(SEARCH_URL);
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({
            typeName: "m4i_gov_data_quality",
            excludeDeletedEntities: true,
            includeSubTypes: false,
            limit: 100,
            attributes: ["name", "ruleDescription", "qualityDimension", "ruleType", "active"],
            entityFilters: {
                attributeName: "qualifiedName",
                operator: "startsWith",
                attributeValue: "m4i_person--",
            },
        });
        // The verdict read runs beside the search, over the opened entity in
        // the draft shape (DD-632): entityFromView's Atlas-shaped body, the
        // pick-less person carrying an empty relationshipAttributes.
        const validate = httpMock.expectOne(VALIDATE_URL);
        expect(validate.request.body).toEqual({
            guid: "pe-1",
            typeName: "m4i_person",
            status: "ACTIVE",
            attributes: { name: "Ada" },
            classifications: [],
            relationshipAttributes: {},
        });

        request.flush({ entities: [] });
        validate.flush({ verdicts: [], unreadRules: [] });
        httpMock.verify();
    });

    it("the draft the verdict read posts carries the view's sections as picks (VEV-08, DD-632)", () => {
        const { store, httpMock } = setup();
        store.load({
            ...PERSON,
            classificationNames: ["Finance"],
            sections: [{ attribute: "fields", entities: [{ guid: "f-1", name: "amount", typeName: "m4i_field" }] }],
        });

        const request = httpMock.expectOne(VALIDATE_URL);
        // The end the view carries rides relationshipAttributes (DD-608's
        // helper, the editor's shape), so a relationship rule answers the box
        // with the ends on record instead of refusing them (VEV-08).
        expect(request.request.body).toEqual({
            guid: "pe-1",
            typeName: "m4i_person",
            status: "ACTIVE",
            attributes: { name: "Ada" },
            classifications: [{ typeName: "Finance", entityGuid: "pe-1" }],
            relationshipAttributes: {
                fields: [{ guid: "f-1", typeName: "m4i_field", displayText: "amount", relationshipStatus: "ACTIVE" }],
            },
        });
        request.flush({ verdicts: [], unreadRules: [] });
        httpMock.expectOne(SEARCH_URL).flush({ entities: [] });
        httpMock.verify();
    });

    it("builds rows in name order, clears loading, and joins verdicts (DET-42)", () => {
        const { store, httpMock } = setup();
        store.load(PERSON);

        expect(store.loading()).toBe(true);
        flushRules(httpMock, [
            rule("r2", "Person has a name", { ruleDescription: "A name is stored." }),
            rule("r1", "Person has an email address", { active: true }),
        ]);
        flushVerdicts(httpMock, {
            verdicts: [
                {
                    ruleGuid: "r1",
                    ruleName: "x",
                    attribute: "email",
                    dimension: "COMPLETENESS",
                    compliant: false,
                    message: "no email",
                },
            ],
            unreadRules: [{ ruleGuid: "r2", ruleName: "y", error: "boom" }],
        });

        expect(store.loading()).toBe(false);
        expect(store.rows()).toEqual([
            {
                guid: "r2",
                name: "Person has a name",
                description: "A name is stored.",
                dimension: "COMPLETENESS",
                ruleType: "",
                compliant: null,
            },
            {
                guid: "r1",
                name: "Person has an email address",
                description: "",
                dimension: "COMPLETENESS",
                ruleType: "",
                compliant: false,
            },
        ]);
        httpMock.verify();
    });

    it("drops an inactive rule and keeps a text or missing active (DET-42, VEV-03)", () => {
        const { store, httpMock } = setup();
        store.load(PERSON);

        flushRules(httpMock, [
            rule("off", "Off", { active: false }),
            rule("raw", "Raw", { active: { raw: false } }), // the stored raw form is still false
            rule("text", "Text", { active: "true" }),
            rule("bare", "Bare"),
        ]);
        flushVerdicts(httpMock, { verdicts: [], unreadRules: [] });

        expect(store.rows().map((row) => row.guid)).toEqual(["bare", "text"]);
        httpMock.verify();
    });

    it("unwraps a raw text attribute and falls back to display text (DET-42)", () => {
        const { store, httpMock } = setup();
        store.load(PERSON);

        flushRules(httpMock, [
            {
                guid: "r1",
                typeName: "m4i_gov_data_quality",
                displayText: "Shown",
                attributes: { name: { raw: "Unwrapped" }, ruleDescription: { raw: "Body." } },
            },
            { guid: "r2", typeName: "m4i_gov_data_quality", displayText: "Only display", attributes: {} },
        ]);
        flushVerdicts(httpMock, { verdicts: [], unreadRules: [] });

        expect(store.rows()).toEqual([
            { guid: "r2", name: "Only display", description: "", dimension: "", ruleType: "", compliant: null },
            { guid: "r1", name: "Unwrapped", description: "Body.", dimension: "", ruleType: "", compliant: null },
        ]);
        httpMock.verify();
    });

    it("a failed rule read keeps the box empty and alerts nothing (DET-42, DD-521)", () => {
        const { store, httpMock } = setup();
        store.load(PERSON);

        flushRules(httpMock, [], { status: 500, statusText: "Server Error" });
        flushVerdicts(httpMock, { verdicts: [], unreadRules: [] });

        expect(store.rows()).toEqual([]);
        expect(store.loading()).toBe(false);
        httpMock.verify();
    });

    it("a failed verdict read keeps the rows, every one iconless (DET-42, DD-521)", () => {
        const { store, httpMock } = setup();
        store.load(PERSON);

        flushRules(httpMock, [rule("r1", "Person has a name")]);
        httpMock.expectOne(VALIDATE_URL).flush({}, { status: 502, statusText: "Bad Gateway" });

        expect(store.rows()).toEqual([
            {
                guid: "r1",
                name: "Person has a name",
                description: "",
                dimension: "COMPLETENESS",
                ruleType: "",
                compliant: null,
            },
        ]);
        httpMock.verify();
    });

    it("a superseded entity drops the stale answers (DET-42, DET-08's sibling)", () => {
        const { store, httpMock } = setup();
        store.load(PERSON);

        const staleSearch = httpMock.expectOne(SEARCH_URL);
        const staleValidate = httpMock.expectOne(VALIDATE_URL);

        const next: EntityView = { ...PERSON, guid: "pe-2", attributes: { name: "Lin" } };
        store.load(next);
        expect(store.rows()).toEqual([]); // the new round starts empty
        expect(store.loading()).toBe(true);

        staleSearch.flush({ entities: [rule("r9", "Stale rule")] });
        staleValidate.flush({
            verdicts: [{ ruleGuid: "r9", ruleName: "", attribute: "", dimension: "", compliant: true, message: "" }],
        });
        expect(store.rows()).toEqual([]); // neither stale answer paints

        flushRules(httpMock, [rule("r1", "Fresh rule")]);
        flushVerdicts(httpMock, { verdicts: [], unreadRules: [] });
        expect(store.rows().map((row) => row.guid)).toEqual(["r1"]);
        httpMock.verify();
    });

    it("a clear mid-flight drops the in-flight answers", () => {
        const { store, httpMock } = setup();
        store.load(PERSON);

        const search = httpMock.expectOne(SEARCH_URL);
        const validate = httpMock.expectOne(VALIDATE_URL);
        store.load(null);
        expect(store.loading()).toBe(false);

        search.flush({ entities: [rule("r1", "Rule")] });
        validate.flush({ verdicts: [], unreadRules: [] });
        expect(store.rows()).toEqual([]);
        httpMock.verify();
    });
});

/** A seeded rule: the basic test's rule, widened by the type (DET-42 amended). */
interface SeedRule {
    guid: string;
    name: string;
    dimension?: string;
    ruleType?: string;
    description?: string;
    /** The verdict; left out, the rule is unread and shows no verdict. */
    compliant?: boolean | null;
}

/**
 * Bring the box up with the given rules, answering both reads in one go.
 * The store sorts the rules by name (DET-42), so that order is what the
 * Relevance sort shows — the seeds below name themselves accordingly.
 */
function seed(store: DetailsGovQualityState, httpMock: HttpTestingController, rules: SeedRule[]): void {
    store.load(PERSON);
    // The helper spreads its extra straight into the header's attributes.
    flushRules(
        httpMock,
        rules.map((seedRule) =>
            rule(seedRule.guid, seedRule.name, {
                ruleDescription: seedRule.description ?? "",
                qualityDimension: seedRule.dimension ?? "",
                ruleType: seedRule.ruleType ?? "",
                active: true,
            }),
        ),
    );
    flushVerdicts(httpMock, {
        verdicts: rules
            .filter((seedRule) => seedRule.compliant !== undefined)
            .map((seedRule) => ({
                ruleGuid: seedRule.guid,
                ruleName: seedRule.name,
                attribute: "",
                dimension: seedRule.dimension ?? "",
                compliant: seedRule.compliant,
                message: "",
            })),
        unreadRules: rules.filter((seedRule) => seedRule.compliant === undefined).map((seedRule) => seedRule.guid),
    });
}

/** The four rules the sorts and facets turn on: two dimensions, two types,
 * one refused, one unread, and one carrying neither a dimension nor a type. */
const SORT_SEED: SeedRule[] = [
    { guid: "a", name: "Alpha", dimension: "COMPLETENESS", ruleType: "COLUMN", compliant: true },
    { guid: "b", name: "bravo", dimension: "ACCURACY", ruleType: "TABLE", compliant: false },
    // Charlie and delta carry no verdict at all — the aux could not read them.
    { guid: "c", name: "Charlie" },
    { guid: "d", name: "delta", dimension: "ACCURACY", ruleType: "TABLE" },
];

describe("The Governance Quality Rules card section (DET-44..DET-48, DD-842)", () => {
    /** The store with the four seed rules on screen. */
    function arrive() {
        const { store, httpMock } = setup();
        seed(store, httpMock, SORT_SEED);
        return { store, httpMock };
    }

    /** One popover group of the view, by key. */
    function group(view: GovSectionView, key: string) {
        return view.facets.find((facet) => facet.key === key)!;
    }

    it("the section chrome starts on Relevance with both facet groups (DET-44, DET-46)", () => {
        const { store } = arrive();

        const view = store.view();
        expect(view.kind).toBe("gov-quality");
        expect(view.anchor).toBe("gov-quality");
        expect(view.title).toBe("Governance Quality Rules");
        expect(view.count).toBe(4);
        expect(view.countShown).toBe(4);
        expect(view.filtered).toBe(false);
        expect(view.filterActive).toBe(false);
        expect(view.sort).toBe("relevance");
        expect(view.descending).toBe(false);
        expect(view.query).toBeNull();
        expect(view.allLoaded).toBe(true);
        expect(view.loading).toBe(false);
        // The two groups, in the legacy order, counted over the rows (VCF-12).
        expect(view.facets.map((facet) => [facet.key, facet.title])).toEqual([
            ["dataqualityruledimension", "Dimension"],
            ["dataqualitytype", "Rule Type"],
        ]);
        expect(group(view, "dataqualityruledimension").items.map((item) => [item.label, item.count])).toEqual([
            ["ACCURACY", 2],
            ["COMPLETENESS", 1],
        ]);
        expect(group(view, "dataqualitytype").items.map((item) => [item.label, item.count])).toEqual([
            ["TABLE", 2],
            ["COLUMN", 1],
        ]);
        // The sort menu, in the legacy order with Relevance first (DET-45).
        expect(view.sortOptions.map((option) => option.key)).toEqual([
            "relevance",
            "name",
            "dataqualityruledimension",
            "compliant",
            "dataqualitytype",
        ]);
    });

    it("the sorts order the rows, by key with missing values last (DET-45)", () => {
        const { store } = arrive();
        const guids = () => store.view().rows.map((row) => row.guid);

        // Relevance is the rule read's order: the name (DET-42).
        expect(guids()).toEqual(["a", "b", "c", "d"]);

        // Name — the same order, case-insensitively (Alpha, bravo, Charlie,
        // delta): the legacy's own first sort option.
        store.setSort("name");
        expect(guids()).toEqual(["a", "b", "c", "d"]);

        // The dimension sorts missing values last ascending, first descending.
        store.setSort("dataqualityruledimension");
        expect(store.view().descending).toBe(false);
        expect(guids()).toEqual(["b", "d", "a", "c"]);
        store.toggleDirection();
        expect(store.view().descending).toBe(true);
        expect(guids()).toEqual(["c", "a", "b", "d"]);

        // Ties keep the Relevance order in both directions (DET-45): the
        // ACCURACY pair b, d stays b before d in each direction. A new sort
        // key keeps the direction the button holds (the legacy's two controls
        // are independent), so it goes back to ascending here.
        store.toggleDirection();
        store.setSort("compliant");
        expect(store.view().descending).toBe(false);
        // Passed, refused, then the no-verdict rows in Relevance order.
        expect(guids()).toEqual(["a", "b", "c", "d"]);
        store.toggleDirection();
        // Reversed: the no-verdict rows lead, still in Relevance order, then
        // the refused rule, then the passed one.
        expect(guids()).toEqual(["c", "d", "b", "a"]);

        // The rule type sorts the same way (DET-45): COLUMN, then the two
        // TABLE rows in Relevance order, then the row with no type last.
        store.toggleDirection(); // back to ascending
        store.setSort("dataqualitytype");
        expect(store.view().descending).toBe(false);
        expect(guids()).toEqual(["a", "b", "d", "c"]);
    });

    it("the facet filters select within and across the groups (DET-46)", () => {
        const { store } = arrive();
        const guids = () => store.view().rows.map((row) => row.guid);

        // One value narrows to its rows; the other group recounts over them.
        store.toggleFacet("dataqualityruledimension", "ACCURACY", true);
        expect(guids()).toEqual(["b", "d"]);
        expect(store.view().filtered).toBe(true);
        expect(store.view().filterActive).toBe(true);
        expect(store.view().count).toBe(4);
        expect(store.view().countShown).toBe(2);
        expect(group(store.view(), "dataqualitytype").items.map((item) => [item.label, item.count])).toEqual([
            ["TABLE", 2],
        ]);

        // A second value in the same group widens it (VCF-11's OR).
        store.toggleFacet("dataqualityruledimension", "COMPLETENESS", true);
        expect(guids()).toEqual(["a", "b", "d"]);

        // A value in the other group narrows across groups (VCF-11's AND):
        // Alpha is a COLUMN rule, so it drops.
        store.toggleFacet("dataqualitytype", "TABLE", true);
        expect(guids()).toEqual(["b", "d"]);

        // Unticking the last value of a group clears it (VCF-12's sibling).
        store.toggleFacet("dataqualitytype", "TABLE", false);
        expect(guids()).toEqual(["a", "b", "d"]);
        store.toggleFacet("dataqualityruledimension", "COMPLETENESS", false);
        store.toggleFacet("dataqualityruledimension", "ACCURACY", false);
        expect(store.view().filtered).toBe(false);
        expect(store.view().filterActive).toBe(false);
    });

    it("the keyword searches the name, description, dimension and type (DET-47)", () => {
        const { store, httpMock } = setup();
        seed(store, httpMock, [
            {
                guid: "a",
                name: "Email present",
                description: "Every person has one",
                dimension: "COMPLETENESS",
                ruleType: "COLUMN",
                compliant: true,
            },
            {
                guid: "b",
                name: "Region code",
                description: "",
                dimension: "ACCURACY",
                ruleType: "TABLE",
                compliant: true,
            },
            { guid: "c", name: "Table layout", description: "", dimension: "", ruleType: "TABLE", compliant: true },
        ]);
        const guids = () => store.view().rows.map((row) => row.guid);

        // Matched on the name.
        store.setText("email");
        expect(guids()).toEqual(["a"]);
        expect(store.view().filtered).toBe(true);
        expect(store.view().query).toBe("email");

        // Matched on the description.
        store.setText("Every");
        expect(guids()).toEqual(["a"]);

        // Matched on the dimension, case-insensitive.
        store.setText("accuracy");
        expect(guids()).toEqual(["b"]);

        // Matched on the rule type.
        store.setText("table");
        expect(guids()).toEqual(["b", "c"]);

        // An empty keyword shows all the rows again.
        store.setText("");
        expect(store.view().query).toBeNull();
        expect(store.view().filtered).toBe(false);
        expect(store.view().filterActive).toBe(false);
    });

    it("the section shows nine rows at a time and grows by nine (DET-47)", () => {
        const { store, httpMock } = setup();
        // Padded names: the store's name order is then the seeded numeric order.
        const twenty: SeedRule[] = Array.from({ length: 20 }, (_, index) => {
            const suffix = String(index).padStart(2, "0");
            return {
                guid: `r${suffix}`,
                name: `Rule ${suffix}`,
                dimension: "COMPLETENESS",
                ruleType: "COLUMN",
                compliant: true,
            };
        });
        seed(store, httpMock, twenty);
        const guids = () => store.view().rows.map((row) => row.guid);

        let view = store.view();
        expect(view.count).toBe(20);
        expect(guids()).toEqual(twenty.slice(0, 9).map((seedRule) => seedRule.guid));
        expect(view.allLoaded).toBe(false);
        // Unfiltered, the count line shows the whole set (DET-20 carried).
        expect(view.countShown).toBe(20);

        store.nextPage();
        view = store.view();
        expect(guids()).toEqual(twenty.slice(0, 18).map((seedRule) => seedRule.guid));
        expect(view.allLoaded).toBe(false);

        store.nextPage();
        view = store.view();
        expect(view.rows).toHaveLength(20);
        expect(view.allLoaded).toBe(true);
        // Asking past the end changes nothing.
        store.nextPage();
        expect(store.view().rows).toHaveLength(20);
    });

    it("the count line clears every control and returns page one (DET-44)", () => {
        const { store, httpMock } = setup();
        const twenty: SeedRule[] = Array.from({ length: 20 }, (_, index) => {
            const suffix = String(index).padStart(2, "0");
            return {
                guid: `r${suffix}`,
                name: `${index % 2 === 0 ? "Match" : "Rule"} ${suffix}`,
                dimension: index % 2 === 0 ? "COMPLETENESS" : "ACCURACY",
                ruleType: "COLUMN",
                compliant: true,
            };
        });
        seed(store, httpMock, twenty);

        store.setText("Match");
        store.toggleFacet("dataqualityruledimension", "COMPLETENESS", true);
        store.setSort("name");
        store.toggleDirection();
        store.nextPage();
        expect(store.view().rows.length).toBe(10);
        expect(store.view().filterActive).toBe(true);

        store.reset();

        const view = store.view();
        expect(view.query).toBeNull();
        expect(view.sort).toBe("relevance");
        expect(view.descending).toBe(false);
        expect(view.filterActive).toBe(false);
        expect(view.filtered).toBe(false);
        expect(view.count).toBe(20);
        expect(view.rows).toHaveLength(9); // page one of the unfiltered set
        expect(view.facets.every((facet) => facet.items.every((item) => !item.checked))).toBe(true);
    });

    it("a reload returns the chrome to its defaults (DET-44)", () => {
        const { store, httpMock } = arrive();

        store.setText("bravo");
        store.setSort("name");
        store.load(PERSON);
        flushRules(httpMock, [rule("r1", "Fresh rule")]);
        flushVerdicts(httpMock, { verdicts: [], unreadRules: [] });

        const view = store.view();
        expect(view.query).toBeNull();
        expect(view.sort).toBe("relevance");
        expect(view.descending).toBe(false);
        expect(view.filterActive).toBe(false);
        expect(store.rows().map((row) => row.guid)).toEqual(["r1"]);
    });

    it("a rule with no verdict sorts after the refused one (DET-45)", () => {
        const { store, httpMock } = arrive();

        // Charlie and delta carry no verdict; the compliant sort puts them
        // after the refused row (DET-45), and the rows themselves stay.
        store.setSort("compliant");
        expect(store.view().rows.map((row) => [row.guid, row.compliant])).toEqual([
            ["a", true],
            ["b", false],
            ["c", null],
            ["d", null],
        ]);
    });
});
