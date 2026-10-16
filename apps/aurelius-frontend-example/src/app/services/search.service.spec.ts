import { TestBed } from "@angular/core/testing";
import { EntitiesService, Entity, Envelope, PaginatedResponse } from "aurelius-data-access";
import { of, Subject, throwError } from "rxjs";
import { SEARCH_SERVICE_DEBOUNCE_MS, SearchService } from "./search.service";

describe("SearchService", () => {
    let service: SearchService;
    let entitiesService: EntitiesService;
    let entitiesSubject: Subject<Envelope<Entity>>;

    /**
     * Time to advance the fake clock by, enough for the debounced search
     * (SEARCH_SERVICE_DEBOUNCE_MS = 25) and change-detection microtasks to run.
     */
    const FLUSH_MS = 100;

    beforeEach(() => {
        entitiesSubject = new Subject<Envelope<Entity>>();
        TestBed.configureTestingModule({
            providers: [
                SearchService,
                {
                    provide: EntitiesService,
                    useValue: {
                        findAll: vi.fn().mockReturnValue(of({ total: 0, data: [] } as PaginatedResponse<Entity>)),
                        entities$: entitiesSubject,
                    },
                },
                { provide: SEARCH_SERVICE_DEBOUNCE_MS, useValue: 25 },
            ],
        });
        // Install the fake clock before constructing the service so its startup (debounced) findAll call
        // is frozen until the test advances time, where it merges with the test's own trigger. Previously
        // the 25 ms debounce, the 100 ms assertion timers and the 200 ms test timeout all raced on the
        // real wall clock, which flaked on loaded CI runners.
        vi.useFakeTimers();
        service = TestBed.inject(SearchService);
        entitiesService = TestBed.inject(EntitiesService);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("should be created", () => {
        expect(service).toBeTruthy();
    });

    it("should trigger refresh and call findAll", async () => {
        const response: PaginatedResponse<Entity> = {
            data: [{ guid: "1", name: "A", description: "desc" }],
            total: 1,
        };

        vi.spyOn(entitiesService, "findAll").mockReturnValueOnce(of(response));

        service.refresh();

        await vi.advanceTimersByTimeAsync(FLUSH_MS);

        expect(entitiesService.findAll).toHaveBeenCalledWith({
            search: service.query(),
            limit: service.pageSize(),
            skip: service.pageIndex() * service.pageSize(),
        });
        expect(service.entities()).toEqual(response);
    });

    it("should update query and trigger search", async () => {
        const response: PaginatedResponse<Entity> = {
            data: [{ guid: "2", name: "B", description: "desc2" }],
            total: 1,
        };

        vi.spyOn(entitiesService, "findAll").mockReturnValueOnce(of(response));

        service.query.set("B");

        await vi.advanceTimersByTimeAsync(FLUSH_MS);

        expect(entitiesService.findAll).toHaveBeenCalledWith({
            search: service.query(),
            limit: service.pageSize(),
            skip: service.pageIndex() * service.pageSize(),
        });
        expect(service.entities()).toEqual(response);
    });

    it("should update pageIndex and trigger search", async () => {
        const response: PaginatedResponse<Entity> = {
            data: [{ guid: "2", name: "B", description: "desc2" }],
            total: 1,
        };

        vi.spyOn(entitiesService, "findAll").mockReturnValueOnce(of(response));

        service.pageIndex.set(1);

        await vi.advanceTimersByTimeAsync(FLUSH_MS);

        expect(entitiesService.findAll).toHaveBeenCalledWith({
            search: service.query(),
            limit: service.pageSize(),
            skip: service.pageIndex() * service.pageSize(),
        });
        expect(service.entities()).toEqual(response);
    });

    it("should update pageSize and trigger search", async () => {
        const response: PaginatedResponse<Entity> = {
            data: [{ guid: "2", name: "B", description: "desc2" }],
            total: 1,
        };

        vi.spyOn(entitiesService, "findAll").mockReturnValueOnce(of(response));

        service.pageSize.set(10);

        await vi.advanceTimersByTimeAsync(FLUSH_MS);

        expect(entitiesService.findAll).toHaveBeenCalledWith({
            search: service.query(),
            limit: service.pageSize(),
            skip: service.pageIndex() * service.pageSize(),
        });
        expect(service.entities()).toEqual(response);
    });

    it("should debounce rapid queries", async () => {
        const response: PaginatedResponse<Entity> = {
            data: [{ guid: "3", name: "C", description: "desc3" }],
            total: 1,
        };

        vi.spyOn(entitiesService, "findAll").mockReturnValue(of(response));

        service.query.set("C1");
        service.query.set("C2");
        service.query.set("C3");

        await vi.advanceTimersByTimeAsync(FLUSH_MS);

        expect(entitiesService.findAll).toHaveBeenCalledTimes(1);
        expect(service.entities()).toEqual(response);
    });

    it("should handle error from findAll", async () => {
        const err = new Error("fail");

        vi.spyOn(entitiesService, "findAll").mockReturnValueOnce(throwError(() => err));

        service.refresh();

        await vi.advanceTimersByTimeAsync(FLUSH_MS);

        expect(service.error()).toBe(err);
        expect(service.entities()).toEqual({ data: [], total: 0 });
    });

    it("should trigger refresh when entities$ emits an event", async () => {
        const refreshSpy = vi.spyOn(service, "refresh");

        // Simulate an entity update event from the server
        entitiesSubject.next({
            guid: "4",
            op: "INSERT",
            timestamp: new Date().toISOString(),
            value: {
                guid: "4",
                name: "D",
                description: "desc4",
                time_created: new Date().toISOString(),
                time_modified: new Date().toISOString(),
            },
        });

        await vi.advanceTimersByTimeAsync(FLUSH_MS);

        expect(refreshSpy).toHaveBeenCalledOnce();
    });
});
