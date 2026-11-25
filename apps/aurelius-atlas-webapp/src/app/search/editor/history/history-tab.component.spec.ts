/**
 * The entity editor's History pane (HST-01..HST-16, DD-816..DD-825): the
 * audit trail the drawer lists beside the form (AUD-04, AUD-06..AUD-08) — the
 * tab pair (HST-01, HST-02), the trail read and its pages (HST-03, HST-08),
 * the change lists (HST-10, HST-12, HST-14), the description diff (HST-15,
 * HST-16), and the single-attribute restore (HST-11, DD-822). The pane moved
 * out of the drawer at 7.46 (DD-872): it renders the `AuditTrail` store the
 * drawer provides, and the drawer keeps the restore's write (WFE-02) and the
 * crumb's navigation. The shared fixtures ride `../editor-testing`; the read
 * itself (AUD-08) is specced at the data-access layer.
 */
import { HttpRequest } from "@angular/common/http";
import { HttpTestingController } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { Router } from "@angular/router";

import { type EntityAuditEventV2 } from "aurelius-atlas-data-access";

import { AlertsService } from "../../../alerts/alerts.service";

import { EntityEditor } from "../entity-editor.component";
import { ATLAS_ENTITY_URL, VIEW_URL } from "../../../../testing/api";
import { normalize } from "../../../../testing/dom";
import {
    ANSWER,
    AUDIT_BASE,
    AUDIT_EVENTS,
    AUDIT_URL,
    arrive,
    arriveTypeDefs,
    auditPage,
    auditPageRequest,
    openEntityTab,
    openHistoryTab,
    savedView,
    setup,
} from "../editor-testing";

