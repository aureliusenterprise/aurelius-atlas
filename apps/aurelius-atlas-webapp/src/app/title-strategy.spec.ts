import { TestBed } from "@angular/core/testing";
import type { ActivatedRouteSnapshot, RouterStateSnapshot } from "@angular/router";

import type { AppConfig } from "./config";
import { APP_CONFIG } from "./tokens";
import { AtlasTitleStrategy } from "./title-strategy";

const config: AppConfig = {
    keycloak: { clientId: "aurelius", realm: "atlas", url: "https://keycloak.example/" },
    apiBaseUrl: "/api",
    otelExporterUrl: "/otel/v1/traces",
    appName: "Aurelius Atlas Data Governance",
    appCopyright: 2022,
    appVersion: "7.11.0#abc1234",
};

/**
 * A router snapshot by route shape only (TITLE-001): the strategy reads
 * `data.title`, `outlet`, and `firstChild` and nothing else, so the fake
 * carries exactly those.
 * @param shape the route's title, outlet, and child
 * @returns the snapshot to walk
 */
function route({
    title,
    outlet = "primary",
    child,
}: {
    title?: string;
    outlet?: string;
    child?: ActivatedRouteSnapshot;
} = {}): ActivatedRouteSnapshot {
    return {
        data: title === undefined ? {} : { title },
        outlet,
        firstChild: child ?? null,
    } as unknown as ActivatedRouteSnapshot;
}

function state(root: ActivatedRouteSnapshot): RouterStateSnapshot {
    return { root } as unknown as RouterStateSnapshot;
}

describe("AtlasTitleStrategy (TITLE-001, WCAG 2.4.2)", () => {
    beforeEach(() => {
        TestBed.configureTestingModule({ providers: [{ provide: APP_CONFIG, useValue: config }] });
    });

    function apply(root: ActivatedRouteSnapshot): string {
        TestBed.inject(AtlasTitleStrategy).updateTitle(state(root));
        return document.title;
    }

    it("TITLE-001: the deepest primary route's title joins the app name", () => {
        expect(apply(route({ child: route({ child: route({ title: "Lineage" }) }) }))).toBe(
            "Lineage - Aurelius Atlas Data Governance",
        );
    });

    it("TITLE-001: a shallower title survives when the deepest route carries none", () => {
        // The walk returns the child's title first; the ?? keeps the
        // parent's when the chain ends unnamed (search subtree: the layout
        // names nothing, the routed screen does).
        expect(apply(route({ title: "Search", child: route({}) }))).toBe("Search - Aurelius Atlas Data Governance");
    });

    it("TITLE-001: the deepest title wins over its ancestors'", () => {
        expect(apply(route({ title: "Search", child: route({ title: "Results" }) }))).toBe(
            "Results - Aurelius Atlas Data Governance",
        );
    });

    it("TITLE-001: a route with no title falls back to the bare app name", () => {
        // The guarded root before its redirect settles (the string
        // index.html ships).
        expect(apply(route({}))).toBe("Aurelius Atlas Data Governance");
    });

    it("TITLE-001: only the primary outlet names the page (an open drawer stays quiet)", () => {
        // The settings panel route (drawer outlet) carries no title, and a
        // titled aux route must not rename the tab either.
        expect(apply(route({ child: route({ title: "Settings", outlet: "drawer" }) }))).toBe(
            "Aurelius Atlas Data Governance",
        );
        expect(apply(route({ title: "Details", child: route({ title: "Panel", outlet: "drawer" }) }))).toBe(
            "Details - Aurelius Atlas Data Governance",
        );
    });
});
