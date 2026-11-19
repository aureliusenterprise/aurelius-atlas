import { HttpErrorResponse } from "@angular/common/http";
import { Injectable, computed, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import {
    AtlasEntitiesService,
    TypeDefsService,
    ViewEntityService,
    ViewSaveService,
    ViewTypeService,
    isAtlasErrorBody,
    viewConflictFrom,
    type AtlasClassificationDef,
    type AtlasEntity,
    type AtlasEntityDef,
    type AtlasEnumDef,
    type AtlasTypeDefHeader,
    type EntityView,
    type ViewSaveRequest,
} from "aurelius-atlas-data-access";

import { AlertsService } from "../../alerts/alerts.service";
import { nameDisplay } from "../meta/type-display";
import { TYPE_ICONS } from "../meta/type-icons";

import { EntitySaved } from "./entity-saved";
import { entityFromView, tagsAfterConflict } from "./view-as-entity";

/** The editor's mode, read off its own route segment (EDT-01, DD-325). */
export type EditorMode = "edit" | "create";

/** A picker row: the type name and the label to show (EDT-04). */
export type PickerType = { name: string; label: string };

/** What a conflict replaced (VDE-07, DD-610): the view held before it, and the stored one. */
export type ConflictEvent = { from: EntityView | null; to: EntityView };

/**
 * The editor drawer's store on the view doors (VDE-01..VDE-10, DD-608..DD-612):
 * the entity read the drawer owns (EDT-02, DD-322 kept — no shared store with
 * the screen underneath) now rides the read door (VDE-01, DD-608); the form's
 * type material comes from the for-type chain and three small slices, cached
 * by name (VDE-02, DD-611); the tag box starts at the view's own tags
 * (VDE-03 — the client's DD-326 filter retires); and a save is one door POST
 * (VDE-05, DD-609), whose conflict re-edits from the stored view (VDE-07,
 * DD-610). The delete stays Atlas's (VDE-11) — the door does not delete.
 *
 * The create seeds no temporary guid (VDE-05, DD-592): the draft carries the
 * qualified name the client generates, the body names no guid, and the
 * answer's view carries the server's (AVW-06) — the `guidAssignments` remap
 * of DD-325 retires.
 */
@Injectable()
export class EditorState {
    private readonly entities = inject(AtlasEntitiesService);

    private readonly views = inject(ViewEntityService);

    private readonly saves = inject(ViewSaveService);

    private readonly types = inject(ViewTypeService);

    private readonly typedefs = inject(TypeDefsService);

    private readonly alerts = inject(AlertsService);

    private readonly router = inject(Router);

    /** The saved-tick bus (DD-327): the details screen underneath re-reads. */
    private readonly entitySaved = inject(EntitySaved);

    /** The editor's mode, set once by the route component from its route. */
    readonly mode = signal<EditorMode>("edit");

    /**
     * The view the save merges onto (DD-608): the read door's answer, or — after
     * a conflict — the stored view the answer carried (VDE-07, DD-610). Null
     * before the read, on a failed read, and through create (the draft below).
     */
    readonly view = signal<EntityView | null>(null);

    /** The create-mode draft (VDE-05, DD-592): the type and the client's qualified name. */
    private readonly draft = signal<AtlasEntity | null>(null);

    /** The entity the editor renders (VDE-01, DD-608): the view's draft, or the create seed. */
    readonly entity = computed(() => this.viewedEntity() ?? this.draft());

    /** The view's draft, kept as a computed so the view read and the draft stay apart. */
    private readonly viewedEntity = computed(() => {
        const view = this.view();

        return view === null ? null : entityFromView(view);
    });

    /** The create-mode type the picker chose (EDT-04), null before the pick. */
    readonly selectedTypeName = signal<string | null>(null);

    /** The classification names the tag box holds (EDT-05, VDE-03). */
    readonly chosen = signal<readonly string[]>([]);

    /** The entity type chain of the type being edited (VDE-02, AVW-11), through the door's client cache. */
    readonly chainDefs = signal<readonly AtlasEntityDef[]>([]);

    /** The classification defs the tag box offers (VDE-02, DD-611's slice). */
    readonly classificationDefs = signal<readonly AtlasClassificationDef[]>([]);

    /** The enum defs the form's enum fields read (VDE-02, DD-611's slice). */
    readonly enumDefs = signal<readonly AtlasEnumDef[]>([]);

    /** The entity typedef headers the create picker lists (VDE-02, TYR-08). */
    readonly entityHeaders = signal<readonly AtlasTypeDefHeader[]>([]);

    /** The conflict the component must re-seed from, or null (VDE-07, DD-610). */
    readonly conflict = signal<ConflictEvent | null>(null);

    /** Whether the entity read is in flight (EDT-02's loading line). */
    readonly loading = signal(false);

    /** Whether a save is in flight (the Save button's busy state). */
    readonly saving = signal(false);

    /** Whether a delete is in flight (the Delete button's busy state, EDT-19). */
    readonly deleting = signal(false);

    /** The entity type the form renders (edit: the entity's, create: the pick). */
    readonly typeName = computed(() =>
        this.mode() === "create" ? this.selectedTypeName() : (this.entity()?.typeName ?? null),
    );

    /**
     * The chain's entity definitions by name (VDE-02): the walked type and its
     * supertypes, each typedef whole from the for-type door — enough for
     * `buildFields` and `buildRelationshipFields` to walk unchanged.
     */
    readonly entityDefsByName = computed(() => {
        const byName = new Map<string, AtlasEntityDef>();
        for (const def of this.chainDefs()) {
            if (def.name) {
                byName.set(def.name, def);
            }
        }

        return byName;
    });

    /** Every enum definition by name (EDT-03's enum lookup + values, VDE-02). */
    readonly enumsByName = computed(() => {
        const byName = new Map<string, AtlasEnumDef>();
        for (const def of this.enumDefs()) {
            if (def.name) {
                byName.set(def.name, def);
            }
        }

        return byName;
    });

    /**
     * The create-mode picker list (EDT-04 as scoped by MMS-07, VDE-02): only
     * the metamodel types — the entity typedef headers the icon map names — so
     * the base-model supertypes an author never creates directly (`Asset`,
     * `DataSet`, `Process`, `Referenceable`, …) and the scaffold types without
     * an icon (`m4i_referenceable`, `m4i_dq_score`) stay
     * out, as do the glossary types and the `__`-prefixed internals (EDT-04 kept;
     * the icon map is the metamodel boundary — ADR 068, MMS-05, DV-180).
     * Labelled by alias else the dictionary display name, sorted. Headers carry
     * no `displayName`, so the label is the `nameDisplay` of the name (DD-379
     * kept); the order is the labels' (DD-497): a picker a person reads is a
     * word list, so the rows sort by the text they show.
     */
    readonly pickerTypes = computed<readonly PickerType[]>(() => {
        const rows: PickerType[] = [];
        for (const header of this.entityHeaders()) {
            const name = header.name ?? "";
            if (name === "" || !Object.hasOwn(TYPE_ICONS, name)) {
                continue;
            }
            rows.push({ name, label: nameDisplay(name) });
        }

        return rows.sort((a, b) => a.label.localeCompare(b.label));
    });

    /**
     * The classification types the tag box offers (EDT-05, VDE-02): the defs
     * whose `entityTypes` include the entity's type or one of its supertypes
     * — the chain's own names answer the lineage (AVW-11) — minus the chosen
     * ones.
     */
    readonly applicableClassifications = computed<readonly AtlasClassificationDef[]>(() => {
        const typeName = this.typeName();
        if (!typeName) {
            return [];
        }
        const lineage = new Set(
            this.chainDefs()
                .map((def) => def.name ?? "")
                .filter((name) => name !== ""),
        );
        const chosenNames = new Set(this.chosen());

        return this.classificationDefs().filter((def) => {
            if (!def.name || chosenNames.has(def.name)) {
                return false;
            }
            const applies = def.entityTypes ?? [];

            return applies.some((type) => lineage.has(type));
        });
    });

    /**
     * A classification type's description for the chip tooltip (UIC-16): the
     * classification slice answers it (DD-612 — the whole-typedefs dump retired).
     * @param typeName the tag's type
     */
    classificationDescription(typeName: string): string | undefined {
        return this.classificationDefs().find((def) => def.name === typeName)?.description ?? undefined;
    }

    /**
     * The chain for the type being edited (VDE-02): the for-type door's client
     * caches it by name (DD-611), so a re-pick of the same type asks nothing.
     * @param typeName the type to build a form for
     */
    loadChain(typeName: string): void {
        if (this.chainDefs().some((def) => def.name === typeName)) {
            return; // already asked for this chain (a re-pick of the same type)
        }
        this.types.forType(typeName).subscribe({
            next: (answer) => this.chainDefs.set([answer.type as AtlasEntityDef, ...answer.superTypes]),
            error: () => this.typesFailed(),
        });
    }

    /**
     * Fetch the three small slices the form's material rides (VDE-02, DD-611):
     * the classification defs, the enum defs, and the entity headers — once,
     * on the editor's open. A failed slice alerts with the retrieval line
     * EDT-04 kept and leaves its list empty; the drawer stays usable.
     */
    loadSlices(): void {
        this.typedefs.getTypedefs({ type: "CLASSIFICATION" }).subscribe({
            next: (answer) => this.classificationDefs.set(answer.classificationDefs ?? []),
            error: () => this.typesFailed(),
        });
        this.typedefs.getTypedefs({ type: "ENUM" }).subscribe({
            next: (answer) => this.enumDefs.set(answer.enumDefs ?? []),
            error: () => this.typesFailed(),
        });
        this.typedefs.getTypedefHeaders({ type: "ENTITY" }).subscribe({
            next: (headers) => this.entityHeaders.set(headers),
            error: () => this.typesFailed(),
        });
    }

    /** The type-material failure line (EDT-04 kept): one alert, the drawer stays open. */
    private typesFailed(): void {
        this.alerts.add({
            severity: "error",
            message: $localize`:@@search.components.classification.retrieve:Retrieving the classification type definition`,
            source: "search",
        });
    }

    /**
     * Fetch the entity being edited through the read door (VDE-01, DD-608):
     * the view answers the type, the tag box starts at its own
     * `classificationNames` (VDE-03 — propagated ones never enter, so
     * DD-326's filter retires), and the pickers seed from its `sections`
     * (VDE-04). The GUID cache (DD-605) serves a drawer opened from the
     * details screen with no request at all (VDR-07). A failed read (a 404
     * among them) alerts and leaves the form empty; the drawer stays open
     * (EDT-02's shape).
     * @param guid the route's entity address
     */
    loadEntity(guid: string): void {
        this.loading.set(true);
        this.views.view(guid).subscribe({
            next: (view) => {
                this.loading.set(false);
                this.view.set(view);
                this.chosen.set(view.classificationNames ?? []);
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
     * Save through the mutation door (VDE-05, DD-609): one POST carries the
     * attributes, the tag box's names, the picker ends, and the meanings
     * (VDE-03/04); an update names the base view's `updateTime` (AVW-04). The
     * answer is the entity's live view (AVW-07, VDE-06). The success evicts
     * the saved guid from the read cache before firing the tick, so the
     * details re-read asks the door (VDE-10, VDR-07), and lands on the
     * entity's details (EDT-06 kept). A conflict re-edits from the stored
     * view (VDE-07); a taken name answers its own line (VDE-08); anything
     * else is EDT-08's single alert (VDE-09). The navigation never runs on a
     * failed save.
     * @param body the entity's desired state as a door body (`bodyFromEdits`)
     */
    save(body: ViewSaveRequest): void {
        if (this.saving()) {
            return;
        }
        this.saving.set(true);
        this.saves.save(body).subscribe({
            next: (answer) => {
                this.saving.set(false);
                // The screen underneath may be this very entity's details,
                // still mounted (EDT-01): evict first so its re-read asks the
                // door (DD-608), then the tick re-fires it (DD-327), then land
                // on the details with the drawer outlet cleared through the
                // commands array (NavigationExtras has no `outlets` key).
                this.views.evict(answer.guid);
                this.entitySaved.notify(answer.guid);
                // The root compound form (DD-322): a string-command array
                // with a trailing {outlets} applies the outlet instruction
                // inside the primary child group, not the root where the
                // drawer lives — the drawer segment survives it (live-probed
                // in the e2e). The compound is how settings and alerts close
                // their drawer.
                void this.router.navigate([{ outlets: { primary: ["search", "details", answer.guid], drawer: null } }]);
            },
            error: (error: HttpErrorResponse) => {
                this.saving.set(false);
                const conflict = viewConflictFrom(error);
                if (conflict !== null) {
                    this.applyConflict(conflict.view);

                    return;
                }
                if (this.isNameTaken(error)) {
                    this.nameTaken();

                    return;
                }
                this.saveFailed();
            },
        });
    }

    /** The name-taken answer of a create (AVW-06): the Atlas error body carrying that code. */
    private isNameTaken(error: HttpErrorResponse): boolean {
        return error.status === 409 && isAtlasErrorBody(error.error) && error.error.errorCode === "ENTITY_NAME_TAKEN";
    }

    /**
     * The conflict's re-edit (VDE-07, DD-610): the base becomes the stored
     * view, the tag box re-answers it for what the person never touched, and
     * the component re-seeds the controls and pickers from the event. No
     * alert, no navigation (DD-591's reload-and-reedit path); a second Save
     * rides the stored `updateTime`, because it merges onto the new base.
     * @param stored the stored view the conflict answer carried
     */
    private applyConflict(stored: EntityView): void {
        const before = this.view();
        this.view.set(stored);
        this.chosen.set(tagsAfterConflict(before, stored, this.chosen()));
        this.conflict.set({ from: before, to: stored });
    }

    /** The component has re-seeded from the conflict (VDE-07): the event is spent. */
    conflictHandled(): void {
        this.conflict.set(null);
    }

    /** The name-taken line (VDE-08): one alert, drawer open, edits kept. */
    private nameTaken(): void {
        this.alerts.add({
            severity: "error",
            message: $localize`:@@search.components.editor.nameTaken:That name is already held by another entity.`,
            source: "search",
        });
    }

    /** The refused-save path (EDT-08, VDE-09): one alert, drawer open, edits kept. */
    private saveFailed(): void {
        this.alerts.add({
            severity: "error",
            message: $localize`:@@search.services.entityUpdate.save:Saving the entity`,
            source: "search",
        });
    }

    /**
     * Delete the entity (EDT-19, DD-347, VDE-11): one `DELETE .../guid/{guid}` —
     * the hold-to-confirm lives at the button, so the store trusts its
     * caller. No `deleteType` rides: the server's own strategy answers
     * (EDL-04, the reference's shape). Success closes the drawer and lands
     * on the browse landing — the deleted entity's details are not a
     * destination; a refusal adds one alert and keeps the drawer (EDT-08's
     * shape).
     * @param guid the entity's guid (edit mode only — the button's gate)
     */
    delete(guid: string): void {
        if (this.deleting() || this.saving()) {
            return;
        }
        this.deleting.set(true);
        this.entities.deleteEntityByGuid(guid).subscribe({
            next: () => {
                this.deleting.set(false);
                // The screen underneath is the deleted entity's details;
                // it is not a destination any more — the browse landing
                // is (the reference routes 'search', our landing).
                void this.router.navigate([{ outlets: { primary: ["search", "browse"], drawer: null } }]);
            },
            error: () => {
                this.deleting.set(false);
                this.alerts.add({
                    severity: "error",
                    message: $localize`:@@search.services.entityDelete.delete:Deleting the entity`,
                    source: "search",
                });
            },
        });
    }

    /**
     * Add a classification tag (EDT-05, VDE-03): the box holds names — the
     * door's `classifications` key takes the full desired set of names.
     * @param typeName the classification type chosen in the box
     */
    addClassification(typeName: string): void {
        if (typeName === "" || this.chosen().includes(typeName)) {
            return;
        }
        this.chosen.update((tags) => [...tags, typeName]);
    }

    /**
     * Remove a classification tag (EDT-05).
     * @param typeName the tag to drop
     */
    removeClassification(typeName: string): void {
        this.chosen.update((tags) => tags.filter((tag) => tag !== typeName));
    }

    /**
     * Seed the create-mode entity (VDE-05, DD-592): the type and a uuid
     * `qualifiedName` the client generates (the server does not invent one).
     * No temporary guid rides (DD-325's seed retires): the save body names no
     * guid, and the answer's view carries the server's (AVW-06).
     * @param typeName the type the picker chose
     */
    beginCreate(typeName: string): void {
        this.selectedTypeName.set(typeName);
        this.draft.set({ typeName, attributes: { qualifiedName: crypto.randomUUID() } });
        this.chosen.set([]);
    }
}
