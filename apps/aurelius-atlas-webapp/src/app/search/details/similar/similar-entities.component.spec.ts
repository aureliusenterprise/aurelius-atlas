import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentRef } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { API_BASE_URL, AtlasQuickSearchResult } from "aurelius-atlas-data-access";

import { SimilarEntities } from "./similar-entities.component";

/** The box's request for an entity (SBW-01, SBM-05). */
const similarUrl = (guid: string) => `/api/aurelius/v1/entity/guid/${guid}/similar`;

/** An answer of ``count`` neighbours, named ``n0`` … (SBM-05). */
function neighbours(count: number): AtlasQuickSearchResult {
    return {
        searchResults: {
            queryType: "BASIC",
            approximateCount: count,
            entities: Array.from({ length: count }, (_, i) => ({
                guid: `n${i}`,
                typeName: "m4i_data_entity",
                displayText: `n${i}`,
            })),
        },
        aggregationMetrics: {},
    };
}

function setup(guid = "g-1") {
    TestBed.configureTestingModule({
        imports: [SimilarEntities],
        providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: "/api" }],
    });
    const fixture: ComponentFixture<SimilarEntities> = TestBed.createComponent(SimilarEntities);
    const ref: ComponentRef<SimilarEntities> = fixture.componentRef;
    ref.setInput("guid", guid);
    fixture.detectChanges();
    return { fixture, ref, httpMock: TestBed.inject(HttpTestingController) };
}

const box = (fixture: ComponentFixture<SimilarEntities>) =>
    (fixture.nativeElement as HTMLElement).querySelector("section#similar-entities");

describe("SimilarEntities (SBW-07)", () => {
    it("asks for six neighbours and shows a spinner meanwhile", () => {
        const { fixture, httpMock } = setup();

        const request = httpMock.expectOne((candidate) => candidate.url === similarUrl("g-1"));
        expect(request.request.params.get("limit")).toBe("6");
        expect(request.request.params.get("excludeDeletedEntities")).toBe("true");
        expect(box(fixture)?.querySelector("h4")?.textContent?.trim()).toBe("Similar entities");
        expect(box(fixture)?.querySelector("progress")).not.toBeNull();
        request.flush(neighbours(0));
        httpMock.verify();
    });

    it("renders the neighbours as entity cards that lead to their details", () => {
        const { fixture, httpMock } = setup();
        const clicked: string[] = [];
        fixture.componentInstance.entityClicked.subscribe((guid) => clicked.push(guid));

        httpMock.expectOne((candidate) => candidate.url === similarUrl("g-1")).flush(neighbours(3));
        fixture.detectChanges();
        const cards = box(fixture)?.querySelectorAll("aurelius-atlas-ui-entity-card") ?? [];
        // The card's title link is what emits its guid (UIC entity card).
        (cards[1].querySelector("a") as HTMLAnchorElement).click();

        expect(cards).toHaveLength(3);
        expect(box(fixture)?.querySelector("progress")).toBeNull();
        expect(clicked).toEqual(["n1"]);
        httpMock.verify();
    });

    it.each([
        [409, "AURELIUS-409-00-001", "not analysed yet"],
        [500, "ATLAS-500-00-001", "could not be loaded"],
    ])("a %s answer shows its note", (status, errorCode, note) => {
        const { fixture, httpMock } = setup();

        httpMock
            .expectOne((candidate) => candidate.url === similarUrl("g-1"))
            .flush({ errorCode }, { status, statusText: "Refused" });
        fixture.detectChanges();

        expect(box(fixture)?.querySelector(".aurelius-similar-note")?.textContent).toContain(note);
        httpMock.verify();
    });

    it("no neighbour shows the none note", () => {
        const { fixture, httpMock } = setup();

        httpMock.expectOne((candidate) => candidate.url === similarUrl("g-1")).flush(neighbours(0));
        fixture.detectChanges();

        expect(box(fixture)?.querySelector(".aurelius-similar-note")?.textContent).toContain("No similar entities");
        httpMock.verify();
    });

    it("a server without search by meaning renders no box at all", () => {
        const { fixture, httpMock } = setup();

        httpMock
            .expectOne((candidate) => candidate.url === similarUrl("g-1"))
            .flush({ errorCode: "AURELIUS-404-00-001" }, { status: 404, statusText: "Not Found" });
        fixture.detectChanges();

        expect(box(fixture)).toBeNull();
        httpMock.verify();
    });

    it("another entity cancels the fetch in flight and asks for its own", () => {
        const { fixture, ref, httpMock } = setup();
        const first = httpMock.expectOne((candidate) => candidate.url === similarUrl("g-1"));

        ref.setInput("guid", "g-2");
        fixture.detectChanges();

        expect(first.cancelled).toBe(true);
        httpMock.expectOne((candidate) => candidate.url === similarUrl("g-2")).flush(neighbours(1));
        httpMock.verify();
    });
});
