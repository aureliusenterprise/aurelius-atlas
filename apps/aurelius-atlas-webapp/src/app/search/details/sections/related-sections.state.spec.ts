import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import type { AtlasEntitiesWithExtInfo, AtlasEntity } from "aurelius-atlas-data-access";

import { AlertsService } from "../../../alerts/alerts.service";
import { LAYOUTS } from "./section-config";
import { CHUNK_SIZE, PAGE_SIZE, RelatedSectionsState } from "./related-sections.state";

/**
 * The card-section store (DET-17..DET-22, DD-365/DD-368): the seed off the
 * entity's `relationshipAttributes`, the chunked bulk resolve, and the
 * client-side filter, sort, and page. Specs ride the details screen's
 * idiom — `provideHttpClientTesting`, `expectOne` + `flush`.
 */
const BULK_URL = "/api/atlas/v2/entity/bulk";

/** The entity layout's sections: every section of one type at once. */
const LAYOUT = LAYOUTS.m4i_data_entity;

/** A related-entity end of `relationshipAttributes`. */
function related(guid: string, displayText: string, status?: string): Record<string, unknown> {
    return {
        guid,
        displayText,
        typeName: "m4i_data_attribute",
        name: displayText,
        ...(status === undefined ? {} : { relationshipStatus: status }),
    };
}

/** A resolved entity for the bulk answer. */
function resolved(
    guid: string,
    name: string,
    description?: string,
): NonNullable<AtlasEntitiesWithExtInfo["entities"]>[number] {
    return {
        guid,
        typeName: "m4i_data_attribute",
        attributes: {
            name,
            qualifiedName: `${name}@cluster`,
            ...(description === undefined ? {} : { description }),
        },
    };
}

/** An opened entity whose attribute section seeds the given ends. */
function opened(seed: Record<string, unknown>[]): AtlasEntity {
    return {
        guid: "opened",
        typeName: "m4i_data_entity",
        attributes: { name: "opened" },
        relationshipAttributes: { attributes: seed },
    };
}

function setup() {
    TestBed.configureTestingModule({
        providers: [RelatedSectionsState, provideHttpClient(), provideHttpClientTesting()],
    });
    const store = TestBed.inject(RelatedSectionsState);
    const httpMock = TestBed.inject(HttpTestingController);
    return { store, httpMock };
}

/** The bulk requests still in flight. */
function bulkRequests(httpMock: HttpTestingController) {
    return httpMock.match((request) => request.url === BULK_URL);
}

/** Deliver every in-flight bulk chunk with its own guids' cards. */
function flushAll(
    httpMock: HttpTestingController,
    answer: (guids: string[]) => NonNullable<AtlasEntitiesWithExtInfo["entities"]> = (guids) =>
        guids.map((guid) => resolved(guid, `attr-${guid}`)),
) {
    for (const request of bulkRequests(httpMock)) {
        const guids = request.request.params.getAll("guid") ?? [];
        request.flush({ entities: answer(guids), referredEntities: {} });
    }
}

