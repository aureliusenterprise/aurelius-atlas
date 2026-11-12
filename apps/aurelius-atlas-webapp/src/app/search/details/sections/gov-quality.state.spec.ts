import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import type { AtlasEntity } from "aurelius-atlas-data-access";

import { DetailsGovQualityState } from "./gov-quality.state";

/**
 * The Governance Quality Rules store (DET-42, DD-520/DD-521): the rule read
 * is one basic search with the type's qualified-name prefix; the verdict
 * read is the editor's own validate call over the opened entity, joined on
 * `ruleGuid`. Both failures swallow quietly. Specs ride the sections
 * store's idiom — `provideHttpClientTesting`, `expectOne` + `flush`.
 */
const SEARCH_URL = "/api/atlas/v2/search/basic";
const VALIDATE_URL = "/validate-entity/";

/** The opened person: the prefix and the validate body both read it. */
const PERSON: AtlasEntity = {
    guid: "pe-1",
    typeName: "m4i_person",
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
            attributes: ["name", "ruleDescription", "qualityDimension", "active"],
            entityFilters: {
                attributeName: "qualifiedName",
                operator: "startsWith",
                attributeValue: "m4i_person--",
            },
        });
        // The verdict read runs beside the search, on the opened entity.
        const validate = httpMock.expectOne(VALIDATE_URL);
        expect(validate.request.body).toEqual(PERSON);

        request.flush({ entities: [] });
        validate.flush({ verdicts: [], unreadRules: [] });
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
                compliant: null,
            },
            {
                guid: "r1",
                name: "Person has an email address",
                description: "",
                dimension: "COMPLETENESS",
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
            { guid: "r2", name: "Only display", description: "", dimension: "", compliant: null },
            { guid: "r1", name: "Unwrapped", description: "Body.", dimension: "", compliant: null },
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
            { guid: "r1", name: "Person has a name", description: "", dimension: "COMPLETENESS", compliant: null },
        ]);
        httpMock.verify();
    });

    it("a superseded entity drops the stale answers (DET-42, DET-08's sibling)", () => {
        const { store, httpMock } = setup();
        store.load(PERSON);

        const staleSearch = httpMock.expectOne(SEARCH_URL);
        const staleValidate = httpMock.expectOne(VALIDATE_URL);

        const next: AtlasEntity = { ...PERSON, guid: "pe-2", attributes: { name: "Lin" } };
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
