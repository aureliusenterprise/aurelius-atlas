import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";
import Keycloak from "keycloak-js";
import { describe, expect, it } from "vitest";

import fixture from "../../../../../tests/fixtures/lineage-graph.extract.json";
import { APP_CONFIG } from "../../../tokens";

import { LineageModel } from "./lineage-model.component";
import { LineageModelState } from "./lineage-state";

/**
 * The Lineage Model box (LDG-09/LDG-10, DD-392): the three states of the
 * LDG-01 call — pending, empty, diagram — and the failure state's single
 * fallback to the empty message. The diagram itself is the viewer's own
 * spec; here the box only hands it the parsed model and the page's guid.
 * The answer body is the vendored 8.2 chain fixture (DD-391), the same
 * bytes the aux route answers in the 8.2 scenarios.
 */
/**
 * The LDG-01 call: the aux route's root with the always-sent query (the
 * client's own spec pins the full parameter set; here the guid identifies
 * the request).
 */
const lineageCall = (guid: string) => (req: { url: string; params: { get(key: string): string | null } }) =>
    req.url === "/lineage-model/" && req.params.get("guid") === guid;

/** The 8.2 chain's answer for the fixture graph: `{ model, metadata }`. */
const MODEL_ANSWER = { model: fixture.model, metadata: [] };

function setup(guid = "ds-1"): {
    fixture: ComponentFixture<LineageModel>;
    compiled: HTMLElement;
    httpMock: HttpTestingController;
} {
    TestBed.configureTestingModule({
        imports: [LineageModel],
        // DD-400: the fetch state is the page's; mounted alone here, the
        // box gets its own instance — the page's provider is the Details
        // spec's (the stat reads the same one). The diagram state mounts
        // the viewer, whose save flow injects the session and the config.
        providers: [
            provideHttpClient(),
            provideHttpClientTesting(),
            LineageModelState,
            { provide: Keycloak, useValue: { tokenParsed: {} } },
            { provide: APP_CONFIG, useValue: { appName: "Aurelius Atlas", appVersion: "0.0.0" } },
        ],
    });
    const fixture = TestBed.createComponent(LineageModel);
    fixture.componentRef.setInput("guid", guid);
    fixture.detectChanges(); // the guid effect fires the LDG-01 call
    return { fixture, compiled: fixture.nativeElement as HTMLElement, httpMock: TestBed.inject(HttpTestingController) };
}

describe("LineageModel box (LDG-09/LDG-10, DD-392)", () => {
    it("LDG-10: the box asks for the model and waits with the loading message", () => {
        const { compiled, httpMock } = setup("ds-1");

        // LDG-01's call: the aux route's root with the guid (the client's
        // own spec pins the full parameter set).
        const request = httpMock.expectOne(lineageCall("ds-1"));
        expect(request.request.method).toBe("GET");

        expect(compiled.querySelector(".aurelius-lineage-loading")).toBeTruthy();
        expect(compiled.querySelector(".aurelius-lineage-empty")).toBeNull();
        expect(compiled.querySelector("aurelius-atlas-webapp-lineage-viewer")).toBeNull();

        request.flush(null, { status: 204, statusText: "No Content" });
    });

    it("LDG-10: the 204 (no lineage) shows the empty message", () => {
        const { fixture, compiled, httpMock } = setup();

        httpMock.expectOne(lineageCall("ds-1")).flush(null, { status: 204, statusText: "No Content" });
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-lineage-empty")).toBeTruthy();
        expect(compiled.querySelector(".aurelius-lineage-loading")).toBeNull();
        expect(compiled.querySelector("aurelius-atlas-webapp-lineage-viewer")).toBeNull();
    });

    it("LDG-10, DD-392: a failed call shows the empty message too", () => {
        const { fixture, compiled, httpMock } = setup();

        // The box's single fallback (the legacy's catch): the 502 reads like
        // the 204; the drawer carries the failure (the widened 7.19 chain).
        httpMock.expectOne(lineageCall("ds-1")).flush({}, { status: 502, statusText: "Bad Gateway" });
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-lineage-empty")).toBeTruthy();
        expect(compiled.querySelector(".aurelius-lineage-loading")).toBeNull();
    });

    it("LDG-11: a model that fails to parse reads as the empty state", () => {
        const { fixture, compiled, httpMock } = setup();

        // A producer that broke DV-68's contract: the reader throws (LDG-11)
        // and the box rests at the same message (DD-392's posture).
        httpMock.expectOne(lineageCall("ds-1")).flush({ model: '{"not_ar3": true}', metadata: [] });
        fixture.detectChanges();

        expect(compiled.querySelector(".aurelius-lineage-empty")).toBeTruthy();
        expect(compiled.querySelector("aurelius-atlas-webapp-lineage-viewer")).toBeNull();
    });

    it("LDG-09: a model draws the viewer under the drawn view's name", () => {
        const { fixture, compiled, httpMock } = setup("00000000-0000-4000-8000-000000000001");

        httpMock.expectOne(lineageCall("00000000-0000-4000-8000-000000000001")).flush(MODEL_ANSWER);
        fixture.detectChanges();
        fixture.detectChanges(); // the viewer's zoom effect

        // LDG-09's header: the drawn view's own name — the server's rule
        // names the view "Lineage" (the model's data, not a catalogue key).
        expect(compiled.querySelector(".aurelius-lineage-title")?.textContent?.trim()).toBe("Lineage");

        // The viewer draws the fixture's three nodes.
        expect(compiled.querySelectorAll("aurelius-atlas-webapp-lineage-viewer g.node")).toHaveLength(3);

        // LDG-18 through the box: the page's guid rides the viewer's input,
        // and the opened entity's node carries the highlight.
        const highlighted = compiled.querySelectorAll("g.node.is-highlighted");
        expect(highlighted).toHaveLength(1);
        expect(highlighted[0].classList.contains("dataset")).toBe(true);

        expect(compiled.querySelector(".aurelius-lineage-empty")).toBeNull();
    });

    it("LDG-27/DD-415: the header's Browse routes the quickview open", () => {
        const { fixture, compiled, httpMock } = setup("00000000-0000-4000-8000-000000000001");

        httpMock.expectOne(lineageCall("00000000-0000-4000-8000-000000000001")).flush(MODEL_ANSWER);
        fixture.detectChanges();
        fixture.detectChanges();

        // The legacy's level-right: label plus search icon (LDG-27).
        const browse = compiled.querySelector<HTMLButtonElement>(".aurelius-lineage-browse");
        expect(browse?.textContent?.trim()).toBe("Browse the model");
        expect(browse?.querySelector("span.icon fa-icon")).toBeTruthy();

        // DD-415: the click reaches the quickview through the outlet route —
        // the panel is no longer the viewer's child, so the seam is the URL.
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        browse?.click();
        expect(navigate).toHaveBeenCalledWith([{ outlets: { drawer: ["lineage", "browse"] } }]);
    });
});
