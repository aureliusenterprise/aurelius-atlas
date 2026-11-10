/**
 * The one-retry interceptor (APC-12): the retried set (idempotent methods only,
 * never POST), the failures that count as a dead wire (status 0, the gateway
 * statuses), the single attempt, and the untouched pass-through of everything
 * else. The chain order against the alerts reporter is pinned in
 * `app.config.spec.ts` (APC-13). The zoneless app has no `fakeAsync` (it
 * needs zone.js/testing), so the 150 ms wait rides vitest fake timers, the
 * idiom the editor's debounce specs use.
 */
import { HttpClient, provideHttpClient, withInterceptors } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { vi } from "vitest";

import { retryHttpInterceptor } from "./retry-http.interceptor";

function setup() {
    TestBed.configureTestingModule({
        providers: [provideHttpClient(withInterceptors([retryHttpInterceptor])), provideHttpClientTesting()],
    });

    return {
        http: TestBed.inject(HttpClient),
        controller: TestBed.inject(HttpTestingController),
    };
}

describe("retryHttpInterceptor (APC-12)", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => {
        vi.useRealTimers();
        TestBed.resetTestingModule();
    });

    it("resends a GET that died with no response, and the caller sees the saved answer (APC-12)", () => {
        const { http, controller } = setup();
        let answer: unknown;
        let failure: unknown;

        http.get("/api/atlas/v2/types/typedefs").subscribe({
            next: (body) => (answer = body),
            error: (error) => (failure = error),
        });

        controller.expectOne("/api/atlas/v2/types/typedefs").flush(null, { status: 0, statusText: "Unknown Error" });
        vi.advanceTimersByTime(150);
        controller.expectOne("/api/atlas/v2/types/typedefs").flush({ entityDefs: [] });

        expect(failure).toBeUndefined();
        expect(answer).toEqual({ entityDefs: [] });
        controller.verify();
    });

    it("resends a gateway status the same way (APC-12)", () => {
        const { http, controller } = setup();
        let answer: unknown;

        http.get("/api/atlas/admin/version").subscribe((body) => (answer = body));

        controller.expectOne("/api/atlas/admin/version").flush({}, { status: 502, statusText: "Bad Gateway" });
        vi.advanceTimersByTime(150);
        controller.expectOne("/api/atlas/admin/version").flush("2.4.0");

        expect(answer).toBe("2.4.0");
    });

    it("gives up after the one resend and passes the failure through (APC-12)", () => {
        const { http, controller } = setup();
        let failure: { status?: number } | undefined;

        http.get("/api/atlas/admin/status").subscribe({ error: (error) => (failure = error) });

        controller.expectOne("/api/atlas/admin/status").flush(null, { status: 0, statusText: "Unknown Error" });
        vi.advanceTimersByTime(150);
        controller.expectOne("/api/atlas/admin/status").flush(null, { status: 0, statusText: "Unknown Error" });
        vi.advanceTimersByTime(150);

        expect(failure?.status).toBe(0);
        controller.verify();
    });

    it("never resends a POST (APC-12)", () => {
        const { http, controller } = setup();
        let failure: { status?: number } | undefined;

        http.post("/api/atlas/v2/entity", {}).subscribe({ error: (error) => (failure = error) });

        controller.expectOne("/api/atlas/v2/entity").flush(null, { status: 0, statusText: "Unknown Error" });
        vi.advanceTimersByTime(200);

        expect(failure?.status).toBe(0);
        controller.verify();
    });

    it("passes an answered failure through untouched, with one request (APC-12)", () => {
        const { http, controller } = setup();
        const statuses: number[] = [];

        for (const status of [404, 500]) {
            http.get(`/api/atlas/v2/entity/guid/${status}`).subscribe({
                error: (error) => statuses.push(error.status),
            });

            controller.expectOne(`/api/atlas/v2/entity/guid/${status}`).flush({}, { status, statusText: "" });
        }
        vi.advanceTimersByTime(200);

        expect(statuses).toEqual([404, 500]);
        controller.verify();
    });

    it("resends a DELETE, the idempotent write (APC-12)", () => {
        const { http, controller } = setup();
        let answer: unknown;

        http.delete("/api/atlas/v2/entity/guid/g-1").subscribe((body) => (answer = body));
        controller.expectOne("/api/atlas/v2/entity/guid/g-1").flush(null, { status: 0, statusText: "" });
        vi.advanceTimersByTime(150);
        controller.expectOne("/api/atlas/v2/entity/guid/g-1").flush({ guid: "g-1" });

        expect(answer).toEqual({ guid: "g-1" });
        controller.verify();
    });
});