describe("EntityEditor history tab (HST-01..HST-09)", () => {
    it("the edit drawer carries the Entity/History tab pair, create does not (HST-01)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        // The pair sits in the drawer's subhead slot (DD-180), so a long form
        // cannot scroll it away (HST-01).
        const tabs = compiled.querySelector<HTMLElement>("nav[drawer-subhead].tabs")!;
        expect(tabs.getAttribute("role")).toBe("tablist");
        expect(
            [...tabs.querySelectorAll<HTMLButtonElement>("button[role='tab']")].map((tab) =>
                normalize(tab.textContent),
            ),
        ).toEqual(["Entity", "History"]);
        httpMock.verify();
    });

    it("create mode renders the form alone, with no tab pair (HST-01)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true });
        arriveTypeDefs(fixture, httpMock);

        expect(compiled.querySelector("nav[drawer-subhead]")).toBeNull();
        expect(compiled.querySelector("#editor-entity-tab")).toBeNull();
        expect(compiled.querySelector("#editor-history-tab")).toBeNull();
        expect(compiled.querySelector("button.aurelius-editor-save")).toBeTruthy();
        httpMock.verify();
    });

    it("the tab pair is one tablist with the roving tabindex and the aria pair (HST-02)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const entityTab = compiled.querySelector<HTMLButtonElement>("#editor-entity-tab")!;
        const historyTab = compiled.querySelector<HTMLButtonElement>("#editor-history-tab")!;

        // The drawer opens on the form: Entity is the active tab (UIC-26).
        expect(entityTab.getAttribute("aria-selected")).toBe("true");
        expect(entityTab.tabIndex).toBe(0);
        expect(historyTab.getAttribute("aria-selected")).toBe("false");
        expect(historyTab.tabIndex).toBe(-1);
        // Each tab names its pane and each pane names its tab (UIC-26).
        expect(entityTab.getAttribute("aria-controls")).toBe("editor-entity-pane");
        expect(compiled.querySelector("#editor-entity-pane")?.getAttribute("aria-labelledby")).toBe(
            "editor-entity-tab",
        );
        expect(historyTab.getAttribute("aria-controls")).toBe("editor-history-pane");
        expect(compiled.querySelector("#editor-history-pane")?.getAttribute("aria-labelledby")).toBe(
            "editor-history-tab",
        );
        httpMock.expectNone(AUDIT_URL); // the trail is read only on the tab (HST-03)
    });

    it("the arrow keys move the active tab and carry focus with it (HST-02)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        // The keys walk the active tab (the markdown field's pattern), so the
        // drawer starts on Entity: Right moves to History, Left back.
        compiled
            .querySelector<HTMLButtonElement>("#editor-entity-tab")!
            .dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, cancelable: true }));
        fixture.detectChanges();

        expect(document.activeElement).toBe(compiled.querySelector("#editor-history-tab"));
        expect(compiled.querySelector("#editor-history-tab")?.closest("li")?.classList.contains("is-active")).toBe(
            true,
        );
        httpMock.expectOne(AUDIT_URL).flush(AUDIT_EVENTS);
        fixture.detectChanges();

        // Left from History moves to Entity (UIC-26).
        compiled
            .querySelector<HTMLButtonElement>("#editor-history-tab")!
            .dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true, cancelable: true }));
        fixture.detectChanges();

        expect(document.activeElement).toBe(compiled.querySelector("#editor-entity-tab"));
        expect(compiled.querySelector<HTMLButtonElement>("#editor-entity-tab")?.getAttribute("aria-selected")).toBe(
            "true",
        );
    });

    it("switching to History fires one audit read of the newest page and lists the rows newest first (HST-03, HST-04)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);

        // One GET with the page size and no cursor (HST-03 as amended by
        // 7.36): the endpoint answers its newest 100 events newest-first
        // (AUD-08). An `offset` or `sortBy` would move it onto its sorted,
        // oldest-first path (AUD-07), so neither travels.
        const request = httpMock.expectOne(AUDIT_URL);
        expect(request.request.method).toBe("GET");
        expect(request.request.params.keys()).toEqual(["count"]);
        request.flush(AUDIT_EVENTS);
        fixture.detectChanges();

        const rows = [...compiled.querySelectorAll<HTMLElement>(".aurelius-editor-audit")];
        expect(rows.map((row) => normalize(row.querySelector(".title")?.textContent))).toEqual([
            "Entity updated",
            "Entity created",
        ]);
        // The meta line is the legacy's anatomy: the user, the separator, the time.
        const meta = normalize(rows[0]?.querySelector("small")?.textContent);
        expect(meta).toContain("analyst-3");
        expect(rows[0]?.querySelector("time")?.getAttribute("datetime")).toBe("1700000021000");
        expect(normalize(rows[0]?.querySelector("time")?.textContent)).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    });

    it("the audit read is repeated per visit and never stacks while in flight (HST-03)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        const first = httpMock.expectOne(AUDIT_URL);

        // A second switch while the read runs does not ask again (HST-03).
        compiled.querySelector<HTMLButtonElement>("#editor-history-tab")!.click();
        fixture.detectChanges();
        httpMock.expectNone(AUDIT_URL);

        first.flush(AUDIT_EVENTS);
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(2);

        // Coming back re-reads: no caching rule applies to the trail.
        openEntityTab(compiled, fixture);
        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(AUDIT_EVENTS);
        fixture.detectChanges();
        httpMock.verify();
    });

    it("the sentinel's ask reads the older page from the oldest key and appends it without the repeat (HST-08)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        // A full first page (the count the pane asks for): the trail may have
        // more, so the container shows its sentinel (UIC-21).
        const firstPage = auditPage(1_700_000_100_000, 100);
        httpMock.expectOne(AUDIT_URL).flush(firstPage);
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(100);

        // jsdom has no IntersectionObserver, so the sentinel's load button is
        // the trigger (UIC-22).
        compiled
            .querySelector<HTMLButtonElement>(
                "#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button",
            )!
            .click();
        fixture.detectChanges();

        // The cursor is the oldest listed eventKey, inclusive (AUD-08): the
        // answer repeats it, and the pane drops the repeat (HST-08).
        const oldest = firstPage.at(-1)!.eventKey!;
        const page2 = httpMock.expectOne(auditPageRequest(oldest));
        // A short page is the entity's oldest one (HST-08): the rows grow by
        // the three new events only, the sentinel is gone, and nothing older
        // is asked for.
        page2.flush([firstPage.at(-1)!, ...auditPage(1_700_000_100_000 - 100, 3)]);
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(103);
        expect(
            compiled.querySelector("#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button"),
        ).toBeNull();
        httpMock.verify();
    });

    it("a full last page keeps the sentinel shown and a scroll during a page asks nothing (HST-08)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(auditPage(1_700_000_100_000, 100));
        fixture.detectChanges();

        compiled
            .querySelector<HTMLButtonElement>(
                "#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button",
            )!
            .click();
        fixture.detectChanges();
        const page2 = httpMock.expectOne(auditPageRequest("1700000099901:0"));

        // One page in flight: the container suppresses its triggers and the
        // component guards again, so a fast scroll stacks no reads (HST-08).
        compiled
            .querySelector<HTMLButtonElement>(
                "#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button",
            )!
            .click();
        fixture.detectChanges();
        httpMock.expectNone(auditPageRequest("1700000099901:0"));

        // Exactly the count answers: the pane cannot know the trail ended, so
        // the sentinel stays (DD-820's one dead ask).
        page2.flush(auditPage(1_700_000_100_000 - 100, 100));
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(200);
        expect(
            compiled.querySelector("#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button"),
        ).toBeTruthy();
    });

    it("a next page keeps the rows while it runs and a failed one leaves the rows and the sentinel (HST-05, HST-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(auditPage(1_700_000_100_000, 100));
        fixture.detectChanges();

        compiled
            .querySelector<HTMLButtonElement>(
                "#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button",
            )!
            .click();
        fixture.detectChanges();

        // A next page does not clear the list (HST-05 as amended by 7.36):
        // the rows stay and the container's spinner carries the flight — the
        // pane's own line speaks for the first read only.
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(100);
        expect(normalize(compiled.querySelector("#editor-history-pane .aurelius-editor-loading")?.textContent)).toBe(
            "",
        );

        httpMock.expectOne(auditPageRequest("1700000099901:0")).flush({}, { status: 500, statusText: "Server Error" });
        fixture.detectChanges();

        const alerts = TestBed.inject(AlertsService);
        expect(alerts.hasAlerts()).toBe(true);
        // The rows stay and the sentinel stays, so the ask can be made again
        // (HST-06 as amended by 7.36).
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(100);
        expect(
            compiled.querySelector("#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button"),
        ).toBeTruthy();
        compiled
            .querySelector<HTMLButtonElement>(
                "#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button",
            )!
            .click();
        fixture.detectChanges();
        httpMock.expectOne(auditPageRequest("1700000099901:0")).flush([AUDIT_EVENTS[1]]);
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(101);
    });

    it("the History pane shows the loading line while the read runs (HST-05)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        fixture.detectChanges();

        // The persistent region (LR-002): the history pane's loading line
        // carries the vendored audit-retrieve string while in flight.
        const line = compiled.querySelector("#editor-history-pane .aurelius-editor-loading");
        expect(normalize(line?.textContent)).toBe("Retrieving the audit log");

        httpMock.expectOne(AUDIT_URL).flush([]);
        fixture.detectChanges();

        expect(normalize(compiled.querySelector("#editor-history-pane .aurelius-editor-loading")?.textContent)).toBe(
            "",
        );
        // An answered read with no events shows no rows (HST-05's aged case).
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(0);
    });

    it("a re-read shows no rows while it runs, so the line never sits above stale ones (HST-05)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(AUDIT_EVENTS);
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(2);

        // Every visit re-reads (HST-03), and a re-read starts from an empty
        // list: the loading line alone, not the previous answer under it.
        openEntityTab(compiled, fixture);
        openHistoryTab(compiled, fixture);
        fixture.detectChanges();

        expect(normalize(compiled.querySelector("#editor-history-pane .aurelius-editor-loading")?.textContent)).toBe(
            "Retrieving the audit log",
        );
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(0);

        httpMock.expectOne(AUDIT_URL).flush(AUDIT_EVENTS);
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(2);
    });

    it("a failed re-read leaves the list empty rather than the stale rows (HST-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(AUDIT_EVENTS);
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(2);

        openEntityTab(compiled, fixture);
        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush({}, { status: 500, statusText: "Server Error" });
        fixture.detectChanges();

        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(0);
        expect(TestBed.inject(AlertsService).hasAlerts()).toBe(true);
    });

    it("a failed first read leaves the sentinel, whose ask retries the newest page (HST-06, HST-08)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush({}, { status: 500, statusText: "Server Error" });
        fixture.detectChanges();

        // Nothing is listed, so there is no cursor: the trail is not ended and
        // the sentinel stays (HST-06 as amended by 7.36).
        const sentinel = compiled.querySelector<HTMLButtonElement>(
            "#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button",
        );
        expect(sentinel).toBeTruthy();

        // Its ask reads the newest page again — the same read the switch made,
        // not a cursor page (HST-08).
        sentinel!.click();
        fixture.detectChanges();
        const retry = httpMock.expectOne(AUDIT_URL);
        expect(retry.request.params.get("startKey")).toBeNull();
        retry.flush(AUDIT_EVENTS);
        fixture.detectChanges();
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(2);
    });

    it("a page in flight stacks no read, a tab switch among them (HST-09)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(auditPage(1_700_000_100_000, 100));
        fixture.detectChanges();

        compiled
            .querySelector<HTMLButtonElement>(
                "#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button",
            )!
            .click();
        fixture.detectChanges();
        httpMock.expectOne(auditPageRequest("1700000099901:0"));

        // A switch to the form and back while that page runs asks nothing: the
        // in-flight guard covers the scroll's read too (HST-09).
        openEntityTab(compiled, fixture);
        openHistoryTab(compiled, fixture);
        fixture.detectChanges();
        httpMock.expectNone(AUDIT_BASE);
    });

    it("a failed first read adds one alert, leaves the list empty and keeps the drawer (HST-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush({}, { status: 500, statusText: "Server Error" });
        fixture.detectChanges();

        const alerts = TestBed.inject(AlertsService);
        expect(alerts.hasAlerts()).toBe(true);
        expect(alerts.alerts()[0]?.message).toBe("Retrieving the audit log");
        expect(alerts.alerts()[0]?.severity).toBe("error");
        expect(compiled.querySelectorAll(".aurelius-editor-audit").length).toBe(0);
        // The drawer stays open (EDT-08's posture).
        expect(fixture.nativeElement.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
    });

    it("the foot holds Save and Delete on the Entity tab and hides on History (HST-07)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        expect(compiled.querySelector(".aurelius-editor-foot")).toBeTruthy();

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(AUDIT_EVENTS);
        fixture.detectChanges();

        // The foot holds nothing in History, which hides it (the drawer's
        // empty-foot rule, HST-07 — the legacy's footer rule).
        expect(compiled.querySelector(".aurelius-editor-foot")).toBeNull();
        expect(compiled.querySelector(".aurelius-drawer-foot")?.children.length).toBe(0);
        // The form stayed mounted behind the hidden pane (HST-02, DD-352).
        expect(compiled.querySelector("#editor-entity-pane")?.hasAttribute("hidden")).toBe(true);
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("genomic_variants");

        openEntityTab(compiled, fixture);
        expect(compiled.querySelector(".aurelius-editor-foot")).toBeTruthy();
    });
});