describe("Related sections store (DET-17..DET-22)", () => {
    it("seeds each section from the relationship ends, ACTIVE and guid-bearing only (DET-17)", () => {
        const { store, httpMock } = setup();

        store.seed(
            opened([
                related("a1", "Alpha"),
                related("a2", "Deleted", "DELETED"),
                { displayText: "No guid" },
                related("a4", "Beta"),
            ]),
            LAYOUT,
        );

        const views = store.views();
        const attributes = views.find((view) => view.anchor === "related-attributes");
        expect(attributes?.count).toBe(2); // a1 + a4: the DELETED and guidless end drop
        expect(store.countFor("related-attributes")).toBe(2);
        expect(attributes?.cards.map((card) => card.guid)).toEqual(["a1", "a4"]);
        // The child section has no ends: a zero view, no request (DET-17).
        const children = views.find((view) => view.anchor === "related-entities");
        expect(children?.count).toBe(0);
        bulkRequests(httpMock).forEach((request) => request.flush({ entities: [] }));
        httpMock.verify();
    });

    it("shows the count before any card resolves, as loading cards (DET-17, DET-18)", () => {
        const { store, httpMock } = setup();
        store.seed(opened([related("a1", "Alpha"), related("a2", "Beta")]), LAYOUT);

        const attributes = store.views().find((view) => view.anchor === "related-attributes");
        expect(attributes?.count).toBe(2); // the count is ahead of the cards
        expect(attributes?.loading).toBe(true);
        expect(attributes?.cards.map((card) => card.kind)).toEqual(["loading", "loading"]);
        flushAll(httpMock);

        const after = store.views().find((view) => view.anchor === "related-attributes");
        expect(after?.loading).toBe(false);
        expect(after?.cards.map((card) => (card.kind === "card" ? card.displayText : "?"))).toEqual([
            "attr-a1",
            "attr-a2",
        ]);
        httpMock.verify();
    });

    it("resolves the seed in chunks of at most 25 (DET-18, DD-368)", () => {
        const { store, httpMock } = setup();
        const seed = Array.from({ length: CHUNK_SIZE + 1 }, (_, index) => related(`g${index}`, `g${index}`));
        store.seed(opened(seed), LAYOUT);

        const requests = bulkRequests(httpMock);
        expect(requests).toHaveLength(2); // 26 guids travel as 25 + 1
        expect(requests[0].request.params.getAll("guid")).toHaveLength(CHUNK_SIZE);
        expect(requests[1].request.params.getAll("guid")).toHaveLength(1);
        flushAll(httpMock);
        expect(store.views().find((view) => view.anchor === "related-attributes")?.count).toBe(CHUNK_SIZE + 1);
        httpMock.verify();
    });

    it("a guid missing from the answer is a deleted relation: no card, the count keeps it (DET-18)", () => {
        const { store, httpMock } = setup();
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        store.seed(opened([related("a1", "Alpha"), related("a2", "Beta")]), LAYOUT);

        // The answer holds only one of the two: a deleted relation, not an
        // error — no card for a2, no alert.
        flushAll(httpMock, (guids) => guids.slice(0, 1).map((guid) => resolved(guid, `attr-${guid}`)));

        const attributes = store.views().find((view) => view.anchor === "related-attributes");
        expect(attributes?.count).toBe(2); // the count keeps the missing guid
        expect(attributes?.cards.map((card) => card.guid)).toEqual(["a1"]);
        expect(add).not.toHaveBeenCalled();
        httpMock.verify();
    });

    it("drops a failed chunk's cards with one alert, keeps its count (DET-18)", () => {
        const { store, httpMock } = setup();
        const add = vi.spyOn(TestBed.inject(AlertsService), "add");
        store.seed(opened([related("a1", "Alpha"), related("a2", "Beta")]), LAYOUT);

        bulkRequests(httpMock)[0].flush({ error: "boom" }, { status: 500, statusText: "Server Error" });

        const attributes = store.views().find((view) => view.anchor === "related-attributes");
        expect(attributes?.count).toBe(2); // the count keeps the dropped cards
        expect(attributes?.cards).toHaveLength(0);
        expect(attributes?.loading).toBe(false);
        expect(add).toHaveBeenCalledTimes(1);
        expect(add).toHaveBeenCalledWith({
            severity: "error",
            source: "search",
            message: "Retrieving the entity details",
        });
        httpMock.expectNone(BULK_URL); // no retry loop
    });

    it("filters as the text is typed, not only on submit (DET-20, DD-375)", () => {
        const { store, httpMock } = setup();
        store.seed(opened([related("a1", "Alpha"), related("a2", "Beta")]), LAYOUT);
        flushAll(httpMock);

        // The keystroke path (the part's queryChange model), with no submit.
        store.setText("related-attributes", "attr-a2");
        const typed = store.views().find((view) => view.anchor === "related-attributes");
        expect(typed?.filtered).toBe(true);
        expect(typed?.countShown).toBe(1);
        expect(typed?.cards.map((card) => card.guid)).toEqual(["a2"]);
        // The box keeps the typed text.
        expect(typed?.query).toBe("attr-a2");

        // Backspacing to empty clears the filter.
        store.setText("related-attributes", "");
        const cleared = store.views().find((view) => view.anchor === "related-attributes");
        expect(cleared?.filtered).toBe(false);
        expect(cleared?.cards).toHaveLength(2);
        httpMock.verify();
    });

    it("filters on the submitted term and clears on null (DET-20)", () => {
        const { store, httpMock } = setup();
        store.seed(opened([related("a1", "Alpha"), related("a2", "Beta")]), LAYOUT);
        flushAll(httpMock);
        store.setQuery("related-attributes", "attr-a2");

        const filtered = store.views().find((view) => view.anchor === "related-attributes");
        expect(filtered?.filtered).toBe(true);
        expect(filtered?.countShown).toBe(1); // the count line shows the filtered count
        expect(filtered?.count).toBe(2); // the stats count stays the seed's
        expect(filtered?.cards.map((card) => card.guid)).toEqual(["a2"]);

        store.setQuery("related-attributes", null);
        const cleared = store.views().find((view) => view.anchor === "related-attributes");
        expect(cleared?.filtered).toBe(false);
        expect(cleared?.countShown).toBe(2);
        expect(cleared?.cards).toHaveLength(2);
        httpMock.verify();
    });

    it("matches the qualifiedName and the description, case-insensitively (DET-20, DD-368)", () => {
        const { store, httpMock } = setup();
        store.seed(opened([related("a1", "Alpha"), related("a2", "Beta")]), LAYOUT);
        flushAll(httpMock, (guids) => [
            resolved("a1", "alpha-one", "Sequencing reads"),
            { ...resolved("a2", "beta-two"), attributes: { name: "beta-two", qualifiedName: "beta@warehouse" } },
        ]);

        store.setQuery("related-attributes", "SEQUENCING");
        expect(
            store
                .views()
                .find((view) => view.anchor === "related-attributes")
                ?.cards.map((c) => c.guid),
        ).toEqual(["a1"]);

        store.setQuery("related-attributes", "warehouse");
        expect(
            store
                .views()
                .find((view) => view.anchor === "related-attributes")
                ?.cards.map((c) => c.guid),
        ).toEqual(["a2"]);
        httpMock.verify();
    });

    it("the reset link clears the query and the sort (DET-20)", () => {
        const { store, httpMock } = setup();
        store.seed(opened([related("a1", "Alpha"), related("a2", "Beta")]), LAYOUT);
        flushAll(httpMock);
        store.setQuery("related-attributes", "beta");
        store.setSort("related-attributes", "name");
        store.toggleDirection("related-attributes");

        store.reset("related-attributes");

        const view = store.views().find((view) => view.anchor === "related-attributes");
        expect(view?.filtered).toBe(false);
        expect(view?.query).toBeNull();
        expect(view?.sort).toBe("relevance");
        expect(view?.descending).toBe(false);
        httpMock.verify();
    });

    it("sorts by name over the display texts; the direction reverses (DET-21)", () => {
        const { store, httpMock } = setup();
        store.seed(opened([related("a1", "zebra"), related("a2", "alpha")]), LAYOUT);
        flushAll(httpMock, (guids) => [resolved("a1", "zebra-name"), resolved("a2", "alpha-name")]);
        // A resolved card's display text is its `name` attribute
        // (cardDisplayText): the sort compares those.
        store.setSort("related-attributes", "name");
        expect(
            store
                .views()
                .find((view) => view.anchor === "related-attributes")
                ?.cards.map((c) => c.displayText),
        ).toEqual(["alpha-name", "zebra-name"]);

        store.toggleDirection("related-attributes");
        expect(
            store
                .views()
                .find((view) => view.anchor === "related-attributes")
                ?.cards.map((c) => c.displayText),
        ).toEqual(["zebra-name", "alpha-name"]);
        httpMock.verify();
    });

    it("pages at 9 and extends the page on nextPage (DET-22)", () => {
        const { store, httpMock } = setup();
        const seed = Array.from({ length: PAGE_SIZE + 2 }, (_, index) => related(`g${index}`, `name-${index}`));
        store.seed(opened(seed), LAYOUT);
        flushAll(httpMock, (guids) => guids.map((guid) => resolved(guid, `attr-${guid}`)));

        let view = store.views().find((view) => view.anchor === "related-attributes");
        expect(view?.cards).toHaveLength(PAGE_SIZE);
        expect(view?.allLoaded).toBe(false);

        store.nextPage("related-attributes");
        view = store.views().find((view) => view.anchor === "related-attributes");
        expect(view?.cards).toHaveLength(PAGE_SIZE + 2);
        expect(view?.allLoaded).toBe(true);
        httpMock.verify();
    });

    it("a re-seed drops in-flight answers and re-seeds the sections (DET-17)", () => {
        const { store, httpMock } = setup();
        store.seed(opened([related("a1", "Alpha")]), LAYOUT);
        const before = bulkRequests(httpMock);

        // The editor's save re-read: a new entity arrives with new ends.
        store.seed(
            {
                guid: "opened",
                typeName: "m4i_data_entity",
                attributes: { name: "renamed" },
                relationshipAttributes: { attributes: [related("b1", "New")] },
            },
            LAYOUT,
        );

        before[0].flush({ entities: [resolved("a1", "gone")] }); // superseded: paints nothing
        const views = store.views();
        expect(views.find((view) => view.anchor === "related-attributes")?.cards.map((card) => card.guid)).toEqual([
            "b1",
        ]);

        flushAll(httpMock);
        expect(
            store
                .views()
                .find((view) => view.anchor === "related-attributes")
                ?.cards.map((card) => card.guid),
        ).toEqual(["b1"]);
        httpMock.verify();
    });

    it("a null entity or layout clears every section (DET-15's reset)", () => {
        const { store, httpMock } = setup();
        store.seed(opened([related("a1", "Alpha")]), LAYOUT);
        flushAll(httpMock);

        store.seed(null, undefined);
        expect(store.views()).toEqual([]);
        expect(store.countFor("related-attributes")).toBe(0);
        httpMock.verify();
    });
});

