import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import type { EntityView } from "aurelius-atlas-data-access";

import { DetailsRuleVerdictsState } from "./rule-verdicts.state";

/**
 * The rule page's verdict store (DET-51, DET-52, DET-55, DD-850): the screen's
 * one read of part-0's door, split into the two sets the legacy drew and
 * counted, and the chart's score. Specs ride the sections store's idiom —
 * `provideHttpClientTesting`, `expectOne` + `flush`.
 */
const VERDICTS_URL = "/api/aurelius/v1/rule/verdicts";

/** The opened governance rule, as the read door answers it (VDR-01). */
const RULE: EntityView = {
    guid: "rule-1",
    typeName: "m4i_gov_data_quality",
    displayText: "Name filled",
    status: "ACTIVE",
    stale: false,
    attributes: { name: "Name filled" },
};

/** One door row: the judged entity, its verdict, and the legacy's extras. */
function row(entity: string, compliant: boolean | null): Record<string, unknown> {
    return { entity, compliant, name: entity, message: "The dataset carries no name" };
}

function setup() {
    TestBed.configureTestingModule({
        providers: [DetailsRuleVerdictsState, provideHttpClient(), provideHttpClientTesting()],
    });
    const store = TestBed.inject(DetailsRuleVerdictsState);
    const httpMock = TestBed.inject(HttpTestingController);
    return { store, httpMock };
}

/** Deliver the in-flight verdict read. */
function flushVerdicts(
    httpMock: HttpTestingController,
    verdicts: Record<string, unknown>[],
    status?: { status: number; statusText: string },
) {
    const request = httpMock.expectOne(VERDICTS_URL);
    request.flush(status ? {} : { verdicts }, status);
    return request;
}

describe("Rule verdicts store (DET-51)", () => {
    it("asks nothing and holds nothing for no entity (DET-51, DD-850)", () => {
        const { store, httpMock } = setup();
        store.load(null);
        expect(store.rows()).toEqual([]);
        expect(store.loading()).toBe(false);
        expect(store.nonCompliantGuids()).toEqual([]);
        expect(store.compliantGuids()).toEqual([]);
        expect(store.score()).toBe(0);
        httpMock.verify();
    });

    it("asks the door once for the opened rule's GUID (DET-51, VDR-15)", () => {
        const { store, httpMock } = setup();
        store.load(RULE);
        expect(store.loading()).toBe(true);

        const request = httpMock.expectOne(VERDICTS_URL);
        expect(request.request.method).toBe("POST");
        expect(request.request.body).toEqual({ rule: "rule-1" });
        request.flush({ verdicts: [] });
        expect(store.loading()).toBe(false);
        httpMock.verify();
    });

    it("splits the rows on compliant and seeds the two boxes in door order (DET-51, DET-53)", () => {
        const { store, httpMock } = setup();
        store.load(RULE);
        flushVerdicts(httpMock, [
            row("e-1", false),
            row("e-2", true),
            row("e-3", false),
            row("e-4", null),
            row("e-5", true),
        ]);

        // The two sets, in the store's document id order (ASG-09).
        expect(store.nonCompliantGuids()).toEqual(["e-1", "e-3"]);
        expect(store.compliantGuids()).toEqual(["e-2", "e-5"]);
        // DET-52: the stats' counts are the two sets' lengths.
        expect(store.nonCompliantCount()).toBe(2);
        expect(store.compliantCount()).toBe(2);
        // DET-51: the legacy's formula over the judged entities — 2 of 4.
        expect(store.score()).toBe(50);
        httpMock.verify();
    });

    it("counts a row with no verdict in neither box and never in the score (DET-51)", () => {
        const { store, httpMock } = setup();
        store.load(RULE);
        flushVerdicts(httpMock, [row("e-1", false), row("e-2", null), row("e-3", null)]);

        expect(store.nonCompliantGuids()).toEqual(["e-1"]);
        expect(store.compliantGuids()).toEqual([]);
        expect(store.nonCompliantCount()).toBe(1);
        expect(store.compliantCount()).toBe(0);
        expect(store.score()).toBe(0);
        httpMock.verify();
    });

    it("scores every judged entity passing at 100 (DET-51, DET-54)", () => {
        const { store, httpMock } = setup();
        store.load(RULE);
        flushVerdicts(httpMock, [row("e-1", true), row("e-2", true)]);

        expect(store.nonCompliantCount()).toBe(0);
        expect(store.compliantCount()).toBe(2);
        expect(store.score()).toBe(100);
        httpMock.verify();
    });

    it("scores a rule judging nothing at 0, the legacy's NaN painted no arc (DET-51)", () => {
        const { store, httpMock } = setup();
        store.load(RULE);
        flushVerdicts(httpMock, []);

        expect(store.nonCompliantCount()).toBe(0);
        expect(store.compliantCount()).toBe(0);
        expect(store.score()).toBe(0);
        httpMock.verify();
    });

    it("keeps the page empty and quiet on a failed read (DET-55)", () => {
        const { store, httpMock } = setup();
        store.load(RULE);
        flushVerdicts(httpMock, [], { status: 500, statusText: "Server Error" });

        // DET-49's posture: both boxes empty at count 0, score 0, no loading.
        expect(store.rows()).toEqual([]);
        expect(store.nonCompliantGuids()).toEqual([]);
        expect(store.compliantGuids()).toEqual([]);
        expect(store.nonCompliantCount()).toBe(0);
        expect(store.compliantCount()).toBe(0);
        expect(store.score()).toBe(0);
        expect(store.loading()).toBe(false);
        httpMock.verify();
    });

    it("clears the page when the entity goes away (DET-51, DD-850)", () => {
        const { store, httpMock } = setup();
        store.load(RULE);
        flushVerdicts(httpMock, [row("e-1", false)]);
        expect(store.nonCompliantCount()).toBe(1);

        store.load(null);
        expect(store.rows()).toEqual([]);
        expect(store.nonCompliantGuids()).toEqual([]);
        expect(store.compliantGuids()).toEqual([]);
        expect(store.score()).toBe(0);
        httpMock.verify();
    });

    it("drops a superseded answer and keeps the newest (DET-51, DET-08's guard)", () => {
        const { store, httpMock } = setup();
        store.load(RULE);
        // The editor's save re-read: the second arrival re-asks while the
        // first is still in flight, and only the newest answer paints.
        store.load(RULE);
        const [first, second] = httpMock.match(VERDICTS_URL);

        first.flush({ verdicts: [row("old", false)] });
        expect(store.rows()).toEqual([]);
        expect(store.nonCompliantGuids()).toEqual([]);
        expect(store.loading()).toBe(true);

        second.flush({ verdicts: [row("new", true)] });
        expect(store.compliantGuids()).toEqual(["new"]);
        expect(store.nonCompliantGuids()).toEqual([]);
        expect(store.loading()).toBe(false);
        httpMock.verify();
    });
});
