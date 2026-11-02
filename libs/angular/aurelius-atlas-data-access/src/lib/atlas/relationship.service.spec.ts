import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { API_BASE_URL, provideApiBaseUrl } from "../api-config";
import { atlasErrorFrom } from "./atlas-error";
import type { AtlasRelationship } from "./atlas-relationship";
import { RelationshipService } from "./relationship.service";

describe("RelationshipService", () => {
    let service: RelationshipService;
    let httpMock: HttpTestingController;

    const relationship: AtlasRelationship = {
        guid: "r-1",
        typeName: "_table_table_join",
        label: "join",
        end1: { guid: "g-1", typeName: "table" },
        end2: { guid: "g-2", typeName: "table" },
        propagateTags: "BOTH",
        status: "ACTIVE",
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        service = TestBed.inject(RelationshipService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("createRelationship posts the bare relationship and answers it back (AREL-01)", () =>
        new Promise<void>((done, fail) => {
            service.createRelationship(relationship).subscribe({
                next: (created) => {
                    expect(created).toEqual(relationship);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/relationship");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual(relationship);
            req.flush(relationship);
        }));

    it("updateRelationship puts the bare relationship and answers it back (AREL-01)", () =>
        new Promise<void>((done, fail) => {
            service.updateRelationship({ ...relationship, propagateTags: "NONE" }).subscribe({
                next: (updated) => {
                    expect(updated.propagateTags).toBe("BOTH");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/relationship");
            expect(req.request.method).toBe("PUT");
            expect(req.request.body).toEqual({ ...relationship, propagateTags: "NONE" });
            req.flush(relationship);
        }));

    it("getRelationship answers the wrapper with no referredEntities and no parameter (AREL-02)", () =>
        new Promise<void>((done, fail) => {
            const answer = { relationship };

            service.getRelationship("r-1").subscribe({
                next: (result) => {
                    expect(result.relationship).toEqual(relationship);
                    expect(result.referredEntities).toBeUndefined();
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/relationship/guid/r-1");
            expect(req.request.method).toBe("GET");
            expect(req.request.params.keys()).toEqual([]);
            req.flush(answer);
        }));

    it("getRelationship sends extendedInfo only when set, with the ends' headers (AREL-02)", () =>
        new Promise<void>((done, fail) => {
            const answer = {
                relationship,
                referredEntities: { "g-1": { guid: "g-1", typeName: "table" } },
            };

            service.getRelationship("r-1", true).subscribe({
                next: (result) => {
                    expect(result.referredEntities?.["g-1"].typeName).toBe("table");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/relationship/guid/r-1?extendedInfo=true");
            req.flush(answer);
        }));

    it("getRelationship percent-encodes the guid path segment (AREL-02, APC-01)", () =>
        new Promise<void>((done, fail) => {
            service.getRelationship("r 1/x").subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/relationship/guid/r%201%2Fx");
            req.flush({ relationship });
        }));

    it("deleteRelationship sends no parameter and answers void on 204 (AREL-03)", () =>
        new Promise<void>((done, fail) => {
            service.deleteRelationship("r-1").subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/relationship/guid/r-1");
            expect(req.request.method).toBe("DELETE");
            expect(req.request.params.keys()).toEqual([]);
            req.flush(null, { status: 204, statusText: "No Content" });
        }));

    it("deleteRelationship sends the chosen deleteType (AREL-03, EDL-04)", () =>
        new Promise<void>((done, fail) => {
            service.deleteRelationship("r-1", "HARD").subscribe({
                next: () => done(),
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/relationship/guid/r-1?deleteType=HARD");
            expect(req.request.method).toBe("DELETE");
            req.flush(null, { status: 204, statusText: "No Content" });
        }));

    it("surfaces the Atlas error body on a 4xx (AREL-02, APC-04)", () =>
        new Promise<void>((done, fail) => {
            service.getRelationship("r-nope").subscribe({
                next: fail,
                error: (error) => {
                    expect(error.status).toBe(404);
                    expect(atlasErrorFrom(error)).toEqual({
                        errorCode: "ATLAS-404-00-001",
                        errorMessage: "no relationship r-nope",
                    });
                    done();
                },
            });

            const req = httpMock.expectOne("/api/atlas/v2/relationship/guid/r-nope");
            req.flush(
                { errorCode: "ATLAS-404-00-001", errorMessage: "no relationship r-nope" },
                { status: 404, statusText: "Not Found" },
            );
        }));

    it("composes every URL from API_BASE_URL (APC-01)", () => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), provideApiBaseUrl("https://atlas:21000/api")],
        });
        const custom = TestBed.inject(RelationshipService);
        const mock = TestBed.inject(HttpTestingController);

        custom.getRelationship("r-1").subscribe();

        expect(mock.expectOne("https://atlas:21000/api/atlas/v2/relationship/guid/r-1").request.method).toBe("GET");
        mock.verify();
        expect(TestBed.inject(API_BASE_URL)).toBe("https://atlas:21000/api");
    });
});
