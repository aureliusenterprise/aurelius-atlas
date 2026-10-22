import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from "@angular/router";
import { By } from "@angular/platform-browser";
import { of } from "rxjs";

import { Breadcrumbs } from "aurelius-atlas-ui";

import { Details } from "./details.component";

/**
 * The details skeleton (DET-01..06, DD-096): it renders the legacy
 * default-details anatomy in its empty state — no entity answers (server
 * 2.3 is planned), so every slot is empty, the title rides its localized
 * fallback, and the screen issues no request. The specs are the skeleton's
 * contract with the wiring increment: same shape, bound to the entity read.
 */
function setup(guid = "7a1b") {
    TestBed.configureTestingModule({
        imports: [Details],
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            provideRouter([]),
            { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ guid })) } },
        ],
    });
}

function render() {
    const fixture = TestBed.createComponent(Details);
    fixture.detectChanges();
    return { fixture, compiled: fixture.nativeElement as HTMLElement };
}

const normalize = (text: string | undefined | null) => text?.replace(/\s+/g, " ").trim();

describe("Details skeleton (DET-01, DET-02, DET-04, DET-05, DET-06)", () => {
    it("creates (DET-01)", () => {
        setup();
        expect(TestBed.createComponent(Details).componentInstance).toBeTruthy();
    });

    it("renders the skeleton anatomy: header, description, properties, side navigation (DET-01)", () => {
        setup();
        const { compiled } = render();

        const container = compiled.querySelector("section.section > .container.aurelius-details");
        expect(container).toBeTruthy();
        expect(container?.querySelector(".aurelius-details-header h1.entity.title")).toBeTruthy();
        expect(container?.querySelector(".aurelius-details-header .subtitle.name")).toBeTruthy();
        expect(container?.querySelector(".aurelius-details-trail")).toBeTruthy(); // the breadcrumbs host
        expect(container?.querySelector("#description-details .title.is-3")).toBeTruthy();
        expect(container?.querySelector("#properties-details")).toBeTruthy(); // the accordion
        expect(container?.querySelector(".aurelius-details-nav")).toBeTruthy();
        // The legacy scroll targets the side navigation links to.
        expect(container?.querySelectorAll('a[href="#properties-details"]').length).toBeGreaterThanOrEqual(2);
    });

    it("renders the empty state, not fake state (DET-02, DD-096)", () => {
        setup();
        const { compiled } = render();

        // The title falls back to the localized type label; the trail is
        // absent (the breadcrumbs' empty guard); the type-name line is
        // empty; the description is empty; the properties table holds
        // zero rows, and the count reads 0. No placeholder entity, no
        // loading state, no mock.
        expect(normalize(compiled.querySelector("h1.aurelius-details-title")?.textContent)).toBe("Entity type");
        expect(compiled.querySelector("nav.breadcrumb")).toBeNull();
        expect(normalize(compiled.querySelector(".aurelius-details-type")?.textContent)).toBe("");
        expect(normalize(compiled.querySelector(".aurelius-details-description")?.textContent)).toBe("");
        expect(compiled.querySelectorAll(".aurelius-details-properties tbody tr")).toHaveLength(0);
        expect(normalize(compiled.querySelector(".aurelius-details-property-count")?.textContent)).toBe("0");
    });

    it("renders the chrome from the bridge keys, in English (DET-04, SHL-08)", () => {
        setup();
        const { compiled } = render();

        // The i18n marker renders the catalogue's English text: the
        // search.details.* keys the Aurelius bridge carries.
        const titles = [...compiled.querySelectorAll("#description-details .title.is-3")].map((t) =>
            normalize(t.textContent),
        );
        expect(titles).toEqual(["Description"]);
        expect(normalize(compiled.querySelector(".aurelius-details-nav .menu-label")?.textContent)).toBe("Details");
        const headers = [...compiled.querySelectorAll(".aurelius-details-properties thead th")].map((th) =>
            normalize(th.textContent),
        );
        expect(headers).toEqual(["Key", "Value"]);
        expect(normalize(compiled.querySelector(".level .heading a")?.textContent)).toBe("Properties");
    });

    it("navigates the details route on a crumb click (DET-06, DD-066's sibling)", () => {
        setup();
        const { fixture } = render();
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        // The skeleton's trail is empty (DET-02), so the wiring is
        // proven at the component boundary: the lib's emit reaches the
        // screen's router call — the screen routes, the lib never does.
        const crumbs = fixture.debugElement.query(By.directive(Breadcrumbs)).componentInstance as Breadcrumbs;
        crumbs.itemClicked.emit("g2");

        expect(navigate).toHaveBeenCalledWith(["/search/details", "g2"]);
    });

    it("issues no HTTP requests: the skeleton exists before its API (DET-02, DET-03)", () => {
        setup();
        render();

        // The client method (DET-03) exists in the lib; no screen calls
        // it until the 2.3 wiring increment.
        expect(TestBed.inject(HttpTestingController).match(() => true)).toHaveLength(0);
    });

    it("keeps the guid from the route as the screen's address (DET-01, DET-07)", () => {
        setup("guid-from-route");
        const { fixture } = render();

        // The guid's observable surface: the trail's activeGuid binding
        // (the skeleton's only consumer of the address, DET-02).
        const crumbs = fixture.debugElement.query(By.directive(Breadcrumbs)).componentInstance as Breadcrumbs;
        expect(crumbs.activeGuid()).toBe("guid-from-route");
    });
});
