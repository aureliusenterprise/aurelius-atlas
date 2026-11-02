import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { provideApiBaseUrl } from "../api-config";
import { AtlasEntitiesService } from "./atlas-entities.service";
import type { EntityAuditEventV2 } from "./atlas-audit";
import type {
    AtlasClassification,
    AtlasClassifications,
    AtlasEntitiesWithExtInfo,
    AtlasEntityWithExtInfo,
} from "./atlas-entity";
import type { BulkImportResponse } from "./atlas-impexp";
import type { EntityMutationResponse } from "./atlas-mutation";
import type { AtlasEntityHeader, AtlasEntityHeaders } from "./atlas-search";

/**
 * The entity-by-GUID read, asserted on the wire (DET-03, DD-187): the
 * request (method, path, encoding, the APC-01 base url) and the DTO mapping.
 * The endpoint is server 2.3's surface — today it answers 404, so every
 * scenario here is an `expectOne` plus a synthetic `flush`: honest against
 * the wire format, not a claim that the server speaks it yet.
 */
describe("AtlasEntitiesService (DET-03)", () => {
    let service: AtlasEntitiesService;
    let httpMock: HttpTestingController;

    const read: AtlasEntityWithExtInfo = {
        entity: {
            guid: "7a1b",
            typeName: "sales_table",
            status: "ACTIVE",
            attributes: { name: "orders", qualifiedName: "s1.table.orders" },
            classificationNames: ["PII"],
            relationshipAttributes: { meanings: { termNames: ["G1"], meaning: [{ guid: "t1", displayText: "G1" }] } },
        },
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting(), provideApiBaseUrl("/api")],
        });
        service = TestBed.inject(AtlasEntitiesService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("getEntityByGuid calls GET /api/atlas/v2/entity/guid/{guid} (DET-03, APC-01)", () =>
        new Promise<void>((done, fail) => {
            service.getEntityByGuid("7a1b").subscribe({
                next: (result) => {
                    // The DTO maps through untouched — the client is the wire shape.
                    expect(result).toEqual(read);
                    expect(result.entity?.attributes?.["qualifiedName"]).toBe("s1.table.orders");
                    expect(result.entity?.relationshipAttributes?.meanings?.meaning?.[0]?.displayText).toBe("G1");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b");
            expect(req.request.method).toBe("GET");
            expect(req.request.params.keys()).toEqual([]);
            req.flush(read);
        }));

    it("URL-encodes the guid (DET-03, the typedefs lookups' idiom)", () => {
        service.getEntityByGuid("a b/c?d").subscribe();

        // Angular encodes the remaining reserved characters of the path.
        const req = httpMock.expectOne((r) => r.url.includes("entity/guid/"));
        expect(req.request.url).toBe("/api/atlas/v2/entity/guid/a%20b%2Fc%3Fd");
        req.flush({});
    });

    it("composes from the injected API_BASE_URL, not a hard-coded host (APC-01, DD-188)", () => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            providers: [
                provideHttpClient(),
                provideHttpClientTesting(),
                provideApiBaseUrl("https://catalogue.example/gw"),
            ],
        });
        TestBed.inject(AtlasEntitiesService).getEntityByGuid("g1").subscribe();

        TestBed.inject(HttpTestingController)
            .expectOne("https://catalogue.example/gw/atlas/v2/entity/guid/g1")
            .flush({});
    });

    it("surfaces the Atlas error body on a 404, honest against today's server (APC-04, DD-187)", () => {
        let status = 0;
        service.getEntityByGuid("missing").subscribe({
            error: (error) => {
                status = error.status;
            },
        });

        // Today's server (admin, types) has no entity endpoint: 404, and the
        // client keeps the status — it does not swallow it.
        httpMock
            .expectOne("/api/atlas/v2/entity/guid/missing")
            .flush(
                { errorCode: "ATLAS-404-00-002", errorMessage: "entity not found" },
                { status: 404, statusText: "Not Found" },
            );
        expect(status).toBe(404);
    });

    // ---- 8.17: the remaining reads and the audits (AEN-01..AEN-06) ----

    it("getEntityByGuid sends the flags only when true (AEN-01)", () => {
        service.getEntityByGuid("7a1b", true, true).subscribe();

        // request.url excludes the query string: match the path, check params below.
        const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/guid/7a1b");
        expect(req.request.params.get("minExtInfo")).toBe("true");
        expect(req.request.params.get("ignoreRelationships")).toBe("true");
        req.flush({});
    });

    it("getEntityHeaderByGuid calls GET …/guid/{guid}/header with no params (AEN-02, ERD-07)", () =>
        new Promise<void>((done, fail) => {
            const header: AtlasEntityHeader = { guid: "7a1b", typeName: "sales_table", displayText: "orders" };
            service.getEntityHeaderByGuid("7a1b").subscribe({
                next: (result) => {
                    expect(result).toEqual(header);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/header");
            expect(req.request.method).toBe("GET");
            expect(req.request.params.keys()).toEqual([]);
            req.flush(header);
        }));

    it("getEntityByUniqueAttributes sends attr:<name> params (AEN-03, ERD-08)", () => {
        service
            .getEntityByUniqueAttributes("sales_table", { qualifiedName: "s1.table.orders" }, true, false)
            .subscribe();

        const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table");
        expect(req.request.params.get("attr:qualifiedName")).toBe("s1.table.orders");
        expect(req.request.params.get("minExtInfo")).toBe("true");
        expect(req.request.params.get("ignoreRelationships")).toBe(null);
        req.flush({});
    });

    it("getEntityHeaderByUniqueAttributes calls the /header sibling with attr: params (AEN-02)", () => {
        service.getEntityHeaderByUniqueAttributes("sales_table", { qualifiedName: "s1.table.orders" }).subscribe();

        const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table/header");
        expect(req.request.params.get("attr:qualifiedName")).toBe("s1.table.orders");
        req.flush({});
    });

    it("getEntitiesByGuids sends a repeated guid param in order (AEN-04, ERD-01)", () => {
        service.getEntitiesByGuids(["g1", "g2", "g3"]).subscribe();

        const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/bulk");
        expect(req.request.params.getAll("guid")).toEqual(["g1", "g2", "g3"]);
        req.flush({ entities: [] });
    });

    it("getEntitiesByUniqueAttributes numbers attr_<n>: 1-based, in order (AEN-04, DV-19)", () => {
        service
            .getEntitiesByUniqueAttributes("sales_table", [{ qualifiedName: "a" }, { qualifiedName: "b" }])
            .subscribe();

        const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/bulk/uniqueAttribute/type/sales_table");
        expect(req.request.params.get("attr_1:qualifiedName")).toBe("a");
        expect(req.request.params.get("attr_2:qualifiedName")).toBe("b");
        req.flush({ entities: [] });
    });

    it("getAuditEvents calls GET /{guid}/audit and answers a list (AEN-05, AUD-06)", () =>
        new Promise<void>((done, fail) => {
            const events: EntityAuditEventV2[] = [
                { entityId: "7a1b", action: "ENTITY_CREATE", user: "alice", timestamp: 1_700_000_000_000 },
            ];
            service
                .getAuditEvents("7a1b", { auditAction: "ENTITY_CREATE", count: 10, offset: 0, sortOrder: "desc" })
                .subscribe({
                    next: (result) => {
                        expect(result).toEqual(events);
                        done();
                    },
                    error: fail,
                });

            const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/7a1b/audit");
            expect(req.request.params.get("auditAction")).toBe("ENTITY_CREATE");
            expect(req.request.params.get("count")).toBe("10");
            expect(req.request.params.get("offset")).toBe("0");
            expect(req.request.params.get("sortOrder")).toBe("desc");
            expect(req.request.params.get("startKey")).toBe(null);
            req.flush(events);
        }));

    it("getAuditEvents sends no params when the query is empty (AEN-05)", () => {
        service.getAuditEvents("7a1b").subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/entity/7a1b/audit");
        expect(req.request.params.keys()).toEqual([]);
        req.flush([]);
    });

    it("getAuditEvents lets a given count of 0 travel (AEN-05, CLE-10)", () => {
        service.getAuditEvents("7a1b", { count: 0 }).subscribe();

        // The one case the lib's default-absence habit would silently drop:
        // a count of 0 is a choice, not a default.
        const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/7a1b/audit");
        expect(req.request.params.get("count")).toBe("0");
        req.flush([]);
    });

    it("getChangedClassifications sends tagUpdateStartTime (AEN-06, CAU-07)", () =>
        new Promise<void>((done, fail) => {
            const answer: AtlasEntityHeaders = { guidHeaderMap: { g1: { guid: "g1", typeName: "t" } } };
            service.getChangedClassifications(1_700_000_000_000).subscribe({
                next: (result) => {
                    expect(result).toEqual(answer);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/bulk/headers");
            expect(req.request.params.get("tagUpdateStartTime")).toBe("1700000000000");
            req.flush(answer);
        }));

    // ---- 8.18: the writes and the deletes (AEW-01..AEW-05) ----

    it("createOrUpdateEntity posts the bare body and answers the mutation response (AEW-01, EWR-02)", () =>
        new Promise<void>((done, fail) => {
            const answer: EntityMutationResponse = {
                mutatedEntities: { CREATE: [{ guid: "g1", typeName: "sales_table" }] },
                guidAssignments: { "-1": "g1" },
            };
            service
                .createOrUpdateEntity({ entity: { guid: "-1", typeName: "sales_table", attributes: {} } })
                .subscribe({
                    next: (result) => {
                        expect(result).toEqual(answer);
                        done();
                    },
                    error: fail,
                });

            const req = httpMock.expectOne("/api/atlas/v2/entity");
            expect(req.request.method).toBe("POST");
            expect(req.request.body).toEqual({ entity: { guid: "-1", typeName: "sales_table", attributes: {} } });
            req.flush(answer);
        }));

    it("createOrUpdateEntities posts the bulk body to /bulk (AEW-02, EWR-02)", () => {
        service
            .createOrUpdateEntities({
                entities: [
                    { guid: "g1", typeName: "t" },
                    { guid: "g2", typeName: "t" },
                ],
            })
            .subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/entity/bulk");
        expect(req.request.method).toBe("POST");
        expect((req.request.body as AtlasEntitiesWithExtInfo).entities?.length).toBe(2);
        req.flush({});
    });

    it("partialUpdateAttribute PUTs the bare value; name travels only when given (AEW-03, EWR-15)", () => {
        service.partialUpdateAttribute("7a1b", "orders", "name").subscribe();

        const named = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/guid/7a1b");
        expect(named.request.method).toBe("PUT");
        expect(named.request.body).toBe("orders");
        expect(named.request.params.get("name")).toBe("name");
        named.flush({});

        service.partialUpdateAttribute("7a1b", 42).subscribe();

        const unnamed = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/guid/7a1b");
        expect(unnamed.request.body).toBe(42);
        expect(unnamed.request.params.keys()).toEqual([]);
        unnamed.flush({});
    });

    it("partialUpdateByUniqueAttributes PUTs the sparse body with attr: params (AEW-04, EWR-14)", () => {
        service
            .partialUpdateByUniqueAttributes(
                "sales_table",
                { qualifiedName: "s1.t.o" },
                { entity: { guid: "g1", typeName: "sales_table", attributes: { description: "d" } } },
            )
            .subscribe();

        const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table");
        expect(req.request.method).toBe("PUT");
        expect(req.request.params.get("attr:qualifiedName")).toBe("s1.t.o");
        expect((req.request.body as AtlasEntityWithExtInfo).entity?.attributes?.["description"]).toBe("d");
        req.flush({});
    });

    it("deleteEntityByGuid sends deleteType only when given (AEW-05, EDL-01, EDL-04)", () => {
        service.deleteEntityByGuid("7a1b").subscribe();

        const plain = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b");
        expect(plain.request.method).toBe("DELETE");
        expect(plain.request.params.keys()).toEqual([]);
        plain.flush({});

        service.deleteEntityByGuid("7a1b", "HARD").subscribe();

        const hard = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/guid/7a1b");
        expect(hard.request.params.get("deleteType")).toBe("HARD");
        hard.flush({});
    });

    it("deleteEntitiesByGuids sends repeated guid params plus optional deleteType (AEW-05, EDL-02)", () => {
        service.deleteEntitiesByGuids(["g1", "g2"], "SOFT").subscribe();

        const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/bulk");
        expect(req.request.method).toBe("DELETE");
        expect(req.request.params.getAll("guid")).toEqual(["g1", "g2"]);
        expect(req.request.params.get("deleteType")).toBe("SOFT");
        req.flush({});
    });

    it("deleteEntityByUniqueAttributes sends attr: params and optional deleteType (AEW-05, EDL-02)", () => {
        service.deleteEntityByUniqueAttributes("sales_table", { qualifiedName: "s1.t.o" }, "HARD").subscribe();

        const req = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table");
        expect(req.request.method).toBe("DELETE");
        expect(req.request.params.get("attr:qualifiedName")).toBe("s1.t.o");
        expect(req.request.params.get("deleteType")).toBe("HARD");
        req.flush({});
    });

    // ---- 8.19: classifications, business metadata, labels (ACL-01..ACL-09) ----

    it("getClassification reads one classification (ACL-01, CLS-03)", () => {
        const cls: AtlasClassification = { typeName: "PII", entityGuid: "7a1b", propagate: true };
        service.getClassification("7a1b", "PII").subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/classification/PII");
        expect(req.request.method).toBe("GET");
        req.flush(cls);
    });

    it("getClassifications reads the PList (ACL-01, CLS-03)", () => {
        const page: AtlasClassifications = { list: [{ typeName: "PII" }], totalCount: 1, pageSize: 1 };
        service.getClassifications("7a1b").subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/classifications");
        expect(req.request.params.keys()).toEqual([]);
        req.flush(page);
    });

    it("addClassifications posts the bare array; PUT changes them (ACL-02, CLS-04/08)", () => {
        service.addClassifications("7a1b", [{ typeName: "PII" }, { typeName: "CONF" }]).subscribe();

        const post = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/classifications");
        expect(post.request.method).toBe("POST");
        expect(post.request.body).toEqual([{ typeName: "PII" }, { typeName: "CONF" }]);
        post.flush({});

        service.updateClassifications("7a1b", [{ typeName: "PII", propagate: false }]).subscribe();

        const put = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/classifications");
        expect(put.request.method).toBe("PUT");
        expect(put.request.body).toEqual([{ typeName: "PII", propagate: false }]);
        put.flush({});
    });

    it("addClassificationsByUniqueAttributes sends attr: params (ACL-02, CLS-06)", () => {
        service
            .addClassificationsByUniqueAttributes("sales_table", { qualifiedName: "s1.t.o" }, [{ typeName: "PII" }])
            .subscribe();

        const req = httpMock.expectOne(
            (r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table/classifications",
        );
        expect(req.request.method).toBe("POST");
        expect(req.request.params.get("attr:qualifiedName")).toBe("s1.t.o");
        expect(req.request.body).toEqual([{ typeName: "PII" }]);
        req.flush({});

        service
            .updateClassificationsByUniqueAttributes("sales_table", { qualifiedName: "s1.t.o" }, [
                { typeName: "PII", propagate: false },
            ])
            .subscribe();

        const put = httpMock.expectOne(
            (r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table/classifications",
        );
        expect(put.request.method).toBe("PUT");
        expect(put.request.params.get("attr:qualifiedName")).toBe("s1.t.o");
        put.flush({});
    });

    it("deleteClassification sends associatedEntityGuid only when given (ACL-03, CLS-09)", () => {
        service.deleteClassification("7a1b", "PII").subscribe();

        const plain = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/classification/PII");
        expect(plain.request.method).toBe("DELETE");
        expect(plain.request.params.keys()).toEqual([]);
        plain.flush({});

        service.deleteClassification("7a1b", "PII", "g-src").subscribe();

        const assoc = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/guid/7a1b/classification/PII");
        expect(assoc.request.params.get("associatedEntityGuid")).toBe("g-src");
        assoc.flush({});
    });

    it("deleteClassificationByUniqueAttributes sends attr: params (ACL-03, CLS-06)", () => {
        service.deleteClassificationByUniqueAttributes("sales_table", { qualifiedName: "s1.t.o" }, "PII").subscribe();

        const req = httpMock.expectOne(
            (r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table/classification/PII",
        );
        expect(req.request.method).toBe("DELETE");
        expect(req.request.params.get("attr:qualifiedName")).toBe("s1.t.o");
        req.flush({});
    });

    it("associateClassification posts the request whole (ACL-04, CLS-07)", () => {
        const request = { classification: { typeName: "PII" }, entityGuids: ["g1", "g2"] };
        service.associateClassification(request).subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/entity/bulk/classification");
        expect(req.request.method).toBe("POST");
        expect(req.request.body).toEqual(request);
        req.flush({});
    });

    it("setClassifications posts the headers and answers the summary array (ACL-05, CLA-04, DV-36)", () => {
        service.setClassifications({ guidHeaderMap: { g1: {} } }).subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/entity/bulk/setClassifications");
        expect(req.request.method).toBe("POST");
        expect(req.request.body).toEqual({ guidHeaderMap: { g1: {} } });
        req.flush([{ guid: "g1", success: true }]);
    });

    it("addOrUpdateBusinessMetadata sends the {bm: attrs} map; isOverwrite only when true (ACL-06, BMD-01)", () => {
        const attrs = { domain: { "domain-name": "Sales" }, owner: null };
        service.addOrUpdateBusinessMetadata("7a1b", attrs).subscribe();

        const plain = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/businessmetadata");
        expect(plain.request.method).toBe("POST");
        expect(plain.request.body).toEqual(attrs);
        expect(plain.request.params.keys()).toEqual([]);
        plain.flush({});

        service.addOrUpdateBusinessMetadata("7a1b", attrs, true).subscribe();

        const over = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/guid/7a1b/businessmetadata");
        expect(over.request.params.get("isOverwrite")).toBe("true");
        over.flush({});
    });

    it("removeBusinessMetadata sends a DELETE with a body via request() (ACL-06, BMD-05)", () => {
        const attrs = { domain: { "domain-name": "Sales" } };
        service.removeBusinessMetadata("7a1b", attrs).subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/businessmetadata");
        expect(req.request.method).toBe("DELETE");
        expect(req.request.body).toEqual(attrs);
        req.flush({});
    });

    it("the …Of business-metadata pair sends the bare attribute map (ACL-06, BMD-03/05)", () => {
        service.addOrUpdateBusinessMetadataOf("7a1b", "domain", { "domain-name": "Sales" }).subscribe();

        const post = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/businessmetadata/domain");
        expect(post.request.method).toBe("POST");
        expect(post.request.body).toEqual({ "domain-name": "Sales" });
        post.flush({});

        service.removeBusinessMetadataOf("7a1b", "domain", { "domain-name": null }).subscribe();

        const del = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/businessmetadata/domain");
        expect(del.request.method).toBe("DELETE");
        expect(del.request.body).toEqual({ "domain-name": null });
        del.flush({});
    });

    it("businessMetadataTemplate answers the bytes pair (ACL-07, BMI-01, DD-315)", () =>
        new Promise<void>((done, fail) => {
            const csv = new ArrayBuffer(3);
            new Uint8Array(csv).set([0x61, 0x62, 0x63]);

            service.businessMetadataTemplate().subscribe({
                next: (answer) => {
                    expect(answer.body).toEqual(csv);
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/entity/businessmetadata/import/template");
            expect(req.request.method).toBe("GET");
            req.flush(csv, { headers: { "content-type": "application/octet-stream" } });
        }));

    it("importBusinessMetadata posts the file part and answers the bulk response (ACL-07, BMI-02, CLE-09)", () => {
        const answer: BulkImportResponse = {
            successImportInfoList: [{ parentObjectName: "g", importStatus: "SUCCESS" }],
        };
        service.importBusinessMetadata("attrs.csv", new Blob(["a,b\n"])).subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/entity/businessmetadata/import");
        expect(req.request.method).toBe("POST");
        const form = req.request.body as FormData;
        expect(form).toBeInstanceOf(FormData);
        expect((form.get("file") as File).name).toBe("attrs.csv");
        req.flush(answer);
    });

    it("the three label verbs map as the server reads them: POST set, PUT add, DELETE remove (ACL-08, CLE-06)", () => {
        service.setLabels("7a1b", ["PII"]).subscribe();

        const set = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/labels");
        expect(set.request.method).toBe("POST");
        expect(set.request.body).toEqual(["PII"]);
        set.flush({});

        service.addLabels("7a1b", ["PII"]).subscribe();

        const add = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/labels");
        expect(add.request.method).toBe("PUT");
        add.flush({});

        service.removeLabels("7a1b", ["PII"]).subscribe();

        const rm = httpMock.expectOne("/api/atlas/v2/entity/guid/7a1b/labels");
        expect(rm.request.method).toBe("DELETE");
        expect(rm.request.body).toEqual(["PII"]);
        rm.flush({});
    });

    it("the unique-attribute label siblings send attr: params and a bare array (ACL-08, CLE-06)", () => {
        service.setLabelsByUniqueAttributes("sales_table", { qualifiedName: "s1.t.o" }, ["PII"]).subscribe();

        const set = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table/labels");
        expect(set.request.method).toBe("POST");
        expect(set.request.params.get("attr:qualifiedName")).toBe("s1.t.o");
        expect(set.request.body).toEqual(["PII"]);
        set.flush({});

        service.addLabelsByUniqueAttributes("sales_table", { qualifiedName: "s1.t.o" }, ["PII"]).subscribe();

        const add = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table/labels");
        expect(add.request.method).toBe("PUT");
        add.flush({});

        service.removeLabelsByUniqueAttributes("sales_table", { qualifiedName: "s1.t.o" }, ["PII"]).subscribe();

        const rm = httpMock.expectOne((r) => r.url === "/api/atlas/v2/entity/uniqueAttribute/type/sales_table/labels");
        expect(rm.request.method).toBe("DELETE");
        expect(rm.request.params.get("attr:qualifiedName")).toBe("s1.t.o");
        expect(rm.request.body).toEqual(["PII"]);
        rm.flush({});
    });
});
