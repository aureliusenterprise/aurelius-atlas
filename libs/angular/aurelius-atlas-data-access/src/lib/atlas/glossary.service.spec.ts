import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { API_BASE_URL, provideApiBaseUrl } from "../api-config";
import type { AtlasGlossary, AtlasGlossaryCategory, AtlasGlossaryTerm } from "./atlas-glossary";
import type { BulkImportResponse } from "./atlas-impexp";
import { GlossaryService } from "./glossary.service";

describe("GlossaryService (AGL-01..07)", () => {
    let service: GlossaryService;
    let httpMock: HttpTestingController;

    const glossary: AtlasGlossary = {
        guid: "gl-1",
        qualifiedName: "Sales",
        name: "Sales",
        terms: [{ termGuid: "t-1", displayText: "Revenue" }],
    };
    const category: AtlasGlossaryCategory = {
        guid: "c-1",
        name: "Products",
        anchor: { glossaryGuid: "gl-1", displayText: "Sales" },
    };
    const term: AtlasGlossaryTerm = {
        guid: "t-1",
        name: "Revenue",
        anchor: { glossaryGuid: "gl-1", displayText: "Sales" },
    };

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [provideHttpClient(), provideHttpClientTesting()],
        });
        service = TestBed.inject(GlossaryService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => httpMock.verify());

    it("is created", () => {
        expect(service).toBeTruthy();
    });

    it("getGlossary and getDetailedGlossary read the glossary, bare and wrapped (AGL-01, GLS-01/06)", () => {
        service.getGlossary("gl 1").subscribe();

        const get = httpMock.expectOne("/api/atlas/v2/glossary/gl%201");
        expect(get.request.method).toBe("GET");
        get.flush(glossary);

        service.getDetailedGlossary("gl-1").subscribe();

        const detailed = httpMock.expectOne("/api/atlas/v2/glossary/gl-1/detailed");
        expect(detailed.request.method).toBe("GET");
        detailed.flush({ ...glossary, termInfo: { "t-1": term }, categoryInfo: { "c-1": category } });
    });

    it("getGlossaries with no page sends no parameters — the defaults travel as absence (AGL-02, CLG-02)", () => {
        service.getGlossaries().subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/glossary");
        expect(req.request.method).toBe("GET");
        expect(req.request.params.keys()).toEqual([]);
        req.flush([glossary]);
    });

    it("the paging sends only given values: explicit -1 travels, 0 stays absent, sort when given (AGL-02, CLG-02)", () => {
        service.getGlossaries({ limit: -1 }).subscribe();

        const every = httpMock.expectOne((r) => r.url === "/api/atlas/v2/glossary" && r.params.get("limit") === "-1");
        expect(every.request.params.keys()).toEqual(["limit"]);
        every.flush([]);

        service.getGlossaries({ limit: 0, offset: 0 }).subscribe();

        const zeros = httpMock.expectOne((r) => r.url === "/api/atlas/v2/glossary" && r.params.keys().length === 0);
        zeros.flush([]);

        service.getGlossaries({ offset: 10, sort: "DESC" }).subscribe();

        const sorted = httpMock.expectOne((r) => r.url === "/api/atlas/v2/glossary" && r.params.get("offset") === "10");
        expect(sorted.request.params.get("sort")).toBe("DESC");
        sorted.flush([]);
    });

    it("createGlossary posts the bare glossary and answers it back (AGL-03, GLS-02)", () => {
        service.createGlossary(glossary).subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/glossary");
        expect(req.request.method).toBe("POST");
        expect(req.request.body).toEqual(glossary);
        req.flush(glossary);
    });

    it("updateGlossary puts the body as given — the server grafts the path guid (AGL-03, CLG-08)", () => {
        service.updateGlossary("gl-1", { name: "Sales Europe" }).subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/glossary/gl-1");
        expect(req.request.method).toBe("PUT");
        expect(req.request.body).toEqual({ name: "Sales Europe" });
        req.flush({ ...glossary, name: "Sales Europe" });
    });

    it("the four paged category/term reads share the paging and answer their element types (AGL-02, GLS-05)", () => {
        service.getGlossaryCategories("gl-1", { limit: 25 }).subscribe();

        const cats = httpMock.expectOne(
            (r) => r.url === "/api/atlas/v2/glossary/gl-1/categories" && r.params.get("limit") === "25",
        );
        cats.flush([category]);

        service.getGlossaryCategoriesHeaders("gl-1").subscribe();

        const catHeaders = httpMock.expectOne("/api/atlas/v2/glossary/gl-1/categories/headers");
        catHeaders.flush([{ categoryGuid: "c-1", displayText: "Products" }]);

        service.getGlossaryTerms("gl-1").subscribe();

        const terms = httpMock.expectOne("/api/atlas/v2/glossary/gl-1/terms");
        terms.flush([term]);

        service.getGlossaryTermsHeaders("gl-1", { sort: "ASC" }).subscribe();

        const termHeaders = httpMock.expectOne(
            (r) => r.url === "/api/atlas/v2/glossary/gl-1/terms/headers" && r.params.get("sort") === "ASC",
        );
        expect(termHeaders.request.params.keys()).toEqual(["sort"]);
        termHeaders.flush([{ termGuid: "t-1", displayText: "Revenue" }]);
    });

    it("partialUpdateGlossary puts the bare attribute map (AGL-04, GLS-03)", () => {
        service.partialUpdateGlossary("gl-1", { longDescription: "All sales.", usage: "BUSINESS" }).subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/glossary/gl-1/partial");
        expect(req.request.method).toBe("PUT");
        expect(req.request.body).toEqual({ longDescription: "All sales.", usage: "BUSINESS" });
        req.flush(glossary);
    });

    it("partialUpdateGlossary with no fields raises and makes no request (AGL-04, CLG-03)", () => {
        expect(() => service.partialUpdateGlossary("gl-1", {})).toThrow(/NO_PARTIAL_UPDATES/);
        httpMock.expectNone("/api/atlas/v2/glossary/gl-1/partial");
    });

    it("deleteGlossary answers 204 as void (AGL-05, GLS-04, CLG-09)", () => {
        service.deleteGlossary("gl-1").subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/glossary/gl-1");
        expect(req.request.method).toBe("DELETE");
        req.flush(null);
    });

    it("glossaryImportTemplate answers the bytes pair (AGL-06, GIM-06, DD-315)", () =>
        new Promise<void>((done, fail) => {
            const csv = new ArrayBuffer(3);
            new Uint8Array(csv).set([0x61, 0x62, 0x63]);

            service.glossaryImportTemplate().subscribe({
                next: (answer) => {
                    expect(answer.body).toEqual(csv);
                    expect(answer.contentType).toBe("application/octet-stream");
                    done();
                },
                error: fail,
            });

            const req = httpMock.expectOne("/api/atlas/v2/glossary/import/template");
            expect(req.request.method).toBe("GET");
            req.flush(csv, { headers: { "content-type": "application/octet-stream" } });
        }));

    it("importGlossaryData posts the file part and answers the bulk response (AGL-06, GIM-01, CLG-06)", () => {
        const answer: BulkImportResponse = {
            successImportInfoList: [{ parentObjectName: "Sales", importStatus: "SUCCESS" }],
        };
        service.importGlossaryData("terms.csv", new Blob(["a,b\n"])).subscribe();

        const req = httpMock.expectOne("/api/atlas/v2/glossary/import");
        expect(req.request.method).toBe("POST");
        const form = req.request.body as FormData;
        expect(form).toBeInstanceOf(FormData);
        expect((form.get("file") as File).name).toBe("terms.csv");
        req.flush(answer);
    });

    it("every URL composes from API_BASE_URL (AGL-01, APC-01)", () => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({
            providers: [provideApiBaseUrl("/atlas-api"), provideHttpClient(), provideHttpClientTesting()],
        });
        const scoped = TestBed.inject(GlossaryService);
        const mock = TestBed.inject(HttpTestingController);

        scoped.getGlossary("gl-1").subscribe();
        mock.expectOne("/atlas-api/atlas/v2/glossary/gl-1").flush(glossary);
        mock.verify();
    });
});