/** The listener's own `details` prefix of each stored-state action (AUD-03):
 * the change list reads the body behind it (HST-10). */
const AUDIT_PREFIX: Record<string, string> = {
    ENTITY_CREATE: "Created: ",
    ENTITY_UPDATE: "Updated: ",
    ENTITY_IMPORT_CREATE: "Created by import: ",
    ENTITY_IMPORT_UPDATE: "Updated by import: ",
};

/**
 * An audit row whose `details` carry a stored entity, as the ported listener
 * writes them (AUD-03): the prefix and the entity's JSON.
 * @param action the stored-state action
 * @param key the row's eventKey, whose leading number is its timestamp
 * @param attributes the stored attribute map
 * @param relationshipAttributes the stored ends, keyed by attribute name
 */
function stateAuditEvent(
    action: EntityAuditEventV2["action"],
    key: string,
    attributes: Record<string, unknown>,
    relationshipAttributes: Record<string, unknown> = {},
): EntityAuditEventV2 {
    return {
        entityId: "7a1b",
        eventKey: key,
        timestamp: Number(key.slice(0, key.indexOf(":"))),
        user: "analyst-3",
        action,
        details: `${AUDIT_PREFIX[String(action)]}${JSON.stringify({
            typeName: "table",
            guid: "7a1b",
            attributes,
            relationshipAttributes,
        })}`,
    };
}

/** The trail of the change-detail tests: the update of the name, over the
 * create that first set it (newest first, HST-03). */
const CHANGED_TRAIL: EntityAuditEventV2[] = [
    stateAuditEvent("ENTITY_UPDATE", "1700000020000:0", { name: "second" }),
    stateAuditEvent("ENTITY_CREATE", "1700000010000:0", { name: "first" }),
];

/** The History rows of the pane, newest first as listed (HST-03). */
function auditRows(compiled: HTMLElement): HTMLElement[] {
    return [...compiled.querySelectorAll<HTMLElement>(".aurelius-editor-audit")];
}

/** The change toggle of a row (HST-10). */
function auditToggle(row: HTMLElement): HTMLButtonElement {
    return row.querySelector<HTMLButtonElement>("button.aurelius-editor-audit-toggle")!;
}

/** The open change list of a row (HST-10). */
function auditChangePane(row: HTMLElement): HTMLElement | null {
    return row.querySelector<HTMLElement>(".aurelius-editor-audit-changes");
}

