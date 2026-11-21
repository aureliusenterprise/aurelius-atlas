import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";

import { actionLabel, EntityHistory, HISTORY_PAGE } from "./entity-history.component";

/**
 * The editor page's History tab (EDP-20 to EDP-22): the entity audit answer
 * read in pages of 100, newest first, until a page comes back short; each event
 * its translated action, its user and its time; a failed read an empty list.
 */

const AUDIT = "/api/atlas/v2/entity/g-1/audit";

function setup() {
    TestBed.configureTestingModule({
        imports: [EntityHistory],
        providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(EntityHistory);
    fixture.componentRef.setInput("guid", "g-1");
    fixture.detectChanges();
    return { fixture, http: TestBed.inject(HttpTestingController) };
}

function event(action: string, user: string, timestamp: number) {
    return { entityId: "g-1", action, user, timestamp };
}

async function settle(fixture: ReturnType<typeof setup>["fixture"]) {
    await fixture.whenStable();
    fixture.detectChanges();
}

describe("EntityHistory (EDP-20 to EDP-22)", () => {
    it("EDP-20: reads the audit newest first, a page of 100 at a time, until a short page", async () => {
        const { fixture, http } = setup();

        const first = http.expectOne((request) => request.url.endsWith(AUDIT) && request.params.get("offset") === "0");
        expect(first.request.params.get("count")).toBe(String(HISTORY_PAGE));
        expect(first.request.params.get("sortOrder")).toBe("DESC");
        first.flush(Array.from({ length: HISTORY_PAGE }, (_, i) => event("ENTITY_UPDATE", "ann", 1_000 - i)));
        await settle(fixture);

        http.expectOne((request) => request.params.get("offset") === String(HISTORY_PAGE)).flush([
            event("ENTITY_CREATE", "ann", 1),
        ]);
        await settle(fixture);

        const entries = fixture.nativeElement.querySelectorAll(".aurelius-editor-history-event");
        expect(entries.length).toBe(HISTORY_PAGE + 1);
        http.verify();
    });

    it("EDP-21: each entry is the translated action, the user and the time", async () => {
        const { fixture, http } = setup();

        http.expectOne((request) => request.url.endsWith(AUDIT)).flush([
            event("ENTITY_CREATE", "ann", Date.UTC(2026, 10, 21, 9, 5, 7)),
        ]);
        await settle(fixture);

        const entry = fixture.nativeElement.querySelector(".aurelius-editor-history-event") as HTMLElement;
        expect(entry.querySelector("h6")?.textContent?.trim()).toBe("Entity created");
        expect(entry.querySelector("small")?.textContent).toContain("ann");
        expect(entry.querySelector("small")?.textContent).toMatch(/2026-11-21 \d{2}:05:07/);
    });

    it("EDP-21: an action the dictionary has no label for shows as itself", () => {
        expect(actionLabel("ENTITY_UPDATE")).toBe("Entity updated");
        expect(actionLabel("CLASSIFICATION_UPDATE")).toBe("Classification updated");
        expect(actionLabel("SOMETHING_NEW")).toBe("SOMETHING_NEW");
        expect(actionLabel(undefined)).toBe("");
    });

    it("EDP-22: a failed read shows an empty list and throws nowhere", async () => {
        const { fixture, http } = setup();

        http.expectOne((request) => request.url.endsWith(AUDIT)).flush({}, { status: 500, statusText: "Error" });
        await settle(fixture);

        expect(fixture.nativeElement.querySelectorAll(".aurelius-editor-history-event").length).toBe(0);
    });
});
