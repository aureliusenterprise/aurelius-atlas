import { provideHttpClient } from "@angular/common/http";
import { HttpErrorResponse } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ReactiveFormsModule } from "@angular/forms";
import { EntitiesService } from "aurelius-atlas-data-access";
import { of } from "rxjs";
import { beforeEach, describe, expect, it } from "vitest";
import { EntityService } from "../services/entity.service";
import { SEARCH_SERVICE_DEBOUNCE_MS, SearchService } from "../services/search.service";
import { Editor } from "./editor.component";

describe("Editor", () => {
    let component: Editor;
    let fixture: ComponentFixture<Editor>;

    let entityService: EntityService;
    let searchService: SearchService;
    let entitiesService: EntitiesService;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [ReactiveFormsModule],
            providers: [
                provideHttpClient(),
                provideHttpClientTesting(),
                EntityService,
                SearchService,
                EntitiesService,
                { provide: SEARCH_SERVICE_DEBOUNCE_MS, useValue: 25 },
            ],
        }).compileComponents();

        fixture = TestBed.createComponent(Editor);
        component = fixture.componentInstance;

        entityService = TestBed.inject(EntityService);
        searchService = TestBed.inject(SearchService);
        entitiesService = TestBed.inject(EntitiesService);
    });

    it("should create", () => {
        expect(component).toBeTruthy();
    });

    it("should clear entity on cancel", () => {
        vi.spyOn(entityService, "clear").mockImplementationOnce(() => null);

        component.cancel();

        expect(entityService.clear).toHaveBeenCalled();
    });

    it("should delete entity and clear state", async () => {
        vi.spyOn(entitiesService, "delete").mockImplementationOnce(() => of(void 0));
        vi.spyOn(entityService, "clear").mockImplementationOnce(() => null);

        await component.delete("test-guid");

        expect(entitiesService.delete).toHaveBeenCalledWith("test-guid");
        expect(entityService.clear).toHaveBeenCalled();
    });

    it("should not call delete if guid is null", async () => {
        vi.spyOn(entitiesService, "delete").mockImplementationOnce(() => of(void 0));
        vi.spyOn(searchService, "refresh").mockImplementationOnce(() => null);
        vi.spyOn(entityService, "clear").mockImplementationOnce(() => null);

        await component.delete(null);

        expect(entitiesService.delete).not.toHaveBeenCalled();
        expect(entityService.clear).toHaveBeenCalled();
    });

    it("should save entity and clear state", async () => {
        const entity = { description: "desc", guid: "g", name: "n", time_created: null, time_modified: null };

        vi.spyOn(entitiesService, "createOrUpdate").mockImplementationOnce(() => of(entity));
        vi.spyOn(entityService, "clear").mockImplementationOnce(() => null);

        entityService.edit(entity);
        await fixture.whenStable();

        await component.save();

        expect(entitiesService.createOrUpdate).toHaveBeenCalledWith(entity);
        expect(entityService.clear).toHaveBeenCalled();
    });

    it("should patch form when updateEntityForm called with entity", async () => {
        const compiled = fixture.nativeElement as HTMLElement;

        const entity = { description: "d", guid: "g", name: "n", time_created: null, time_modified: null };
        entityService.edit(entity);
        await fixture.whenStable();

        expect(compiled.querySelector<HTMLInputElement>("#guid")?.value).toEqual(entity.guid);
        expect(compiled.querySelector<HTMLInputElement>("#name")?.value).toEqual(entity.name);
        expect(compiled.querySelector<HTMLInputElement>("#description")?.value).toEqual(entity.description);
    });

    it("should reset form when updateEntityForm called with null", async () => {
        const compiled = fixture.nativeElement as HTMLElement;

        const entity = { description: "d", guid: "g", name: "n", time_created: null, time_modified: null };
        entityService.edit(entity);
        await fixture.whenStable();

        expect(compiled.querySelector<HTMLInputElement>("#guid")?.value).toEqual(entity.guid);
        expect(compiled.querySelector<HTMLInputElement>("#name")?.value).toEqual(entity.name);
        expect(compiled.querySelector<HTMLInputElement>("#description")?.value).toEqual(entity.description);

        entityService.clear();
        await fixture.whenStable();

        expect(compiled.querySelector<HTMLInputElement>("input#guid")?.value).toBeUndefined();
        expect(compiled.querySelector<HTMLInputElement>("input#name")?.value).toBeUndefined();
        expect(compiled.querySelector<HTMLInputElement>("input#description")?.value).toBeUndefined();
    });

    it("should preserve timestamp fields when saving", async () => {
        const entity = {
            description: "desc",
            guid: "g",
            name: "n",
            time_created: "2024-01-01T00:00:00.000Z",
            time_modified: "2024-01-02T00:00:00.000Z",
        };

        vi.spyOn(entitiesService, "createOrUpdate").mockImplementationOnce(() => of(entity));
        vi.spyOn(entityService, "clear").mockImplementationOnce(() => null);

        entityService.edit(entity);
        await fixture.whenStable();
        await component.save();

        expect(entitiesService.createOrUpdate).toHaveBeenCalledWith(entity);
    });

    // The failure trio below runs against a real HttpClient +
    // HttpTestingController (DD-214): no spy on the service under test, so
    // the failure travels the same path the app's users take.

    it("keeps the entity open when the server rejects a save (DD-214)", async () => {
        const httpMock = TestBed.inject(HttpTestingController);
        const entity = { description: "desc", guid: "g", name: "n", time_created: null, time_modified: null };

        entityService.edit(entity);
        await fixture.whenStable();

        const saving = component.save();
        const req = httpMock.expectOne("/api/entities/");
        expect(req.request.method).toBe("PUT");
        req.flush(
            { errorCode: "ATLAS-500-00-001", errorMessage: "failed to persist entity" },
            { status: 500, statusText: "Internal Server Error" },
        );

        // The rejection surfaces (the app's error handler records it) and
        // the editor stays open: clear() never runs, the edit is not lost.
        const status = await saving.then(
            () => null,
            (e: unknown) => (e instanceof HttpErrorResponse ? e.status : -1),
        );
        expect(status).toBe(500);
        expect(entityService.entity()).toEqual(entity);
    });

    it("surfaces the status when the server rejects a delete (DD-214)", async () => {
        const httpMock = TestBed.inject(HttpTestingController);

        const deleting = component.delete("gone-guid");
        const req = httpMock.expectOne("/api/entities/gone-guid");
        expect(req.request.method).toBe("DELETE");
        req.flush(
            { errorCode: "ATLAS-404-00-002", errorMessage: "entity with guid gone-guid does not exist" },
            { status: 404, statusText: "Not Found" },
        );

        const status = await deleting.then(
            () => null,
            (e: unknown) => (e instanceof HttpErrorResponse ? e.status : -1),
        );
        expect(status).toBe(404);
    });

    it("sends nothing when the name is over the limit (DD-214)", async () => {
        const httpMock = TestBed.inject(HttpTestingController);
        const entity = { description: "desc", guid: "g", name: "short", time_created: null, time_modified: null };

        entityService.edit(entity);
        fixture.detectChanges();
        await fixture.whenStable();

        const compiled = fixture.nativeElement as HTMLElement;
        const nameInput = compiled.querySelector<HTMLInputElement>("#name");
        nameInput!.value = "n".repeat(101);
        nameInput!.dispatchEvent(new Event("input"));
        fixture.detectChanges();

        // The maxLength(100) validator marks the field (the template's
        // is-danger + help text): the form is invalid.
        expect(nameInput!.classList.contains("is-danger")).toBe(true);

        // The Save button is the gate (the template disables it while the
        // form is invalid): clicking it must not fire a request.
        const saveButton = compiled.querySelector("button.is-success") as HTMLButtonElement;
        expect(saveButton.disabled).toBe(true);
        saveButton.click();
        await fixture.whenStable();

        expect(httpMock.match((r) => r.url === "/api/entities/")).toHaveLength(0);
    });
});