describe("EntityEditor history change details (HST-10)", () => {
    it("a state row opens and closes its change list and its toggle names the state (HST-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(CHANGED_TRAIL);
        fixture.detectChanges();

        const row = auditRows(compiled)[0];
        const toggle = auditToggle(row);
        expect(normalize(toggle.textContent)).toBe("Changes");
        expect(toggle.getAttribute("aria-expanded")).toBe("false");
        expect(auditChangePane(row)).toBeNull();

        toggle.click();
        fixture.detectChanges();
        expect(toggle.getAttribute("aria-expanded")).toBe("true");
        // The open toggle names the list it controls and the list carries that
        // id — the accordion's pairing (FORM-CUSTOM-001).
        const paneId = toggle.getAttribute("aria-controls");
        expect(paneId).toBeTruthy();
        expect(auditChangePane(row)?.id).toBe(paneId);

        auditToggle(auditRows(compiled)[0]).click();
        fixture.detectChanges();
        expect(
            auditRows(compiled)[0].querySelector("button.aurelius-editor-audit-toggle")?.getAttribute("aria-expanded"),
        ).toBe("false");
        // A closed toggle names nothing (FORM-CUSTOM-001): the id would dangle.
        expect(
            auditRows(compiled)[0].querySelector("button.aurelius-editor-audit-toggle")?.getAttribute("aria-controls"),
        ).toBeNull();
        expect(auditChangePane(auditRows(compiled)[0])).toBeNull();
    });

    it("the open list shows the changed attribute with its old and new value (HST-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(CHANGED_TRAIL);
        fixture.detectChanges();
        auditToggle(auditRows(compiled)[0]).click();
        fixture.detectChanges();

        const pane = auditChangePane(auditRows(compiled)[0])!;
        expect(normalize(pane.textContent)).toContain("Attributes");
        const line = normalize(pane.querySelector("tbody tr")?.textContent);
        // The row words the attribute as the form words it (HST-14), and it is
        // still the attribute the trail changed.
        expect(line).toContain("Name");
        expect(pane.querySelector("del")?.textContent).toBe("first");
        expect(pane.querySelector("ins")?.textContent).toBe("second");
    });

    it("a create row lists everything it holds as added (HST-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(CHANGED_TRAIL);
        fixture.detectChanges();
        const create = auditRows(compiled)[1];
        auditToggle(create).click();
        fixture.detectChanges();

        const pane = auditChangePane(auditRows(compiled)[1])!;
        expect(normalize(pane.textContent)).toContain("Added");
        expect(normalize(pane.querySelector("tbody tr")?.textContent)).toContain("Name");
        expect(pane.querySelector("ins")).toBeNull();
    });

    it("a row whose write changed nothing says nothing changed (HST-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock
            .expectOne(AUDIT_URL)
            .flush([
                stateAuditEvent("ENTITY_UPDATE", "1700000020000:0", { name: "same" }),
                stateAuditEvent("ENTITY_UPDATE", "1700000010000:0", { name: "same" }),
            ]);
        fixture.detectChanges();
        auditToggle(auditRows(compiled)[0]).click();
        fixture.detectChanges();

        expect(normalize(auditChangePane(auditRows(compiled)[0])?.textContent)).toBe("Nothing changed");
    });

    it("a relationship added and one removed are listed by their end entity (HST-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock
            .expectOne(AUDIT_URL)
            .flush([
                stateAuditEvent(
                    "ENTITY_UPDATE",
                    "1700000020000:0",
                    {},
                    { input: [{ guid: "b", displayText: "beta" }] },
                ),
                stateAuditEvent(
                    "ENTITY_UPDATE",
                    "1700000010000:0",
                    {},
                    { input: [{ guid: "a", displayText: "alpha" }] },
                ),
            ]);
        fixture.detectChanges();
        auditToggle(auditRows(compiled)[0]).click();
        fixture.detectChanges();

        const pane = auditChangePane(auditRows(compiled)[0])!;
        const text = normalize(pane.textContent);
        expect(text).toContain("Relationships");
        expect(text).toContain("input");
        expect(text).toContain("beta");
        expect(text).toContain("alpha");
        expect(text).toContain("Added");
        expect(text).toContain("Removed");
    });

    it("only a state row carries a change toggle (HST-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush([
            {
                entityId: "7a1b",
                eventKey: "1700000030000:0",
                timestamp: 1_700_000_030_000,
                user: "analyst-3",
                action: "CLASSIFICATION_ADD",
                details: "Added classification: {}",
            },
            ...CHANGED_TRAIL,
            {
                entityId: "7a1b",
                eventKey: "1700000000000:0",
                timestamp: 1_700_000_000_000,
                user: "analyst-3",
                action: "ENTITY_DELETE",
                details: "Deleted entity",
            },
        ]);
        fixture.detectChanges();

        const rows = auditRows(compiled);
        expect(rows).toHaveLength(4);
        expect(rows[0].querySelector("button.aurelius-editor-audit-toggle")).toBeNull();
        expect(rows[3].querySelector("button.aurelius-editor-audit-toggle")).toBeNull();
        expect(rows[1].querySelector("button.aurelius-editor-audit-toggle")).toBeTruthy();
        expect(rows[2].querySelector("button.aurelius-editor-audit-toggle")).toBeTruthy();
    });

    it("a row whose body the server cut down says the details are not recorded (HST-10, AUD-04)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush([
            {
                entityId: "7a1b",
                eventKey: "1700000020000:0",
                timestamp: 1_700_000_020_000,
                user: "analyst-3",
                action: "ENTITY_UPDATE",
                details: 'Updated: {"typeName":"table","guid":"7a1b"}',
            },
        ]);
        fixture.detectChanges();
        auditToggle(auditRows(compiled)[0]).click();
        fixture.detectChanges();

        expect(normalize(auditChangePane(auditRows(compiled)[0])?.textContent)).toBe("The details are not recorded");
    });

    it("the newest row says the earlier state is not loaded, and a next page answers it (HST-10, HST-08)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        // A full first page whose only state row is the newest one: nothing
        // older on screen holds a state, so that row claims nothing (HST-10).
        const filler = Array.from({ length: 99 }, (_, index) => ({
            entityId: "7a1b",
            eventKey: `16999999${String(index).padStart(4, "0")}:0`,
            timestamp: 1_699_999_990_000 - index,
            user: "analyst-3",
            action: "CLASSIFICATION_ADD",
            details: "Added classification: {}",
        })) as EntityAuditEventV2[];
        const firstPage = [stateAuditEvent("ENTITY_UPDATE", "1700000100000:0", { name: "b" }), ...filler];
        httpMock.expectOne(AUDIT_URL).flush(firstPage);
        fixture.detectChanges();

        // The rows without a stored state keep the plain row of 7.35 (HST-04).
        expect(auditRows(compiled)).toHaveLength(100);
        expect(auditRows(compiled)[99].querySelector("button.aurelius-editor-audit-toggle")).toBeNull();

        const newest = auditRows(compiled)[0];
        auditToggle(newest).click();
        fixture.detectChanges();
        expect(normalize(auditChangePane(auditRows(compiled)[0])?.textContent)).toBe("The earlier state is not loaded");

        // Scrolling brings the page that holds the state this write replaced.
        compiled
            .querySelector<HTMLButtonElement>(
                "#editor-history-pane aurelius-atlas-ui-infinite-scroll-container > p button",
            )!
            .click();
        fixture.detectChanges();
        httpMock
            .expectOne(auditPageRequest(firstPage.at(-1)!.eventKey!))
            .flush([stateAuditEvent("ENTITY_CREATE", "1699999900000:0", { name: "a" })]);
        fixture.detectChanges();

        // The row is still open and answers itself now (HST-08's next page).
        expect(normalize(auditChangePane(auditRows(compiled)[0])?.textContent)).toContain("Attributes");
        expect(auditRows(compiled)[0].querySelector("del")?.textContent).toBe("a");
        expect(auditRows(compiled)[0].querySelector("ins")?.textContent).toBe("b");
    });

    it("two rows can be open at the same time (HST-10)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(CHANGED_TRAIL);
        fixture.detectChanges();
        auditToggle(auditRows(compiled)[0]).click();
        fixture.detectChanges();
        auditToggle(auditRows(compiled)[1]).click();
        fixture.detectChanges();

        expect(auditRows(compiled).filter((row) => auditChangePane(row) !== null)).toHaveLength(2);
        expect(
            auditRows(compiled)[0].querySelector("button.aurelius-editor-audit-toggle")?.getAttribute("aria-expanded"),
        ).toBe("true");
        expect(
            auditRows(compiled)[1].querySelector("button.aurelius-editor-audit-toggle")?.getAttribute("aria-expanded"),
        ).toBe("true");
    });

    it("opening a change list asks for nothing (HST-10, AUD-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        openHistoryTab(compiled, fixture);
        httpMock.expectOne(AUDIT_URL).flush(CHANGED_TRAIL);
        fixture.detectChanges();

        auditToggle(auditRows(compiled)[0]).click();
        fixture.detectChanges();
        auditToggle(auditRows(compiled)[1]).click();
        fixture.detectChanges();

        httpMock.expectNone(AUDIT_URL);
        httpMock.verify();
    });
});

