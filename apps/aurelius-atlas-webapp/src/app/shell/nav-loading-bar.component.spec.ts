import { TestBed } from "@angular/core/testing";
import { Event, NavigationCancel, NavigationEnd, NavigationError, NavigationStart, Router } from "@angular/router";
import { Subject } from "rxjs";

import { NavLoadingBar } from "./nav-loading-bar.component";

/**
 * The bar with a controllable router: the subject stands in for
 * `Router.events`, the only input the component reads (SRH-09).
 */
function setup() {
    const events = new Subject<Event>();
    TestBed.configureTestingModule({
        imports: [NavLoadingBar],
        providers: [{ provide: Router, useValue: { events } }],
    });
    const fixture = TestBed.createComponent(NavLoadingBar);
    fixture.detectChanges();
    return { events, fixture, compiled: fixture.nativeElement as HTMLElement };
}

/** Feed a navigation event; zoneless change detection is signal-driven. */
function emit(harness: { events: Subject<Event>; fixture: { detectChanges(): void } }, event: Event) {
    harness.events.next(event);
    harness.fixture.detectChanges();
}

describe("NavLoadingBar (SRH-09)", () => {
    it("is invisible at rest", () => {
        const { compiled } = setup();

        expect(compiled.querySelector("progress")).toBeFalsy();
    });

    it("shows the Bulma bar from NavigationStart to NavigationEnd (the legacy isNavigating)", () => {
        const harness = setup();

        emit(harness, new NavigationStart(1, "/search/results"));
        const bar = harness.compiled.querySelector("progress")!;
        expect(bar).toBeTruthy();
        expect(bar.classList.contains("progress")).toBe(true);
        expect(bar.classList.contains("is-link")).toBe(true);
        expect(bar.getAttribute("max")).toBe("100");

        emit(harness, new NavigationEnd(1, "/search/results", "/search/results"));
        expect(harness.compiled.querySelector("progress")).toBeFalsy();
    });

    it("a NavigationError hides the bar", () => {
        const harness = setup();

        emit(harness, new NavigationStart(2, "/x"));
        emit(harness, new NavigationError(2, "/x", new Error("nope")));

        expect(harness.compiled.querySelector("progress")).toBeFalsy();
    });

    it("a NavigationCancel — a guard's redirect — hides the bar", () => {
        const harness = setup();

        emit(harness, new NavigationStart(3, "/x"));
        emit(harness, new NavigationCancel(3, "/x", "/search/browse"));

        expect(harness.compiled.querySelector("progress")).toBeFalsy();
    });
});
