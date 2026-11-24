import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import type { EntityCard, EntityRelation, EntityView, RelationEntity } from "aurelius-atlas-data-access";

import { AlertsService } from "../../../alerts/alerts.service";
import { LAYOUTS } from "./section-config";
import { CHUNK_SIZE, PAGE_SIZE, RelatedSectionsState } from "./related-sections.state";

/**
 * The card-section store (DET-17..DET-22, DD-365/DD-368, VDR-03, VCF-02,
 * DD-615): the seed off the view's `sections`, the chunked resolve through
 * the search door, and the client-side filter, sort, and page. Specs ride
 * the details screen's idiom — `provideHttpClientTesting`, `expectOne` +
 * `flush`.
 */
const SEARCH_URL = "/api/aurelius/v1/search";

/** The entity layout's sections: every section of one type at once. */
const LAYOUT = LAYOUTS.m4i_data_entity;

/** A related-entity end of a view section. */
function related(guid: string, displayText: string, status?: string): Record<string, unknown> {
    return {
        guid,
        displayText,
        typeName: "m4i_data_attribute",
        name: displayText,
        ...(status === undefined ? {} : { status }),
    };
}

/**
 * One view section carrying the given ends. The fixture ends stay loose
 * (`Record<string, unknown>`) on purpose: the guidless and deleted entries
 * the DET-17 rule drops are not representable as a `RelationEntity`.
 */
function ends(attribute: string, seed: readonly Record<string, unknown>[]): EntityRelation {
    return { attribute, entities: seed as unknown as RelationEntity[] };
}

/** A resolved card for the door answer (DD-615). */
function resolved(guid: string, displayText: string, definition?: string): EntityCard {
    return {
        guid,
        typeName: "m4i_data_attribute",
        displayText,
        qualifiedName: `${displayText}@cluster`,
        status: "ACTIVE",
        stale: false,
        ...(definition === undefined ? {} : { definition }),
    };
}