/** The two change tables of an open change list, attributes first (HST-12).
 * Each is the shared sortable table component (UIC-05, DD-823), so the helper
 * finds its host elements rather than a table the drawer would own. */
function auditTables(pane: HTMLElement): HTMLElement[] {
    return [...pane.querySelectorAll<HTMLElement>("aurelius-atlas-ui-sortable-table")];
}

/** The header words of a table, in order (HST-12). */
function auditHeaders(table: HTMLElement): string[] {
    return [...table.querySelectorAll("thead th")].map((cell) => normalize(cell.textContent)!);
}

/** The trail of the table tests: one attribute change and two ends, one added
 * and one removed (HST-12). The added end carries a type, so its crumb can
 * show an icon (DET-26). */
const TABLE_TRAIL: EntityAuditEventV2[] = [
    stateAuditEvent(
        "ENTITY_UPDATE",
        "1700000020000:0",
        { name: "second" },
        { input: [{ guid: "b", typeName: "m4i_system", displayText: "beta" }] },
    ),
    stateAuditEvent(
        "ENTITY_UPDATE",
        "1700000010000:0",
        { name: "first" },
        { input: [{ guid: "a", typeName: "m4i_dataset", displayText: "alpha" }] },
    ),
];

/** Open the newest row's change list over a trail (HST-12). */
function openChangePane(
    compiled: HTMLElement,
    fixture: ComponentFixture<EntityEditor>,
    httpMock: HttpTestingController,
    trail: EntityAuditEventV2[] = TABLE_TRAIL,
): HTMLElement {
    openHistoryTab(compiled, fixture);
    httpMock.expectOne(AUDIT_URL).flush(trail);
    fixture.detectChanges();
    auditToggle(auditRows(compiled)[0]).click();
    fixture.detectChanges();

    return auditChangePane(auditRows(compiled)[0])!;
}

describe("EntityEditor history change tables (HST-12)", () => {
    it("an open change list is two tables, each with its own header row (HST-12)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock);
        const tables = auditTables(pane);

        expect(tables).toHaveLength(2);
        expect(auditHeaders(tables[0])).toEqual(["Action", "Name", "Value"]);
        expect(auditHeaders(tables[1])).toEqual(["Action", "Relationship", "Entity"]);
    });

    it("a section with no changes shows no table and no caption (HST-12)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        // The attributes of both states are equal, so only the relationship
        // table is there (HST-10's rule, now about tables).
        const pane = openChangePane(compiled, fixture, httpMock, [
            stateAuditEvent("ENTITY_UPDATE", "1700000020000:0", { name: "same" }, { input: [{ guid: "b" }] }),
            stateAuditEvent("ENTITY_UPDATE", "1700000010000:0", { name: "same" }, { input: [] }),
        ]);

        expect(auditTables(pane)).toHaveLength(1);
        expect(auditHeaders(auditTables(pane)[0])).toEqual(["Action", "Relationship", "Entity"]);
        expect(normalize(pane.textContent)).not.toContain("Attributes");
    });

    it("the attributes table names the action of each of its rows (HST-12)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock);
        const rows = [...auditTables(pane)[0].querySelectorAll("tbody tr")];

        expect(rows).toHaveLength(1);
        const cells = [...rows[0].querySelectorAll("td")];
        expect(normalize(cells[0]?.textContent)).toBe("Changed");
        // The attribute's own localized field label, not its wire name (HST-14).
        expect(normalize(cells[1]?.textContent)).toBe("Name");
        // The value cell keeps 7.37's marks (HST-12 moves them, it does not
        // change them), and the restore button of 7.38 sits in the same cell.
        expect(cells[2]?.querySelector("del")?.textContent).toBe("first");
        expect(cells[2]?.querySelector("ins")?.textContent).toBe("second");
        expect(cells[2]?.querySelector(".aurelius-editor-restore")).toBeTruthy();
    });

    it("the relationships table names each end's action, attribute and entity (HST-12)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock);
        const rows = [...auditTables(pane)[1].querySelectorAll("tbody tr")];

        expect(rows).toHaveLength(2);
        expect(normalize(rows[0].querySelector("td")?.textContent)).toBe("Added");
        expect(normalize(rows[0].querySelectorAll("td")[1]?.textContent)).toBe("input");
        expect(normalize(rows[0].querySelector("aurelius-atlas-ui-breadcrumbs")?.textContent)).toBe("beta");
        expect(normalize(rows[1].querySelector("td")?.textContent)).toBe("Removed");
        expect(normalize(rows[1].querySelector("aurelius-atlas-ui-breadcrumbs")?.textContent)).toBe("alpha");
    });

    it("a relationship crumb carries its end's type icon (HST-12, DET-26)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock);
        const crumbs = [...pane.querySelectorAll("aurelius-atlas-ui-breadcrumbs")];

        expect(crumbs).toHaveLength(2);
        expect(crumbs[0]?.querySelector("fa-icon svg")).toBeTruthy();
    });

    it("pressing a relationship crumb opens that entity's details and closes the drawer (HST-12)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const pane = openChangePane(compiled, fixture, httpMock);
        const link = pane.querySelector<HTMLAnchorElement>("aurelius-atlas-ui-breadcrumbs a")!;
        expect(link.getAttribute("href")).toBe("#");

        link.click();
        fixture.detectChanges();

        expect(navigate).toHaveBeenCalledWith([{ outlets: { primary: ["search", "details", "b"], drawer: null } }]);
        // Pressing a crumb reads nothing: the audit wire stays read-only and no
        // read goes out for the end the crumb names (AUD-06, DD-823).
        httpMock.verify();
    });

    it("the edited entity's own end prints as plain text and presses nothing (HST-12, UIC-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");

        const pane = openChangePane(compiled, fixture, httpMock, [
            stateAuditEvent("ENTITY_UPDATE", "1700000020000:0", { name: "n" }, { input: [{ guid: "7a1b" }] }),
            stateAuditEvent("ENTITY_UPDATE", "1700000010000:0", { name: "n" }, { input: [] }),
        ]);

        // The end carries no display text, so the crumb names it by its guid
        // (HST-12), and it is the entity the drawer edits — text, not a link.
        const crumb = pane.querySelector<HTMLElement>("aurelius-atlas-ui-breadcrumbs")!;
        expect(normalize(crumb.textContent)).toBe("7a1b");
        expect(crumb.querySelector("a")).toBeNull();

        crumb.click();
        fixture.detectChanges();
        expect(navigate).not.toHaveBeenCalled();
    });
});

