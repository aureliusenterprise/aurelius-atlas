import { HttpClient } from "@angular/common/http";
import { HttpTestingController } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";

import { canWriteEntities } from "../app/search/shared/can-write-entities";

import { VIEW_URL, TYPEDEF_URL } from "./api";
import { normalize, settleTypeDefs } from "./dom";
import { provideScreenTest } from "./providers";
import { view } from "./view-fixtures";

/**
 * The harness proves itself here (no rule id — it tests the test code): the
 * providers satisfy the real write gate, the fixture builder answers the
 * fields the doors always answer (AVS-01/06), and the two DOM helpers behave.
 * If a later change makes the harness lie about a provider, this spec fails
 * before a screen spec wastes a cycle on it.
 */
describe("the test harness itself", () => {
    /** Bring up the harness providers and read the write gate (EDT-09). */
    function canWrite(atlasWrite: boolean): boolean {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({ providers: provideScreenTest({ keycloak: { atlasWrite } }) });
        return TestBed.runInInjectionContext(() => canWriteEntities())();
    }

    it("serves the write gate: granted, and refused when the token lacks atlas-write (EDT-09, DD-324)", () => {
        expect(canWrite(true)).toBe(true);
        expect(canWrite(false)).toBe(false);
    });

    it("gives a fixture the fields every door answers (AVS-01, AVS-06)", () => {
        const fixture = view({ classificationNames: ["PII"] });

        expect(fixture.guid).toBe("7a1b");
        expect(fixture.typeName).toBe("DataSet");
        expect(fixture.displayText).toBe("genomic_variants");
        expect(fixture.qualifiedName).toBe("genomic_variants@cluster");
        expect(fixture.status).toBe("ACTIVE");
        expect(fixture.stale).toBe(false);
        expect(fixture.classificationNames).toEqual(["PII"]);
        // Absent fields stay absent, as the wire leaves them (AVS-06).
        expect("sections" in fixture).toBe(false);
        expect("quality" in fixture).toBe(false);
    });

    it("collapses markup whitespace (the ten specs' shared helper)", () => {
        expect(normalize("  a\n   b  ")).toBe("a b");
        expect(normalize(undefined)).toBeUndefined();
    });

    it("settles a typedef walk and leaves the read alone (DET-15)", () => {
        TestBed.configureTestingModule({ providers: provideScreenTest() });
        const http = TestBed.inject(HttpClient);
        const httpMock = TestBed.inject(HttpTestingController);

        // Both carry an error handler, as every service's read does: a bare
        // subscribe() would let the 404 escape as an unhandled error.
        http.get(`${VIEW_URL}x`).subscribe({ error: () => undefined });
        http.get(`${TYPEDEF_URL}DataSet`).subscribe({ error: () => undefined });

        settleTypeDefs(httpMock);

        // The walk's read is done with; the entity read is still in flight.
        expect(httpMock.match((r) => r.url.startsWith(TYPEDEF_URL))).toHaveLength(0);
        httpMock.expectOne(`${VIEW_URL}x`).flush({});
        httpMock.verify();
    });
});