/** An opened entity whose `attributes` section seeds the given ends. */
function opened(seed: Record<string, unknown>[]): EntityView {
    return {
        guid: "opened",
        typeName: "m4i_data_entity",
        displayText: "opened",
        status: "ACTIVE",
        stale: false,
        attributes: { name: "opened" },
        sections: [ends("attributes", seed)],
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

/** The door requests still in flight. */
function searchRequests(httpMock: HttpTestingController) {
    return httpMock.match((request) => request.url === SEARCH_URL && request.method === "POST");
}

/** The GUIDs one door request carries in its filter. */
function filteredGuids(request: { request: { body: unknown } }): string[] {
    const filters = (request.request.body as { filters?: { guid?: unknown } }).filters;
    return Array.isArray(filters?.guid) ? (filters.guid as string[]) : [];
}

/** Deliver every in-flight door chunk with its own guids' cards. */
function flushAll(
    httpMock: HttpTestingController,
    answer: (guids: string[]) => EntityCard[] = (guids) => guids.map((guid) => resolved(guid, `attr-${guid}`)),
) {
    for (const request of searchRequests(httpMock)) {
        const cards = answer(filteredGuids(request));
        request.flush({ cards, facets: {}, total: cards.length });
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
        searchRequests(httpMock).forEach((request) => request.flush({ cards: [], facets: {}, total: 0 }));
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

    it("resolves the seed in chunks of at most 25 through the door (DET-18, DD-368, VCF-02)", () => {
        const { store, httpMock } = setup();
        const seed = Array.from({ length: CHUNK_SIZE + 1 }, (_, index) => related(`g${index}`, `g${index}`));
        store.seed(opened(seed), LAYOUT);

        const requests = searchRequests(httpMock);
        expect(requests).toHaveLength(2); // 26 guids travel as 25 + 1
        expect(filteredGuids(requests[0])).toHaveLength(CHUNK_SIZE);
        expect(filteredGuids(requests[1])).toHaveLength(1);
        // VCF-02: the body carries the GUID filter, the limit, and no facets.
        const body = requests[0].request.body as { filters: Record<string, unknown>; limit: number; facets?: unknown };
        expect(body.limit).toBe(CHUNK_SIZE);
        expect(body.facets).toBeUndefined();
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

        searchRequests(httpMock)[0].flush({ error: "boom" }, { status: 500, statusText: "Server Error" });

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
        httpMock.expectNone(SEARCH_URL); // no retry loop
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

    it("matches the qualifiedName and the description, case-insensitively (DET-20, DD-368, VCF-05)", () => {
        const { store, httpMock } = setup();
        store.seed(opened([related("a1", "Alpha"), related("a2", "Beta")]), LAYOUT);
        flushAll(httpMock, (guids) => [
            resolved("a1", "alpha-one", "Sequencing reads"),
            { ...resolved("a2", "beta-two"), qualifiedName: "beta@warehouse" },
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
        // A resolved card's display text is the card's own `displayText`
        // (AVS-03): the sort compares those.
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
        const before = searchRequests(httpMock);

        // The editor's save re-read: a new view arrives with new ends.
        store.seed(
            {
                guid: "opened",
                typeName: "m4i_data_entity",
                displayText: "renamed",
                status: "ACTIVE",
                stale: false,
                attributes: { name: "renamed" },
                sections: [ends("attributes", [related("b1", "New")])],
            },
            LAYOUT,
        );

        before[0].flush({ cards: [resolved("a1", "gone")], facets: {}, total: 1 }); // superseded: paints nothing
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

    /** An opened `m4i_field` whose `dataQuality` section seeds the given rules. */
    function openedField(seed: Record<string, unknown>[]): EntityView {
        return {
            guid: "field-1",
            typeName: "m4i_field",
            displayText: "field-1",
            status: "ACTIVE",
            stale: false,
            attributes: { name: "field-1" },
            sections: [ends("dataQuality", seed)],
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
        expect(searchRequests(httpMock)).toEqual([]); // a zero view sends nothing
        httpMock.verify();
    });
});

describe("The person stats bar's per-end counts (DET-40, DD-519)", () => {
    /** An opened person carrying the given ends as sections under their own keys. */
    function openedPerson(seeds: Record<string, unknown[]>): EntityView {
        return {
            guid: "pe-1",
            typeName: "m4i_person",
            displayText: "Ada",
            status: "ACTIVE",
            stale: false,
            attributes: { name: "Ada" },
            sections: Object.entries(seeds).map(([attribute, seed]) =>
                ends(attribute, seed as Record<string, unknown>[]),
            ),
        };
    }

    it("counts one end on its own, by the seed rule (DET-40)", () => {
        const { store, httpMock } = setup();
        store.seed(
            openedPerson({
                domainLead: [related("d1", "Genomics"), related("d1", "Genomics"), { displayText: "No guid" }],
                stewardEntity: [related("e1", "Variants")],
            }),
            LAYOUTS.m4i_person,
        );

        // A deduped, guid-bearing, ACTIVE-only count — the section's own rule.
        expect(store.endCount("domainLead")).toBe(1); // the duplicate and guidless end drop
        expect(store.endCount("stewardEntity")).toBe(1);
        expect(store.endCount("stewardAttribute")).toBe(0); // an absent end counts nothing
        // The merged box agrees: two ends, two cards' worth of seed.
        expect(store.countFor("governance-roles")).toBe(2);
        searchRequests(httpMock).forEach((request) => request.flush({ cards: [], facets: {}, total: 0 }));
        httpMock.verify();
    });

    it("a DELETED edge counts nothing, as in a section (DET-40, EDT-15)", () => {
        const { store, httpMock } = setup();
        store.seed(
            openedPerson({
                businessOwnerEntity: [related("e1", "Live"), related("e2", "Gone", "DELETED")],
            }),
            LAYOUTS.m4i_person,
        );

        expect(store.endCount("businessOwnerEntity")).toBe(1);
        searchRequests(httpMock).forEach((request) => request.flush({ cards: [], facets: {}, total: 0 }));
        httpMock.verify();
    });

    it("the count follows the last seed: a re-seed or a clear moves it (DET-40)", () => {
        const { store, httpMock } = setup();
        store.seed(openedPerson({ domainLead: [related("d1", "Genomics")] }), LAYOUTS.m4i_person);
        expect(store.endCount("domainLead")).toBe(1);
        searchRequests(httpMock).forEach((request) => request.flush({ cards: [], facets: {}, total: 0 }));

        store.seed(openedPerson({}), LAYOUTS.m4i_person); // the save re-read's entity
        expect(store.endCount("domainLead")).toBe(0);

        store.seed(null, undefined); // no entity: no counts
        expect(store.endCount("domainLead")).toBe(0);
        httpMock.verify();
    });
});

describe("The section facet filters (VCF-09..VCF-14, VCF-18, DD-619/DD-620/DD-629)", () => {
    /** The attribute body whose Fields section seeds the given ends (its
     * section asks the System / Collection / Dataset groups, DD-619). */
    function openedAttribute(seed: Record<string, unknown>[]): EntityView {
        return {
            guid: "at-1",
            typeName: "m4i_data_attribute",
            displayText: "attribute",
            status: "ACTIVE",
            stale: false,
            attributes: { name: "attribute" },
            sections: [ends("fields", seed)],
        };
    }

    /** A door card carrying stored derived relations per attribute (AVS-02). */
    function cardWithRelations(guid: string, displayText: string, relations: Record<string, string[]>): EntityCard {
        return {
            guid,
            typeName: "m4i_field",
            displayText,
            status: "ACTIVE",
            stale: false,
            relations: Object.entries(relations).map(([attribute, names]) => ({
                attribute,
                entities: names.map((name) => ({ guid: `${attribute}-${name}`, name })),
            })),
        };
    }

    /** Bring the attribute page up with its fields resolved to the given cards. */
    function arriveFields(seed: Record<string, unknown>[], answer: (guids: string[]) => EntityCard[]) {
        const { store, httpMock } = setup();
        store.seed(openedAttribute(seed), LAYOUTS.m4i_data_attribute);
        flushAll(httpMock, answer);
        return { store, httpMock };
    }

    /** The Fields section view. */
    function fields(store: RelatedSectionsState) {
        return store.views().find((view) => view.anchor === "related-fields")!;
    }

    /** One popover group of a view, by key. */
    function group(view: ReturnType<typeof fields>, key: string) {
        return view.facets.find((facet) => facet.key === key)!;
    }

    it("rows count the resolved cards' relations, by count then label (VCF-09)", () => {
        const { store, httpMock } = arriveFields([related("f1", "one"), related("f2", "two")], (guids) =>
            guids.map((guid) =>
                guid === "f1"
                    ? cardWithRelations("f1", "one", { m4i_system: ["elastic"], m4i_dataset: ["raw_logs"] })
                    : cardWithRelations("f2", "two", { m4i_system: ["elastic", "airflow"] }),
            ),
        );

        const view = fields(store);
        // The configured groups with rows, in the layout's order (VCF-10);
        // the Collection group has no rows and leaves, as the legacy
        // FilterService dropped empty facets (SDX-03).
        expect(view.facets.map((facet) => facet.key)).toEqual(["m4i_system", "m4i_dataset"]);
        const systems = group(view, "m4i_system");
        expect(systems.title).toBe("System");
        // Count descends, then the label; a card counts a value once.
        expect(systems.items.map((row) => [row.label, row.count])).toEqual([
            ["elastic", 2],
            ["airflow", 1],
        ]);
        // The dataset group counts its own relation names.
        expect(group(view, "m4i_dataset").items.map((row) => [row.label, row.count])).toEqual([["raw_logs", 1]]);
        // Nothing selected, nothing filtered (VCF-08/VCF-13).
        expect(view.filterActive).toBe(false);
        expect(view.filtered).toBe(false);
        expect(view.countShown).toBe(2);
        httpMock.verify();
    });

    it("the facet groups ask the roles, counting the cards' role relations (VCF-18, DD-629)", () => {
        // Since 16.5f the popover asks the three role groups where 16.5e
        // carried the flat People group: each counts its role relation's
        // names (AVS-10). The flat m4i_person relation is asked nowhere —
        // a card that only carries it, still awaiting its re-derive round
        // (VCF-16), adds no people rows until the round fills the roles.
        const { store, httpMock } = setup();
        store.seed(
            {
                guid: "d-1",
                typeName: "m4i_data_domain",
                displayText: "domain",
                status: "ACTIVE",
                stale: false,
                attributes: { name: "domain" },
                sections: [ends("dataEntity", [related("e1", "one"), related("e2", "stale")])],
            },
            LAYOUTS.m4i_data_domain,
        );
        flushAll(httpMock, (guids) =>
            guids.map((guid) =>
                guid === "e1"
                    ? cardWithRelations("e1", "one", { steward: ["ada", "bob"], businessOwner: ["cid"] })
                    : cardWithRelations("e2", "stale", { m4i_person: ["dana"] }),
            ),
        );

        const view = store.views().find((section) => section.anchor === "related-entities")!;
        // Configured order (lead, owner, steward); Domain Lead has no rows and
        // leaves the popover (SDX-03), and no group is titled "People".
        expect(view.facets.map((facet) => facet.title)).toEqual(["Data Owner(s)", "Data Steward(s)"]);
        expect(group(view, "businessOwner").items.map((row) => [row.label, row.count])).toEqual([["cid", 1]]);
        expect(group(view, "steward").items.map((row) => [row.label, row.count])).toEqual([
            ["ada", 1],
            ["bob", 1],
        ]);

        // The role groups filter like any other: AND across groups, so the
        // steward's tick keeps only the card carrying both roles.
        store.toggleFacet("related-entities", "steward", "ada", true);
        store.toggleFacet("related-entities", "businessOwner", "cid", true);
        const filtered = store.views().find((section) => section.anchor === "related-entities")!;
        expect(filtered.cards.map((card) => card.guid)).toEqual(["e1"]);
        httpMock.verify();
    });

    it("the Type Name group labels the dictionary name (VCF-09, DD-622)", () => {
        const { store, httpMock } = setup();
        store.seed(
            {
                guid: "pe-1",
                typeName: "m4i_person",
                displayText: "Ada",
                status: "ACTIVE",
                stale: false,
                attributes: { name: "Ada" },
                sections: [
                    ends("domainLead", [related("e1", "variants"), related("e2", "samples"), related("a1", "gene")]),
                ],
            },
            LAYOUTS.m4i_person,
        );
        flushAll(httpMock, (guids) =>
            guids.map((guid) => ({
                guid,
                typeName: guid === "a1" ? "m4i_data_attribute" : "m4i_data_entity",
                displayText: `card-${guid}`,
                status: "ACTIVE",
                stale: false,
            })),
        );

        const roles = store.views().find((view) => view.anchor === "governance-roles")!;
        // The person box asks Type Name / Data Domain / Data Entity / Name
        // (DD-619); these cards carry no chain relations, so the two chain
        // groups have no rows and leave the popover (SDX-03).
        expect(roles.facets.map((facet) => facet.title)).toEqual(["Type Name", "Name"]);
        const typeNames = roles.facets.find((facet) => facet.key === "typeName")!;
        expect(typeNames.items.map((row) => [row.label, row.count])).toEqual([
            ["Data Entity", 2],
            ["Data Attribute", 1],
        ]);
        // The Name group counts display texts (raw, no dictionary walk).
        expect(roles.facets.find((facet) => facet.key === "name")!.items.map((row) => row.label)).toEqual([
            "card-a1",
            "card-e1",
            "card-e2",
        ]);
        httpMock.verify();
    });

    it("values OR within a group, groups AND, the keyword ANDs with all (VCF-11)", () => {
        const { store, httpMock } = arriveFields(
            [related("f1", "one"), related("f2", "two"), related("f3", "three")],
            (guids) =>
                guids.map((guid) =>
                    guid === "f1"
                        ? cardWithRelations("f1", "one", { m4i_system: ["elastic"], m4i_dataset: ["raw_logs"] })
                        : guid === "f2"
                          ? cardWithRelations("f2", "two", { m4i_system: ["airflow"], m4i_dataset: ["raw_logs"] })
                          : cardWithRelations("f3", "three", { m4i_system: ["airflow"], m4i_dataset: ["hourly"] }),
                ),
        );

        // OR within the System group: either producer keeps its card.
        store.toggleFacet("related-fields", "m4i_system", "elastic", true);
        store.toggleFacet("related-fields", "m4i_system", "airflow", true);
        expect(fields(store).cards.map((card) => card.guid)).toEqual(["f1", "f2", "f3"]);

        // AND across groups: adding a Dataset value keeps only the cards carrying both.
        store.toggleFacet("related-fields", "m4i_dataset", "raw_logs", true);
        expect(fields(store).cards.map((card) => card.guid)).toEqual(["f1", "f2"]);

        // The keyword ANDs with the selections.
        store.setQuery("related-fields", "two");
        expect(fields(store).cards.map((card) => card.guid)).toEqual(["f2"]);
        expect(fields(store).countShown).toBe(1);

        // The last untick deletes the group's key: f1 returns, then all.
        store.setQuery("related-fields", null);
        store.toggleFacet("related-fields", "m4i_dataset", "raw_logs", false);
        expect(fields(store).cards.map((card) => card.guid)).toEqual(["f1", "f2", "f3"]);
        httpMock.verify();
    });

    it("a row at zero leaves the popover, the reset returns it (VCF-12, VCF-13)", () => {
        const { store, httpMock } = arriveFields([related("f1", "one"), related("f2", "two")], (guids) =>
            guids.map((guid) =>
                guid === "f1"
                    ? cardWithRelations("f1", "one", { m4i_system: ["elastic"], m4i_dataset: ["raw_logs"] })
                    : cardWithRelations("f2", "two", { m4i_system: ["airflow"] }),
            ),
        );

        store.toggleFacet("related-fields", "m4i_system", "airflow", true);
        const view = fields(store);
        // The count line moves to the filtered number (VCF-13).
        expect(view.filtered).toBe(true);
        expect(view.countShown).toBe(1);
        expect(view.filterActive).toBe(true);
        // The dataset rows counted the whole set; f1 left, so the group's
        // last row is gone and the group leaves with it (VCF-12, SDX-03).
        expect(view.facets.find((facet) => facet.key === "m4i_dataset")).toBeUndefined();
        // The System group keeps only the surviving row, still ticked.
        expect(group(view, "m4i_system").items.map((row) => [row.label, row.count, row.checked])).toEqual([
            ["airflow", 1, true],
        ]);

        store.reset("related-fields");
        const reset = fields(store);
        expect(reset.countShown).toBe(2);
        expect(reset.filtered).toBe(false);
        expect(group(reset, "m4i_dataset").items.map((row) => row.label)).toEqual(["raw_logs"]);
        httpMock.verify();
    });

    it("a checked row drops with its zero count and the reset recovers it (VCF-12)", () => {
        const { store, httpMock } = arriveFields([related("f1", "one"), related("f2", "two")], (guids) =>
            guids.map((guid) =>
                guid === "f1"
                    ? cardWithRelations("f1", "one", { m4i_system: ["elastic"], m4i_dataset: ["raw_logs"] })
                    : cardWithRelations("f2", "two", { m4i_system: ["elastic"], m4i_dataset: ["hourly"] }),
            ),
        );

        // Tick both a System and a Dataset value no single card carries:
        // the AND empties the set, and the still-checked rows vanish with
        // their zero counts — the demo's measured behaviour.
        store.toggleFacet("related-fields", "m4i_dataset", "raw_logs", true);
        store.toggleFacet("related-fields", "m4i_dataset", "hourly", true);
        store.toggleFacet("related-fields", "m4i_system", "airflow", true);
        const view = fields(store);
        expect(view.cards).toEqual([]);
        expect(view.countShown).toBe(0);
        // Every row fell to zero, so every group left: the popover carries
        // the empty set (the part renders the not-available line, VCF-10).
        expect(view.facets).toEqual([]);

        store.reset("related-fields");
        expect(fields(store).cards.map((card) => card.guid)).toEqual(["f1", "f2"]);
        httpMock.verify();
    });

    it("an unresolved card hides while a selection is active (VCF-14, DD-621)", () => {
        const { store, httpMock } = setup();
        // 26 seeds: two chunks, so one can answer while one stays pending.
        const seed = Array.from({ length: 26 }, (_, index) => related(`f${index}`, `field-${index}`));
        store.seed(openedAttribute(seed), LAYOUTS.m4i_data_attribute);

        // No selection: the loading rows show (DET-18) — one page of them.
        expect(fields(store).cards.every((card) => card.kind === "loading")).toBe(true);

        // Answer the first chunk only, then tick its value: the pending
        // card hides — its values cannot be tested (DD-621). `match`
        // consumes both chunk requests, so both arrive here.
        const [first, second] = searchRequests(httpMock);
        first!.flush({
            cards: seed.slice(0, 25).map((entry) =>
                cardWithRelations(entry["guid"] as string, entry["displayText"] as string, {
                    m4i_system: ["elastic"],
                }),
            ),
            facets: {},
            total: 25,
        });
        store.toggleFacet("related-fields", "m4i_system", "elastic", true);
        const view = fields(store);
        expect(view.cards.every((card) => card.kind === "card")).toBe(true); // the pending card is out of the page
        expect(view.count).toBe(26); // the seed count keeps the unknown entry
        expect(view.countShown).toBe(25); // the filtered set is the resolved five-and-ten

        // When the last card answers and matches, it joins (DD-619's rows
        // settle as the cards arrive).
        second!.flush({
            cards: [cardWithRelations("f25", "field-25", { m4i_system: ["elastic"] })],
            facets: {},
            total: 1,
        });
        expect(fields(store).countShown).toBe(26);
        httpMock.verify();
    });

    it("the reset clears keyword, selections, and sort together (VCF-13)", () => {
        const { store, httpMock } = arriveFields([related("f1", "one"), related("f2", "two")], (guids) =>
            guids.map((guid) => cardWithRelations(guid, `name-${guid}`, { m4i_system: ["elastic"] })),
        );

        store.setQuery("related-fields", "one");
        store.toggleFacet("related-fields", "m4i_system", "elastic", true);
        store.setSort("related-fields", "name");
        store.toggleDirection("related-fields");
        expect(fields(store).filtered).toBe(true);

        store.reset("related-fields");
        const view = fields(store);
        expect(view.query).toBeNull();
        expect(view.sort).toBe("relevance");
        expect(view.descending).toBe(false);
        expect(view.cards.map((card) => card.guid)).toEqual(["f1", "f2"]);
        // The tick is gone from the rows too.
        expect(group(view, "m4i_system").items.every((row) => !row.checked)).toBe(true);
        httpMock.verify();
    });

    it("a sort or direction away from its default marks the funnel (VCF-08, DV-169)", () => {
        const { store, httpMock } = arriveFields([related("f1", "one"), related("f2", "two")], (guids) =>
            guids.map((guid) => cardWithRelations(guid, `name-${guid}`, { m4i_system: ["elastic"] })),
        );

        // The default state: the funnel is unmarked and the count line reads the seed.
        expect(fields(store).filterActive).toBe(false);
        expect(fields(store).filtered).toBe(false);

        // A re-picked sort marks the funnel — the legacy query-object test —
        // but leaves the count line on the seed count (sort filters nothing).
        store.setSort("related-fields", "name");
        expect(fields(store).filterActive).toBe(true);
        expect(fields(store).filtered).toBe(false);

        // The default sort with the direction flipped still marks it, and
        // back to relevance with the direction down marks it too.
        store.setSort("related-fields", "relevance");
        store.toggleDirection("related-fields");
        expect(fields(store).filterActive).toBe(true);

        // Relevance, ascending — the whole default object — clears the mark.
        store.reset("related-fields");
        expect(fields(store).filterActive).toBe(false);
        httpMock.verify();
    });

    it("a section with no groups renders the empty popover set (VCF-10)", () => {
        const { store, httpMock } = setup();
        store.seed(openedAttribute([related("f1", "one")]), LAYOUTS.m4i_data_quality); // the rule page's box asked none

        expect(fields(store).facets).toEqual([]);
        searchRequests(httpMock).forEach((request) => request.flush({ cards: [], facets: {}, total: 0 }));
        httpMock.verify();
    });

    // 7.25b (DET-53, DD-848): the governance rule's two verdict boxes ride
    // this store — the screen hands it the verdict GUIDs per anchor and
    // every rule below (chunked resolve, page of nine, failed chunk,
    // deleted guid) is this store's unchanged.
    describe("the verdict boxes of the rule page (DET-53, DD-848)", () => {
        /** The rule's own layout — the two verdict boxes, no ends. */
        const RULE_LAYOUT = LAYOUTS.m4i_gov_data_quality;

        /** The opened rule: no sections, since its boxes seed from verdicts. */
        const openedRule = (): EntityView => ({
            guid: "rule-1",
            typeName: "m4i_gov_data_quality",
            displayText: "Name filled",
            status: "ACTIVE",
            stale: false,
            attributes: { name: "Name filled" },
        });

        /** The verdict GUIDs of both boxes, in door order. */
        const verdictGuids = (nonCompliant: readonly string[], compliant: readonly string[]) => ({
            "related-non-compliants": nonCompliant,
            "related-compliants": compliant,
        });

        it("seeds the two anchors from the screen's GUIDs, in door order (DET-53)", () => {
            const { store, httpMock } = setup();
            store.seed(openedRule(), RULE_LAYOUT, verdictGuids(["e-1", "e-2"], ["e-3"]));

            const nonCompliant = store.views().find((view) => view.anchor === "related-non-compliants");
            expect(nonCompliant?.count).toBe(2);
            expect(nonCompliant?.cards.map((card) => card.guid)).toEqual(["e-1", "e-2"]);
            expect(store.countFor("related-non-compliants")).toBe(2); // DET-52's stat
            const compliant = store.views().find((view) => view.anchor === "related-compliants");
            expect(compliant?.count).toBe(1);
            // The display text starts as the guid and the card replaces it.
            expect(nonCompliant?.cards.map((card) => card.displayText)).toEqual(["e-1", "e-2"]);
            flushAll(httpMock, (guids) => guids.map((guid) => resolved(guid, `ds-${guid}`)));
            expect(
                store
                    .views()
                    .find((view) => view.anchor === "related-non-compliants")
                    ?.cards.map((card) => card.displayText),
            ).toEqual(["ds-e-1", "ds-e-2"]);
            httpMock.verify();
        });

        it("seeds a verdict box empty when the screen names no GUIDs for it (DET-53)", () => {
            const { store, httpMock } = setup();
            store.seed(openedRule(), RULE_LAYOUT, verdictGuids([], ["e-3"]));

            expect(store.countFor("related-non-compliants")).toBe(0);
            expect(store.views().find((view) => view.anchor === "related-non-compliants")?.cards).toEqual([]);
            // Only the compliant box travels.
            const requests = searchRequests(httpMock);
            expect(requests).toHaveLength(1);
            expect(filteredGuids(requests[0])).toEqual(["e-3"]);
            flushAll(httpMock);
            httpMock.verify();
        });

        it("resolves the verdict GUIDs in chunks of at most 25 (DET-53, DET-18)", () => {
            const { store, httpMock } = setup();
            const guids = Array.from({ length: CHUNK_SIZE + 3 }, (_, index) => `e-${index}`);
            store.seed(openedRule(), RULE_LAYOUT, verdictGuids(guids, []));

            const requests = searchRequests(httpMock);
            expect(requests).toHaveLength(2); // 28 guids travel as 25 + 3
            expect(filteredGuids(requests[0])).toHaveLength(CHUNK_SIZE);
            expect(filteredGuids(requests[1])).toHaveLength(3);
            flushAll(httpMock);
            expect(store.countFor("related-non-compliants")).toBe(CHUNK_SIZE + 3);
            httpMock.verify();
        });

        it("drops a verdict box's duplicate GUID once (DET-53)", () => {
            const { store, httpMock } = setup();
            // One entity judged twice by a re-run leaves one card, as every
            // seed rule does (DET-17's dedupe).
            store.seed(openedRule(), RULE_LAYOUT, verdictGuids(["e-1", "e-1", "e-2"], []));

            expect(store.countFor("related-non-compliants")).toBe(2);
            const requests = searchRequests(httpMock);
            expect(requests).toHaveLength(1);
            expect(filteredGuids(requests[0])).toEqual(["e-1", "e-2"]);
            flushAll(httpMock);
            httpMock.verify();
        });

        it("a failed verdict chunk drops its cards with one alert and keeps the count (DET-53, DET-18)", () => {
            const { store, httpMock } = setup();
            const add = vi.spyOn(TestBed.inject(AlertsService), "add");
            store.seed(openedRule(), RULE_LAYOUT, verdictGuids(["e-1", "e-2"], []));

            searchRequests(httpMock)[0].flush({ error: "boom" }, { status: 500, statusText: "Server Error" });

            const view = store.views().find((section) => section.anchor === "related-non-compliants");
            expect(view?.count).toBe(2); // the count keeps the dropped cards
            expect(view?.cards).toHaveLength(0);
            expect(view?.loading).toBe(false);
            expect(add).toHaveBeenCalledTimes(1);
            httpMock.expectNone(SEARCH_URL); // no retry loop
        });

        it("a verdict GUID the answer omits is a deleted entity: no card, the count keeps it (DET-53, DET-18)", () => {
            const { store, httpMock } = setup();
            const add = vi.spyOn(TestBed.inject(AlertsService), "add");
            store.seed(openedRule(), RULE_LAYOUT, verdictGuids(["e-1", "e-2"], []));

            flushAll(httpMock, (guids) => guids.slice(0, 1).map((guid) => resolved(guid, `ds-${guid}`)));

            const view = store.views().find((section) => section.anchor === "related-non-compliants");
            expect(view?.count).toBe(2);
            expect(view?.cards.map((card) => card.guid)).toEqual(["e-1"]);
            expect(add).not.toHaveBeenCalled();
            httpMock.verify();
        });

        it("pages the verdict cards at nine and extends on scroll (DET-53, DET-22)", () => {
            const { store, httpMock } = setup();
            const guids = Array.from({ length: PAGE_SIZE + 2 }, (_, index) => `e-${index}`);
            store.seed(openedRule(), RULE_LAYOUT, verdictGuids(guids, []));
            flushAll(httpMock);

            const view = store.views().find((section) => section.anchor === "related-non-compliants");
            expect(view?.cards).toHaveLength(PAGE_SIZE);
            store.nextPage("related-non-compliants");
            expect(store.views().find((section) => section.anchor === "related-non-compliants")?.cards).toHaveLength(
                PAGE_SIZE + 2,
            );
            httpMock.verify();
        });
    });
});