describe("EntityEditor history change-table words (HST-14)", () => {
    it("a name cell words a field as the form words it (HST-14)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        // `qualifiedName` and `systems` both have a dictionary label; `input`
        // has none. The trail shows all three shapes at once (EDT-33, EDT-03).
        const pane = openChangePane(compiled, fixture, httpMock, [
            stateAuditEvent(
                "ENTITY_UPDATE",
                "1700000020000:0",
                { qualifiedName: "q-new" },
                {
                    systems: [{ guid: "b", typeName: "m4i_system", displayText: "beta" }],
                    input: [{ guid: "c", displayText: "gamma" }],
                },
            ),
            stateAuditEvent("ENTITY_UPDATE", "1700000010000:0", { qualifiedName: "q-old" }, { systems: [], input: [] }),
        ]);
        const tables = auditTables(pane);

        const attributeName = [...tables[0].querySelectorAll("tbody tr")].map((row) =>
            normalize(row.querySelectorAll("td")[1]?.textContent)!,
        );
        expect(attributeName).toEqual(["Qualified Name"]);

        const relationshipName = [...tables[1].querySelectorAll("tbody tr")].map((row) =>
            normalize(row.querySelectorAll("td")[1]?.textContent)!,
        );
        // One catalogued, one uncatalogued: the second keeps the word Atlas
        // stores it under, exactly as its own form field would (EDT-03).
        expect(relationshipName.sort()).toEqual(["Systems", "input"]);
    });
});

/** The description blocks of an open change list, in the order they print
 * (HST-15). */
function proseBlocks(pane: HTMLElement): HTMLElement[] {
    return [...pane.querySelectorAll<HTMLElement>(".aurelius-editor-audit-prose")];
}

/** The trail of the description tests: one write rewords one word of the
 * description, so the change carries a taken word and a put-in word (HST-15). */
const PROSE_TRAIL: EntityAuditEventV2[] = [
    stateAuditEvent("ENTITY_UPDATE", "1700000020000:0", { description: "The table holds aligned variants" }),
    stateAuditEvent("ENTITY_UPDATE", "1700000010000:0", { description: "The table holds raw variants" }),
];

