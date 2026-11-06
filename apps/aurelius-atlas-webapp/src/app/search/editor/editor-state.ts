import { Injectable, computed, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import { Observable, forkJoin } from "rxjs";
import {
    AtlasEntitiesService,
    TypeDefsService,
    type AtlasClassification,
    type AtlasClassificationDef,
    type AtlasEntity,
    type AtlasEntityDef,
    type AtlasEnumDef,
    type AtlasTypesDef,
} from "aurelius-atlas-data-access";

import { AlertsService } from "../../alerts/alerts.service";

import { EntitySaved } from "./entity-saved";

/** The editor's mode, read off its own route segment (EDT-01, DD-325). */
export type EditorMode = "edit" | "create";

/** A picker row: the type name and the label to show (EDT-04). */
export type PickerType = { name: string; label: string };

/**
 * The editor drawer's store (EDT-02..EDT-06, DD-325, DD-326): the entity
 * read the drawer owns (EDT-02, DD-322 — no shared store with the screen
 * underneath), the one typedefs call the picker, the field resolver, and the
 * classification box all read (EDT-04), the chosen classifications (EDT-05),
 * and the two-request save (EDT-06).
 *
 * The save is the entity POST, then the classification diff: one
 * `POST .../guid/{guid}/classifications` for the added tags and one
 * `DELETE .../classification/{name}` per removal (DD-326 — the legacy
 * diff; the CLS-08 replace call cannot attach a new tag or detach one,
 * live-probed). A create payload carries a negative numeric temporary guid
 * and a uuid `qualifiedName`, and the navigation uses the real guid from
 * the mutation answer's `guidAssignments` (DD-325, live-probed: a uuid guid
 * reads as a reference and the server refuses it).
 */
@Injectable()
export class EditorState {
    private readonly entities = inject(AtlasEntitiesService);

    private readonly typedefs = inject(TypeDefsService);

    private readonly alerts = inject(AlertsService);

    private readonly router = inject(Router);

    /** The saved-tick bus (DD-327): the details screen underneath re-reads. */
    private readonly entitySaved = inject(EntitySaved);

    /** The editor's mode, set once by the route component from its route. */
    readonly mode = signal<EditorMode>("edit");

    /** The entity being edited (edit mode), or null before/without a read. */
    readonly entity = signal<AtlasEntity | null>(null);

    /** The whole typedefs answer (EDT-04's single call). */
    readonly typedefsDef = signal<AtlasTypesDef | null>(null);

    /** The create-mode type the picker chose (EDT-04), null before the pick. */
    readonly selectedTypeName = signal<string | null>(null);

    /** The classifications the tag box holds (EDT-05). */
    readonly chosen = signal<readonly AtlasClassification[]>([]);

    /** The own-classification names the read seeded the box with (DD-326's diff base). */
    private initialOwnNames = new Set<string>();

    /** Whether the entity read is in flight (EDT-02's loading line). */
    readonly loading = signal(false);

    /** Whether a save is in flight (the Save button's busy state). */
    readonly saving = signal(false);

    /** The entity type the form renders (edit: the entity's, create: the pick). */
    readonly typeName = computed(() =>
        this.mode() === "create" ? this.selectedTypeName() : (this.entity()?.typeName ?? null),
    );

    /** Every entity definition by name (the supertype walk's lookup). */
    readonly entityDefsByName = computed(() => {
        const byName = new Map<string, AtlasEntityDef>();
        for (const def of this.typedefsDef()?.entityDefs ?? []) {
            if (def.name) {
                byName.set(def.name, def);
            }
        }
        return byName;
    });

    /** Every enum definition by name (EDT-03's enum lookup + values). */
    readonly enumsByName = computed(() => {
        const byName = new Map<string, AtlasEnumDef>();
        for (const def of this.typedefsDef()?.enumDefs ?? []) {
            if (def.name) {
                byName.set(def.name, def);
            }
        }
        return byName;
    });

    /**
     * The create-mode picker list (EDT-04): every entity typedef except the
     * glossary types and the `__`-prefixed internals, labelled by alias else
     * name, sorted.
     */
    readonly pickerTypes = computed<readonly PickerType[]>(() => {
        const rows: PickerType[] = [];
        for (const def of this.typedefsDef()?.entityDefs ?? []) {
            const name = def.name ?? "";
            if (name === "" || name.startsWith("__") || name.startsWith("AtlasGlossary")) {
                continue;
            }
            rows.push({ name, label: def.options?.["displayName"] ?? name });
        }
        return rows.sort((a, b) => a.label.localeCompare(b.label));
    });

    /**
     * The classification types the tag box offers (EDT-05): the defs whose
     * `entityTypes` include the entity's type or one of its supertypes, minus
     * the chosen ones.
     */
    readonly applicableClassifications = computed<readonly AtlasClassificationDef[]>(() => {
        const typeName = this.typeName();
        if (!typeName) {
            return [];
        }
        const lineage = this.typeLineage(typeName);
        const chosenNames = new Set(this.chosen().map((tag) => tag.typeName));

        return (this.typedefsDef()?.classificationDefs ?? []).filter((def) => {
            if (!def.name || chosenNames.has(def.name)) {
                return false;
            }
            const applies = def.entityTypes ?? [];

            return applies.length === 0 ? false : applies.some((type) => lineage.has(type));
        });
    });

    /** The type and its transitive supertypes (EDT-05's applicability rule). */
    private typeLineage(typeName: string): ReadonlySet<string> {
        const lineage = new Set<string>([typeName]);
        const defs = this.entityDefsByName();
        const queue = [typeName];

        while (queue.length > 0) {
            const current = defs.get(queue.shift() as string);
            for (const superName of current?.superTypes ?? []) {
                if (!lineage.has(superName)) {
                    lineage.add(superName);
                    queue.push(superName);
                }
            }
        }

        return lineage;
    }

    /** Fetch the whole typedefs answer once (EDT-04's single call). */
    loadTypeDefs(): void {
        this.typedefs.getTypedefs({}).subscribe({
            next: (answer) => this.typedefsDef.set(answer),
            error: () =>
                this.alerts.add({
                    severity: "error",
                    message: $localize`:@@search.components.classification.retrieve:Retrieving the classification type definition`,
                    source: "search",
                }),
        });
    }

    /**
     * Fetch the entity being edited (EDT-02): the answer seeds the type, and
     * the tag box starts at the entity's own classifications (DD-326 — only
     * the ones the entity carries itself, so the save's diff can never touch
     * a propagated tag). A failed read (a 404 among them) alerts and leaves
     * the form empty; the drawer stays open.
     * @param guid the route's entity address
     */
    loadEntity(guid: string): void {
        this.loading.set(true);
        this.entities.getEntityByGuid(guid).subscribe({
            next: (answer) => {
                this.loading.set(false);
                const entity = answer.entity ?? null;
                const own = ownClassifications(entity, guid);

                this.entity.set(entity);
                this.chosen.set(own);
                this.initialOwnNames = new Set(
                    own.map((tag) => tag.typeName).filter((name): name is string => Boolean(name)),
                );
            },
            error: () => {
                this.loading.set(false);
                this.alerts.add({
                    severity: "error",
                    message: $localize`:@@search.services.entityDetails.retrieve:Retrieving the entity details`,
                    source: "search",
                });
            },
        });
    }

    /**
     * Save (EDT-06): merge, POST the entity, then apply the classification
     * diff — one POST-add for the tags the box gained, one DELETE per tag it
     * lost (DD-326); tags the box kept are never re-sent, so the server's
     * replace-validation (CLS-08 changes attached tags only) never sees a
     * create-mode attachment or a removed tag. Then close the drawer on the
     * entity's details. A refused save (a 403 among them) adds one alert and
     * keeps the drawer and the edits (EDT-08) — the navigation never runs.
     * @param entity the merged entity (create: seeded, EDT-06/DD-325)
     * @param guid the entity's guid (edit: the route's; create: the temp one)
     */
    save(entity: AtlasEntity, guid: string): void {
        if (this.saving()) {
            return;
        }
        this.saving.set(true);
        this.entities.createOrUpdateEntity({ entity }).subscribe({
            next: (answer) => {
                const realGuid = this.mode() === "create" ? (answer.guidAssignments?.[guid] ?? "") : guid;
                if (realGuid === "") {
                    this.saveFailed();

                    return;
                }
                this.applyClassifications(realGuid).subscribe({
                    next: () => {
                        this.saving.set(false);
                        // The screen underneath may be this very entity's
                        // details, still mounted (EDT-01): the tick re-fires
                        // its read (DD-327), then land on the details with
                        // the drawer outlet cleared through the commands
                        // array (NavigationExtras has no `outlets` key).
                        this.entitySaved.notify(realGuid);
                        // The root compound form (DD-322): a string-command
                        // array with a trailing {outlets} applies the outlet
                        // instruction inside the primary child group, not the
                        // root where the drawer lives — the drawer segment
                        // survives it (live-probed in the e2e). The compound
                        // is how settings and alerts close their drawer.
                        this.router.navigate([{ outlets: { primary: ["search", "details", realGuid], drawer: null } }]);
                    },
                    error: () => this.saveFailed(),
                });
            },
            error: () => this.saveFailed(),
        });
    }

    /**
     * The classification diff (DD-326): the box's added tags ride one
     * `POST .../classifications`, its removed ones one DELETE each — the two
     * name-sets are disjoint, so the writes run together. Added tags are
     * stamped with the real guid (a create-mode tag carries the temporary
     * one, and the attach names its entity). Unchanged tags send nothing.
     * @param realGuid the entity's server guid (create: the assignment)
     * @returns an observable that answers when every write has
     */
    private applyClassifications(realGuid: string): Observable<unknown[]> {
        const finalTags = this.chosen()
            .filter((tag): tag is AtlasClassification & { typeName: string } => Boolean(tag.typeName))
            .map((tag) => ({ ...tag, entityGuid: realGuid }));
        const finalNames = new Set(finalTags.map((tag) => tag.typeName));
        const added = finalTags.filter((tag) => !this.initialOwnNames.has(tag.typeName));
        const removed = [...this.initialOwnNames].filter((name) => !finalNames.has(name));

        const calls: Observable<unknown>[] = removed.map((name) => this.entities.deleteClassification(realGuid, name));

        if (added.length > 0) {
            calls.push(this.entities.addClassifications(realGuid, added));
        }

        // forkJoin needs a non-empty array; an empty diff answers at once.
        return calls.length > 0 ? forkJoin(calls) : new Observable<[]>((subscriber) => subscriber.next([]));
    }

    /** The refused-save path (EDT-08): one alert, drawer open, edits kept. */
    private saveFailed(): void {
        this.saving.set(false);
        this.alerts.add({
            severity: "error",
            message: $localize`:@@search.services.entityUpdate.save:Saving the entity`,
            source: "search",
        });
    }

    /**
     * Add a classification tag (EDT-05): the legacy shape the server expects.
     * @param typeName the classification type chosen in the box
     */
    addClassification(typeName: string): void {
        // The owner is the entity's own guid — in create mode the seeded
        // temporary one, which the server re-keys through guidAssignments
        // (DD-325).
        const owner = this.entity()?.guid ?? "";
        const exists = this.chosen().some((tag) => tag.typeName === typeName);
        if (exists || typeName === "") {
            return;
        }
        this.chosen.update((tags) => [
            ...tags,
            { typeName, entityGuid: owner, propagate: true, removePropagationsOnEntityDelete: true },
        ]);
    }

    /**
     * Remove a classification tag (EDT-05).
     * @param typeName the tag to drop
     */
    removeClassification(typeName: string): void {
        this.chosen.update((tags) => tags.filter((tag) => tag.typeName !== typeName));
    }

    /**
     * Seed the create-mode entity (DD-325): a negative numeric temporary guid
     * (the server's create idiom — the e2e seed sends the same shape; a uuid
     * guid reads as a reference and is refused) and a uuid `qualifiedName`
     * (the server does not invent one). The stored entity exists so the tag
     * box has an `entityGuid` before the save; the save's merge starts here.
     * @param typeName the type the picker chose
     * @returns the seeded entity's temporary guid
     */
    beginCreate(typeName: string): string {
        const temporaryGuid = String(-Math.floor(Math.random() * 1e15) - 1);

        this.selectedTypeName.set(typeName);
        this.entity.set({
            guid: temporaryGuid,
            typeName,
            attributes: { qualifiedName: crypto.randomUUID() },
        });
        this.chosen.set([]);
        this.initialOwnNames = new Set();

        return temporaryGuid;
    }
}

/**
 * The entity's own classifications (DD-326): the tags whose `entityGuid` is
 * the entity's own guid — the propagated ones never enter the box, so the
 * replace call cannot sever them.
 * @param entity the read entity
 * @param guid the entity's guid
 * @returns the own-classification tags
 */
function ownClassifications(entity: AtlasEntity | null, guid: string): AtlasClassification[] {
    return (entity?.classifications ?? []).filter((tag) => tag.entityGuid === guid || tag.entityGuid == null);
}