describe("The field layout's rules box (DET-35/DET-36, 7.24, DD-444)", () => {
    /** The field layout, with the DET-35 `related-rules` section. */
    const FIELD_LAYOUT = LAYOUTS.m4i_field;

    /** An opened `m4i_field` whose `dataQuality` end seeds the given rules. */
    function openedField(seed: Record<string, unknown>[]): AtlasEntity {
        return {
            guid: "field-1",
            typeName: "m4i_field",
            attributes: { name: "field-1" },
            relationshipAttributes: { dataQuality: seed },
        };
    }

    function rule(guid: string, displayText: string): Record<string, unknown> {
        return { guid, displayText, typeName: "m4i_data_quality", name: displayText };
    }

    it("seeds the rules box from the field's own dataQuality end (DET-35)", () => {
        const { store, httpMock } = setup();
        store.seed(openedField([rule("r1", "Not null"), { displayText: "No guid" }]), FIELD_LAYOUT);

        const rules = store.views().find((view) => view.anchor === "related-rules");
        expect(rules?.count).toBe(1); // the guidless end drops, as every DET-17 section
        expect(store.countFor("related-rules")).toBe(1); // the DET-36 stat's value
        // DET-37 (7.27): the view carries the layout row's create door.
        expect(rules?.createAction).toEqual({ type: "m4i_data_quality" });
        flushAll(httpMock);
        const after = store.views().find((view) => view.anchor === "related-rules");
        expect(after?.cards.map((card) => card.guid)).toEqual(["r1"]);
        httpMock.verify();
    });

    it("a field with an empty end renders the box at its zero count, no request (DET-35, DET-17's zero case)", () => {
        const { store, httpMock } = setup();
        store.seed(openedField([]), FIELD_LAYOUT);

        const rules = store.views().find((view) => view.anchor === "related-rules");
        expect(rules?.count).toBe(0);
        expect(store.countFor("related-rules")).toBe(0); // the stat reads its zero, in legacy place
        expect(bulkRequests(httpMock)).toEqual([]); // a zero view sends nothing
        httpMock.verify();
    });
});