describe("EntityEditor history description diff (HST-15, HST-16)", () => {
    it("a reworded description prints under the tables with its marks (HST-15)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock, PROSE_TRAIL);

        // The block names its own attribute with the same word the form's field
        // carries, and asks for no section caption above it (HST-14, HST-15).
        const text = normalize(pane.textContent);
        expect(text).toContain("Description");
        expect(text).not.toContain("Descriptions");
        // The fix shows as the words that moved, with the words around it (HST-10's
        // marks, DD-825).
        const block = proseBlocks(pane)[0];
        expect(block?.querySelector("ins")?.textContent?.trim()).toBe("aligned");
        expect(normalize(block?.textContent)).toContain("The table holds");
        expect(normalize(block?.textContent)).toContain("variants");
        // Nothing else changed, so no table prints at all (HST-12's rule).
        expect(auditTables(pane)).toHaveLength(0);
    });

    it("the one prose attribute leaves the attributes table (HST-15, EDT-20, SPA-06)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock, [
            stateAuditEvent("ENTITY_UPDATE", "1700000020000:0", {
                name: "second",
                description: "new summary",
                summaryNote: "new note",
            }),
            stateAuditEvent("ENTITY_UPDATE", "1700000010000:0", {
                name: "first",
                description: "old summary",
                summaryNote: "old note",
            }),
        ]);
        const tables = auditTables(pane);

        // The table holds the value attributes only: the one prose key leaves
        // for its own section (HST-15), and `summaryNote` — not a prose key
        // since 18.8 — rides the table as any other attribute does.
        expect(tables).toHaveLength(1);
        expect(
            [...tables[0].querySelectorAll("tbody tr")].map((row) =>
                normalize(row.querySelectorAll("td")[1]?.textContent),
            ),
        ).toEqual(["Name", "summaryNote"]);
        expect(normalize(tables[0].textContent)).not.toContain("description");
        expect(proseBlocks(pane)).toHaveLength(1);
        expect(normalize(proseBlocks(pane)[0]?.textContent)).toContain("Description");
    });

    it("a worded-out description prints its whole text as taken (HST-15)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock, [
            stateAuditEvent("ENTITY_UPDATE", "1700000020000:0", { description: "" }),
            stateAuditEvent("ENTITY_UPDATE", "1700000010000:0", { description: "a written description" }),
        ]);
        const block = proseBlocks(pane)[0];

        expect(block?.querySelector("del")?.textContent?.trim()).toBe("a written description");
        expect(block?.querySelector("ins")).toBeNull();
    });

    it("a description filled for the first time prints all its words as put in (HST-15)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock, [
            stateAuditEvent("ENTITY_CREATE", "1700000010000:0", { description: "the first text" }),
        ]);
        const block = proseBlocks(pane)[0];

        expect(block?.querySelector("ins")?.textContent?.trim()).toBe("the first text");
        expect(block?.querySelector("del")).toBeNull();
    });

    it("a long run of kept words folds to one marker stating the count (HST-16)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const long = Array.from({ length: 40 }, (_, index) => `word${index}`).join(" ");
        const pane = openChangePane(compiled, fixture, httpMock, [
            stateAuditEvent("ENTITY_UPDATE", "1700000020000:0", { description: `${long} final` }),
            stateAuditEvent("ENTITY_UPDATE", "1700000010000:0", { description: `${long} last` }),
        ]);
        const text = normalize(proseBlocks(pane)[0]?.textContent);

        // The words around the fix print, the run between them says how many it
        // left out, and the whole text does not (HST-16).
        expect(text).toContain("word0 word1");
        expect(text).toMatch(/\d+ words left out/);
        expect(text).not.toContain("word20");
        expect(proseBlocks(pane)[0]?.querySelector("del")?.textContent?.trim()).toBe("last");
        expect(proseBlocks(pane)[0]?.querySelector("ins")?.textContent?.trim()).toBe("final");
    });

    it("a small edit prints in full, without a marker (HST-16)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock, PROSE_TRAIL);

        expect(normalize(proseBlocks(pane)[0]?.textContent)).not.toContain("left out");
    });

    it("a marked word carries the theme's wash behind it (HST-15)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock, PROSE_TRAIL);
        const block = proseBlocks(pane).at(0);

        // The added words take the success wash and the taken words the danger
        // wash, both from the theme's own helpers — no colour of its own, so the
        // dark theme shades itself (DD-825).
        expect(block?.querySelector("ins")?.classList.contains("has-background-success-soft")).toBe(true);
        expect(block?.querySelector("del")?.classList.contains("has-background-danger-soft")).toBe(true);
        // The marks themselves stay, so the change still reads without the colour.
        expect(block?.querySelector("ins")?.tagName).toBe("INS");
        expect(block?.querySelector("del")?.tagName).toBe("DEL");
    });

    it("the tables' own marks keep 7.37's plain look (HST-12, HST-15)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock);
        const cell = auditTables(pane)[0].querySelector(".aurelius-editor-audit-value")!;

        // The wash belongs to the prose section only: a table value cell answers
        // every attribute the same short way (HST-10).
        expect(cell.querySelector("del")?.className).toBe("");
        expect(cell.querySelector("ins")?.className).toBe("");
    });

    it("the section prints for a person who cannot write and offers no button (HST-15, EDT-09)", () => {
        const { fixture, compiled, httpMock } = setup({ atlasWrite: false });
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock, PROSE_TRAIL);

        expect(proseBlocks(pane)).toHaveLength(1);
        expect(pane.querySelectorAll(".aurelius-editor-restore")).toHaveLength(0);
        // The words come from the states the change list already holds: opening
        // the section asks the server for nothing (AUD-06, HST-16).
        httpMock.verify();
    });

    it("a blank description the store carries on every body claims no line (HST-13, HST-15)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const pane = openChangePane(compiled, fixture, httpMock, [
            stateAuditEvent("ENTITY_CREATE", "1700000010000:0", { name: "n", definition: "", description: "set" }),
        ]);

        expect(proseBlocks(pane)).toHaveLength(1);
        expect(normalize(proseBlocks(pane)[0]?.textContent)).toContain("Description");
        expect(normalize(pane.textContent)).not.toContain("Definition");
    });
});

/** The matcher for one restore write (HST-11, EWR-15): the single-attribute
 * PUT of the changed line's attribute, the body carrying its stored old value. */
function restoreRequest(name: string) {
    return (request: HttpRequest<unknown>) =>
        request.method === "PUT" && request.url === `${ATLAS_ENTITY_URL}7a1b` && request.params.get("name") === name;
}

/** Open the newest row's change list and return its restore buttons (HST-11). */
function openRestoreButtons(
    compiled: HTMLElement,
    fixture: ComponentFixture<EntityEditor>,
    httpMock: HttpTestingController,
    trail: EntityAuditEventV2[] = CHANGED_TRAIL,
): HTMLButtonElement[] {
    openHistoryTab(compiled, fixture);
    httpMock.expectOne(AUDIT_URL).flush(trail);
    fixture.detectChanges();
    auditToggle(auditRows(compiled)[0]).click();
    fixture.detectChanges();

    return [
        ...(auditChangePane(auditRows(compiled)[0])?.querySelectorAll<HTMLButtonElement>(".aurelius-editor-restore") ??
            []),
    ];
}

