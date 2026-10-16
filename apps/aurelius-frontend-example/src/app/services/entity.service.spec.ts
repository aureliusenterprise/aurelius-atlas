import { TestBed } from "@angular/core/testing";
import { EntitiesService, Entity, Envelope } from "aurelius-data-access";
import { Subject } from "rxjs";
import { EntityService } from "./entity.service";

describe("EntityService", () => {
    let service: EntityService;
    let entitiesSubject: Subject<Envelope<Entity>>;

    beforeEach(() => {
        entitiesSubject = new Subject<Envelope<Entity>>();

        TestBed.configureTestingModule({
            providers: [
                EntityService,
                { provide: EntitiesService, useValue: { entities$: entitiesSubject.asObservable() } },
            ],
        });
        service = TestBed.inject(EntityService);
    });

    afterEach(() => {
        entitiesSubject.complete();
    });

    it("should initialize with null entity", () => {
        expect(service.entity()).toBeNull();
    });

    it("should clear the entity", () => {
        service.entity.set({ guid: "123", name: "Test", description: "Desc" });
        service.clear();
        expect(service.entity()).toBeNull();
    });

    it("should create a new entity with default values", () => {
        service.create();
        expect(service.entity()).toEqual({ guid: undefined, name: "", description: "" });
    });

    it("should edit an existing entity", () => {
        const entity: Entity = { guid: "abc", name: "Name", description: "Desc" };
        service.edit(entity);
        expect(service.entity()).toEqual(entity);
    });

    // Subject delivery is synchronous, so no timer wait is needed; the previous
    // setTimeout(50)/100 ms-timeout pattern raced on the wall clock and flaked on loaded runners.
    it("should update the current entity when receiving an update for the same GUID", () => {
        const initialEntity: Entity = { guid: "123", name: "Original", description: "Desc" };
        service.edit(initialEntity);

        const updatedEntity: Entity = { guid: "123", name: "Updated", description: "New Desc" };

        const envelope: Envelope<Entity> = {
            guid: "123",
            op: "UPDATE",
            timestamp: new Date().toISOString(),
            value: updatedEntity,
        };

        entitiesSubject.next(envelope);

        expect(service.entity()).toEqual(updatedEntity);
    });

    it("should clear the entity when receiving a deletion (null value) for the current GUID", () => {
        const initialEntity: Entity = { guid: "123", name: "Original", description: "Desc" };
        service.edit(initialEntity);

        const deleteEnvelope: Envelope<Entity> = {
            guid: "123",
            op: "DELETE",
            timestamp: new Date().toISOString(),
            value: null,
        };

        entitiesSubject.next(deleteEnvelope);

        expect(service.entity()).toBeNull();
    });

    it("should NOT update the entity when receiving an update for a different GUID", () => {
        const currentEntity: Entity = { guid: "123", name: "Current", description: "Desc" };
        service.edit(currentEntity);

        // Simulate update for a different entity with different GUID
        const otherEntity: Entity = { guid: "456", name: "Other", description: "Other Desc" };

        const envelope: Envelope<Entity> = {
            guid: "456",
            op: "UPDATE",
            timestamp: new Date().toISOString(),
            value: otherEntity,
        };

        entitiesSubject.next(envelope);

        expect(service.entity()).toEqual(currentEntity);
    });

    it("should NOT update the entity when receiving a deletion for a different GUID", () => {
        const currentEntity: Entity = { guid: "123", name: "Current", description: "Desc" };
        service.edit(currentEntity);

        // Simulate deletion of a different entity
        const deleteEnvelope: Envelope<Entity> = {
            guid: "456",
            op: "DELETE",
            timestamp: new Date().toISOString(),
            value: null,
        };

        entitiesSubject.next(deleteEnvelope);

        expect(service.entity()).toEqual(currentEntity);
    });

    it("should NOT update the entity when current is null and receives an update for a new GUID", () => {
        // Start with no current entity
        expect(service.entity()).toBeNull();

        const newEntity: Entity = {
            guid: "789",
            name: "New Entity",
            description: "First Desc",
            time_created: new Date().toISOString(),
            time_modified: new Date().toISOString(),
        };

        const envelope: Envelope<Entity> = {
            guid: "789",
            op: "INSERT",
            timestamp: new Date().toISOString(),
            value: newEntity,
        };

        entitiesSubject.next(envelope);

        expect(service.entity()).toBeNull();
    });
});
