import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";

import { LAYOUTS, type TypeLayout } from "./section-config";
import { DetailsLayoutState } from "./layout.state";

/**
 * The layout dispatch (DET-15, DD-366; 7.21c's eighth name, DET-33/DD-383):
 * the eight names answer directly, a type naming one of them among its super
 * types inherits that layout, and everything else — built-in errors among
 * them — keeps the default. The typedef cache rule: one read per name, one
 * URL (APC-01).
 */
const TYPEDEF_URL = "/api/atlas/v2/types/typedef/name/";

/** An entity typedef answer with the given super types. */
function entityDef(superTypes: string[]): Record<string, unknown> {
    return { category: "ENTITY_DEF", name: "whatever", superTypes };
}

function setup() {
    TestBed.configureTestingModule({
        providers: [DetailsLayoutState, provideHttpClient(), provideHttpClientTesting()],
    });
    const store = TestBed.inject(DetailsLayoutState);
    const httpMock = TestBed.inject(HttpTestingController);
    return { store, httpMock };
}

/** Settle every in-flight typedef read with the given answer. */
function flushTypeDefs(httpMock: HttpTestingController, answer: Record<string, unknown> | "error") {
    for (const request of httpMock.match((r) => r.url.startsWith(TYPEDEF_URL))) {
        if (answer === "error") {
            request.flush({}, { status: 404, statusText: "Not Found" });
        } else {
            request.flush(answer);
        }
    }
}

/** Let the walk's promise chain settle. */
async function settle() {
    await new Promise((resolve) => setTimeout(resolve));
}

describe("Layout dispatch (DET-15)", () => {
    it("each of the eight names answers its layout without a read (DET-15, DET-33)", () => {
        const { store, httpMock } = setup();

        for (const name of Object.keys(LAYOUTS)) {
            store.resolve(name);
            expect(store.layout()).toBe(LAYOUTS[name as keyof typeof LAYOUTS]);
        }
        httpMock.expectNone(TYPEDEF_URL); // a direct hit never reads a typedef
        httpMock.verify();
    });

    it("the built-in Process keeps the default: the walk ends at its error (DET-33)", async () => {
        const { store, httpMock } = setup();

        // DET-33's row names the m4i type, as the legacy's dispatch did; a
        // plain `Process` (the Atlas built-in) walks, its typedef read
        // answers SYSTEM_TYPE, and the branch ends at the default.
        store.resolve("Process");
        expect(store.layout()).toBeUndefined();
        flushTypeDefs(httpMock, "error");
        await settle();

        expect(store.layout()).toBeUndefined();
        httpMock.verify();
    });

    it("a non-m4i type whose supertypes are all plain keeps the default (DET-15)", async () => {
        const { store, httpMock } = setup();

        store.resolve("DataSet");
        expect(store.layout()).toBeUndefined(); // default chrome while unresolved
        flushTypeDefs(httpMock, entityDef(["Asset", "Process"]));
        await settle();
        // Each non-m4i supertype is read in turn; none has a typedef of
        // its own (the error ends the branch) and none names one of the
        // seven, so the walk ends at the default.
        flushTypeDefs(httpMock, "error");
        await settle();
        flushTypeDefs(httpMock, "error");
        await settle();

        expect(store.layout()).toBeUndefined();
        httpMock.verify();
    });

    it("a subtype of one of the seven takes that layout (DET-15)", async () => {
        const { store, httpMock } = setup();

        store.resolve("my_custom_entity");
        flushTypeDefs(httpMock, entityDef(["m4i_data_entity"]));
        await settle();

        expect(store.layout()).toBe(LAYOUTS.m4i_data_entity);
        httpMock.verify();
    });

    it("walks past a non-m4i supertype to the m4i name (DET-15)", async () => {
        const { store, httpMock } = setup();

        store.resolve("deep_type");
        // The first supertype is not m4i; its own walk finds the m4i root.
        const first = httpMock.expectOne(`${TYPEDEF_URL}deep_type`);
        first.flush(entityDef(["middle_type"]));
        await settle();
        const second = httpMock.expectOne(`${TYPEDEF_URL}middle_type`);
        second.flush(entityDef(["m4i_data_attribute"]));
        await settle();

        expect(store.layout()).toBe(LAYOUTS.m4i_data_attribute);
        httpMock.verify();
    });

    it("the walk stops at a built-in: its error answer ends the branch (DET-15)", async () => {
        const { store, httpMock } = setup();

        store.resolve("plain_asset");
        flushTypeDefs(httpMock, entityDef(["Referenceable"]));
        await settle();
        // Referenceable is a built-in: its read answers SYSTEM_TYPE (the
        // error), the branch ends there with a null memo, and no further
        // URL rides the walk.
        flushTypeDefs(httpMock, "error");
        await settle();

        expect(store.layout()).toBeUndefined();
        httpMock.verify(); // the two reads above, nothing more
    });

    it("reads each name once: the typedef cache, and a re-resolve is free (DET-15)", async () => {
        const { store, httpMock } = setup();

        store.resolve("typed_once");
        flushTypeDefs(httpMock, entityDef(["m4i_field"]));
        await settle();
        expect(store.layout()).toBe(LAYOUTS.m4i_field);

        // The same name again: no request, same layout once the cached
        // walk settles (the guard answers from the typedef cache).
        store.resolve("m4i_data_domain");
        store.resolve("typed_once");
        httpMock.expectNone(TYPEDEF_URL);
        await settle();
        expect(store.layout()).toBe(LAYOUTS.m4i_field);

        // A second entity whose walk reaches the cached name: the cache
        // answers — one read of the new name, none of the old.
        store.resolve("another_type");
        const request = httpMock.expectOne(`${TYPEDEF_URL}another_type`);
        request.flush(entityDef(["typed_once"]));
        await settle();
        httpMock.expectNone(TYPEDEF_URL);

        // The layout inherits through the cached name: typed_once leads to
        // m4i_field, so the layout arrives without a second typedef read.
        expect(store.layout()).toBe(LAYOUTS.m4i_field);
        httpMock.verify();
    });

    it("a reset clears the layout and a quick switch cannot flash the old one (DET-15)", async () => {
        const { store, httpMock } = setup();

        store.resolve("slow_type"); // no answer yet — a walk is in flight
        store.resolve("m4i_system"); // a direct answer arrives at once
        expect(store.layout()).toBe(LAYOUTS.m4i_system);

        // The slow walk answers late: its answer is stale, the direct one
        // stands (the re-resolve guard).
        flushTypeDefs(httpMock, entityDef(["m4i_data_domain"]));
        await settle();
        expect(store.layout()).toBe(LAYOUTS.m4i_system);

        store.resolve(null);
        expect(store.layout()).toBeUndefined();
        httpMock.verify();
    });
});