describe("EntityEditor history attribute restore (HST-11)", () => {
    it("a changed line carries a restore button and a press writes one attribute back (HST-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const buttons = openRestoreButtons(compiled, fixture, httpMock);

        expect(buttons).toHaveLength(1);
        expect(normalize(buttons[0]?.textContent)).toBe("Restore");
        expect(buttons[0]?.getAttribute("aria-label")).toBe("Restore Name");

        buttons[0]?.click();
        fixture.detectChanges();
        const write = httpMock.expectOne(restoreRequest("name"));
        expect(write.request.body).toBe("first");
        write.flush({});
        fixture.detectChanges();
        // The drawer's own read follows the write (VDR-07), so the form answers
        // the stored entity (HST-11, DD-822).
        httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(savedView());
        fixture.detectChanges();
    });

    it("a create line lists everything as added and carries no button (HST-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const buttons = openRestoreButtons(compiled, fixture, httpMock, [
            stateAuditEvent("ENTITY_CREATE", "1700000010000:0", { name: "first" }),
        ]);

        expect(auditChangePane(auditRows(compiled)[0])?.textContent).toContain("Added");
        expect(buttons).toHaveLength(0);
    });

    it("a removed line, a list value and a relationship end carry no button (HST-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);

        const buttons = openRestoreButtons(compiled, fixture, httpMock, [
            stateAuditEvent(
                "ENTITY_UPDATE",
                "1700000030000:0",
                { list: [1, 3] },
                { input: [{ guid: "b", displayText: "beta" }] },
            ),
            stateAuditEvent(
                "ENTITY_UPDATE",
                "1700000020000:0",
                { name: "gone", list: [1, 2] },
                { input: [{ guid: "a", displayText: "alpha" }] },
            ),
        ]);

        // The list's own diff lines are all there (HST-10), and none of them
        // asks for a write: a removed attribute, a list value, and ends.
        const pane = auditChangePane(auditRows(compiled)[0])!;
        const text = normalize(pane.textContent);
        expect(text).toContain("Removed");
        expect(text).toContain("list");
        expect(text).toContain("Relationships");
        expect(buttons).toHaveLength(0);
    });

    it("no line offers a restore when the person cannot write (HST-11, EDT-09)", () => {
        const { fixture, compiled, httpMock } = setup({ atlasWrite: false });
        arrive(fixture, httpMock);

        expect(openRestoreButtons(compiled, fixture, httpMock)).toHaveLength(0);
    });

    it("create mode offers no History tab and so no restore (HST-11, HST-01)", () => {
        const { fixture, compiled, httpMock } = setup({ create: true, createType: "DataSet" });
        arriveTypeDefs(fixture, httpMock, "DataSet");

        // No tab pair (HST-01), so the pane behind it is never opened and
        // nothing in it asks for a write.
        expect(compiled.querySelector("#editor-history-tab")).toBeNull();
        expect(compiled.querySelector("#editor-history-pane")?.hasAttribute("hidden")).toBe(true);
        expect(compiled.querySelector(".aurelius-editor-restore")).toBeNull();
        httpMock.verify();
    });

    it("the button is disabled while the write is in flight and a second press sends nothing (HST-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const buttons = openRestoreButtons(compiled, fixture, httpMock);

        buttons[0]?.click();
        fixture.detectChanges();
        const write = httpMock.expectOne(restoreRequest("name"));
        const held = auditChangePane(auditRows(compiled)[0])!.querySelectorAll<HTMLButtonElement>(
            ".aurelius-editor-restore",
        );
        expect(held).toHaveLength(1);
        expect(held[0]?.disabled).toBe(true);
        expect(held[0]?.getAttribute("aria-busy")).toBe("true");

        // A second press on the busy line asks for nothing (one write at a time).
        held[0]?.click();
        fixture.detectChanges();
        httpMock.expectNone(restoreRequest("name"));

        write.flush({});
        fixture.detectChanges();
        httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(savedView());
        fixture.detectChanges();
    });

    it("a success re-reads and merges the stored entity into the form (HST-11, VDE-07)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        const buttons = openRestoreButtons(compiled, fixture, httpMock);

        // An edit in another control stays the person's (DD-822: only the one
        // attribute travels).
        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "typed by hand";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();

        buttons[0]?.click();
        fixture.detectChanges();
        const write = httpMock.expectOne(restoreRequest("name"));
        write.flush({});
        fixture.detectChanges();
        const reread = httpMock.expectOne((request) => request.url.startsWith(VIEW_URL));
        reread.flush(
            savedView({
                name: "restored_name",
                displayText: "restored_name",
                attributes: { ...ANSWER.attributes, name: "restored_name", description: "restored summary" },
            }),
        );
        fixture.detectChanges();
        fixture.detectChanges();

        // The touched control keeps the person's value and the untouched one
        // answers the stored entity (VDE-07, DD-610). The untouched control is
        // the prose textarea — the base owner is hidden (EDT-37).
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("typed by hand");
        expect(compiled.querySelector<HTMLTextAreaElement>("textarea#editor-description")?.value).toBe(
            "restored summary",
        );
        // The line says what the write did (LR-005), and the drawer stays open
        // with the change list the person was reading (DD-822).
        expect(normalize(compiled.querySelector(".aurelius-editor-outcome")?.textContent)).toBe("Entity restored");
        expect(auditChangePane(auditRows(compiled)[0])).not.toBeNull();
        expect(compiled.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
        expect(navigate).not.toHaveBeenCalled();
        expect(add).not.toHaveBeenCalled();
    });

    it("a refusal alerts once and keeps the drawer, the list and the edit (HST-11)", () => {
        const { fixture, compiled, httpMock } = setup();
        arrive(fixture, httpMock);
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        const navigate = vi.spyOn(TestBed.inject(Router), "navigate");
        const buttons = openRestoreButtons(compiled, fixture, httpMock);

        const nameInput = compiled.querySelector<HTMLInputElement>("#editor-name")!;
        nameInput.value = "typed by hand";
        nameInput.dispatchEvent(new Event("input"));
        fixture.detectChanges();

        buttons[0]?.click();
        fixture.detectChanges();
        httpMock.expectOne(restoreRequest("name")).flush({}, { status: 403, statusText: "Forbidden" });
        fixture.detectChanges();

        expect(add).toHaveBeenCalledTimes(1);
        expect(add).toHaveBeenCalledWith(
            expect.objectContaining({ severity: "error", message: "Restoring the attribute", source: "search" }),
        );
        // Nothing re-reads, nothing navigates, and the edits and the open list
        // stay as the person left them (HST-06's shape).
        httpMock.expectNone(
            (request) => request.url.startsWith(VIEW_URL) && request.method === "GET" && !request.url.includes("audit"),
        );
        expect(compiled.querySelector<HTMLInputElement>("#editor-name")?.value).toBe("typed by hand");
        expect(auditChangePane(auditRows(compiled)[0])).not.toBeNull();
        expect(compiled.querySelector("dialog.aurelius-drawer-panel")).toBeTruthy();
        expect(navigate).not.toHaveBeenCalled();
        const again = auditChangePane(auditRows(compiled)[0])!.querySelectorAll<HTMLButtonElement>(
            ".aurelius-editor-restore",
        );
        expect(again).toHaveLength(1);
        expect(again[0]?.disabled).toBe(false);
    });
});
