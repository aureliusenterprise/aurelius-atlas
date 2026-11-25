/**
 * The entity editor's test world (7.46): the drawer's fixtures, the fake route,
 * and the settle helpers every editor spec shares — the read flushes (EDT-02,
 * VDE-01, VDE-02), the validation verdicts (VEV-02), and the audit pages
 * (AUD-08, HST-03, HST-08). Split out of the main spec so the History specs
 * (moved at 7.46) and the Entity specs ride the same setup; it is a test
 * module, not a spec, so it carries no `it()` of its own.
 */

import { HttpRequest } from "@angular/common/http";
import { HttpTestingController } from "@angular/common/http/testing";
import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { ActivatedRoute, ParamMap, RouterOutlet, convertToParamMap } from "@angular/router";
import { By } from "@angular/platform-browser";
import { Subject, of } from "rxjs";
import { Holdable } from "aurelius-atlas-ui";
import {
    type AtlasEntityDef,
    type EntityAuditEventV2,
    type AtlasEnumDef,
    type AtlasRelationshipAttributeDef,
    type AtlasRelationshipDef,
    type AtlasTypeDefHeader,
    type AtlasTypesDef,
    type EntityRelation,
    type EntityView,
    type ViewForTypeAnswer,
} from "aurelius-atlas-data-access";
import { EntityEditor } from "./entity-editor.component";
import {
    CHAIN_URL,
    CLASSIFICATION_SLICE_URL,
    ENTITY_HEADERS_URL,
    ENUM_SLICE_URL,
    RELATIONSHIP_SLICE_URL,
    VALIDATE_URL,
    VIEW_URL,
} from "../../../testing/api";
import { provideScreenTest } from "../../../testing/providers";

/** The test host for the routed-drawer specs that need a real router: the
 * `drawer` aux outlet, the way `app.component.html` carries it (DD-355). */
@Component({
    selector: "aurelius-atlas-webapp-drawer-test-host",
    imports: [RouterOutlet],
    template: `<router-outlet name="drawer" />`,
})
export class DrawerTestHost {}

/**
 * The edit-mode view of the DataSet (VDE-01): the read door's answer — the
 * card fields, its own values, its own tag names, and (in the RA fixtures)
 * its sections. The unique qualifiedName rides the card, not `attributes`;
 * `entityFromView` folds it back in for the form (VDE-01, DD-608).
 */
export const ANSWER: EntityView = {
    guid: "7a1b",
    typeName: "DataSet",
    superTypeNames: ["Asset", "Referenceable"],
    name: "genomic_variants",
    qualifiedName: "genomic_variants@cluster",
    displayText: "genomic_variants",
    status: "ACTIVE",
    createTime: 1_700_000_000_000,
    updateTime: 1_700_000_021_000,
    createdBy: "analyst-3",
    updatedBy: "analyst-3",
    classificationNames: ["PII"],
    stale: false,
    attributes: {
        name: "genomic_variants",
        description: "Curated variant calls.",
        owner: "analyst-3",
        displayName: "Genomic Variants",
    },
    sections: [],
};

/** The type defs the chain answers, the tag-box slice, and the picker slice
 * are all built from this bag. The supertype walk reads the chain the for-type
 * door answers (VDE-02, AVW-11), not the whole-typedefs dump of before. */
export const TYPEDEFS: AtlasTypesDef = {
    entityDefs: [
        {
            name: "Referenceable",
            attributeDefs: [{ name: "qualifiedName", typeName: "string", isUnique: true, isOptional: false }],
        },
        {
            name: "Asset",
            superTypes: ["Referenceable"],
            attributeDefs: [
                { name: "name", typeName: "string", isOptional: false },
                { name: "description", typeName: "string" },
                { name: "owner", typeName: "string" },
                { name: "displayName", typeName: "string" },
            ],
        },
        { name: "DataSet", superTypes: ["Asset"], attributeDefs: [] },
        { name: "Process", superTypes: ["Asset"], attributeDefs: [] },
        // Two metamodel types the icon map names (MMS-07): the only ones the
        // create picker offers (EDT-04 as scoped). `m4i_collection` extends
        // `m4i_dataset`, so picking the subtype loads the supertype whole and a
        // re-pick up the chain asks nothing (VDE-02's cache).
        { name: "m4i_dataset", superTypes: ["DataSet"], attributeDefs: [] },
        { name: "m4i_collection", superTypes: ["m4i_dataset"], attributeDefs: [] },
        { name: "AtlasGlossary", attributeDefs: [] },
        { name: "__AtlasHauskeeping", attributeDefs: [] },
    ],
    classificationDefs: [
        { name: "PII", entityTypes: ["DataSet"] },
        { name: "CONFIDENTIAL", entityTypes: ["Asset"] },
        { name: "FINANCE", entityTypes: ["Process"] },
    ],
    enumDefs: [],
    structDefs: [],
    businessMetadataDefs: [],
    relationshipDefs: [],
};

/** The classification slice the tag box reads (VDE-02, DD-611). */
export const CLASSIFICATION_SLICE = { classificationDefs: TYPEDEFS.classificationDefs };
/** The enum slice the form's enum fields read (VDE-02, DD-611): none shipped. */
export const ENUM_SLICE: { enumDefs: AtlasEnumDef[] } = { enumDefs: [] };
/** The relationship slice the pickers read the opposite end from (RPS-07):
 * none shipped, so no picker of these fixtures filters its search. */
export const RELATIONSHIP_SLICE: { relationshipDefs: AtlasRelationshipDef[] } = { relationshipDefs: [] };

/** The create picker's rows come from the entity typedef headers (VDE-02):
 * names only — headers carry no display name, so every label is the
 * `nameDisplay` of the name (DD-379 kept, DD-497's alias order mooted). */
export const ENTITY_HEADERS: AtlasTypeDefHeader[] = (TYPEDEFS.entityDefs ?? []).map((def) => ({ name: def.name }));

/** The supertype chain of one type, flattened the way the for-type door
 * answers it (`[name, *all_super_types]`, AVW-11): the whole typedefs, each
 * with the attributes it declares. */
export function chainFor(defs: AtlasTypesDef, name: string): ViewForTypeAnswer {
    const byName = new Map((defs.entityDefs ?? []).map((def) => [def.name, def]));
    const supertypes: AtlasEntityDef[] = [];
    const walk = (def: AtlasEntityDef): void => {
        for (const superName of def.superTypes ?? []) {
            const supertype = byName.get(superName);
            if (supertype !== undefined && !supertypes.includes(supertype) && supertype.name !== name) {
                supertypes.push(supertype);
                walk(supertype);
            }
        }
    };
    const type = byName.get(name);
    if (type === undefined) {
        throw new Error(`no fixture def for ${name}`);
    }
    walk(type);

    return { type, superTypes: supertypes };
}

/** The chain answer the DataSet drawer reads (edit and create share it). */
export const DATASET_CHAIN = chainFor(TYPEDEFS, "DataSet");

/** One enum typedef, its elements deliberately out of ordinal order so the
 * renderer's ordinal sort (EDT-03's enum kind, `form-fields.ts`) is pinned
 * rather than implied by the fixture's order. */
export const TIER_ENUM = {
    name: "tier",
    elementDefs: [
        { value: "gold", ordinal: 2 },
        { value: "bronze", ordinal: 0 },
        { value: "silver", ordinal: 1 },
    ],
};

/** The enum slice carrying {@link TIER_ENUM} (the plain `ENUM_SLICE` ships none). */
export const TIER_ENUM_SLICE: { enumDefs: AtlasEnumDef[] } = { enumDefs: [TIER_ENUM] };

/** The DataSet chain carrying every field kind the form renders (EDT-03):
 * the enum ({@link TIER_ENUM}), the mandatory boolean (whose `required` rule
 * the form skips on purpose), the SET multi, the mandatory number and the
 * date. The DataSet's own type has none of these, so the control render pins
 * in `entity-fields.component.spec.ts` ride this chain. */
export const ALL_KINDS_DEFS: AtlasTypesDef = {
    ...TYPEDEFS,
    entityDefs: TYPEDEFS.entityDefs!.map((def) =>
        def.name === "DataSet"
            ? {
                  ...def,
                  attributeDefs: [
                      { name: "tier", typeName: "tier" },
                      { name: "retired", typeName: "boolean", isOptional: false },
                      { name: "tags", typeName: "array<string>", cardinality: "SET" },
                      { name: "score", typeName: "int", isOptional: false },
                      { name: "when", typeName: "date" },
                  ],
              }
            : def,
    ),
};

/** The chain of {@link ALL_KINDS_DEFS}'s DataSet. */
export const ALL_KINDS_CHAIN = chainFor(ALL_KINDS_DEFS, "DataSet");

/** The edit view over the all-kinds type: one seeded value per kind (EDT-02's
 * seed reads each in its own shape — the number as a number, the date as epoch
 * ms, the multi as a list, the enum as its text). */
export const ALL_KINDS_ANSWER: EntityView = {
    ...ANSWER,
    attributes: {
        name: "genomic_variants",
        description: "Curated variant calls.",
        tier: "silver",
        retired: true,
        tags: ["a", "b"],
        score: 7,
        when: 1_700_000_000_000,
    },
};

/** The edit-mode view for the relationship pickers (EDT-13..EDT-17, VDE-04):
 * one ACTIVE end, one end on a non-ACTIVE entity (never seeded, EDT-15), and
 * an empty `model` section. The door carries the ends in `sections` only — no
 * stale `attributes` mirror (DD-340 retired with the Atlas read, VDE-04). */
export const RA_ANSWER: EntityView = {
    ...ANSWER,
    attributes: {
        name: "genomic_variants",
        owner: "analyst-3",
    },
    sections: [
        {
            attribute: "inputToProcesses",
            entities: [
                { guid: "p1", name: "load_events", typeName: "Process", status: "ACTIVE" },
                { guid: "p9", typeName: "Process", status: "DELETE_PENDING" },
            ],
        },
        { attribute: "model", entities: [] },
    ],
};

/** The DataSet chain carrying the derived relationship attributes (EDT-13):
 * the door answers them on the whole typedef (AVW-11). */
export function raChain(modelRequired = false): ViewForTypeAnswer {
    return chainFor(
        withDataSetRelationships(TYPEDEFS, [
            {
                name: "inputToProcesses",
                typeName: "array<Process>",
                cardinality: "SET",
                relationshipTypeName: "dataset_process_inputs",
            },
            { name: "model", typeName: "Process", isOptional: !modelRequired },
        ]),
        "DataSet",
    );
}

/** One def of the chain's DataSet stand-in, carrying relationship attributes. */
export type RaFixture = AtlasRelationshipAttributeDef & { name: string };

/** The shipped typedefs with the DataSet's derived ends swapped (the chain
 * walk needs the base defs beside it — Referenceable and Asset carry the
 * plain fields, so a wholesale entityDefs replacement breaks the form). */
export function withDataSetRelationships(defs: AtlasTypesDef, ends: RaFixture[]): AtlasTypesDef {
    return {
        ...defs,
        entityDefs: defs.entityDefs!.map((def) =>
            def.name === "DataSet" ? { ...def, relationshipAttributeDefs: ends } : def,
        ),
    };
}

/** The 18.3 parent choice on the same DataSet stand-in (PME-10): two `SINGLE`
 * ends of one `mutuallyExclusive` group — the shape the server derives from
 * `m4i_data_entity`'s `dataDomain` and `parentEntity` ends.
 * @param required whether both ends are mandatory (the PME-10 lock-out probe)
 */
export function parentChain(required = false): ViewForTypeAnswer {
    const group = [{ type: "mutuallyExclusive", params: { group: "m4i_data_entity_parent" } }];

    return chainFor(
        withDataSetRelationships(TYPEDEFS, [
            {
                name: "dataDomain",
                typeName: "m4i_data_domain",
                cardinality: "SINGLE",
                isOptional: !required,
                relationshipTypeName: "m4i_data_entity_assignment",
                constraints: group,
            },
            {
                name: "parentEntity",
                typeName: "DataSet",
                cardinality: "SINGLE",
                isOptional: !required,
                relationshipTypeName: "m4i_parent_entity_assignment",
                constraints: group,
            },
        ]),
        "DataSet",
    );
}

/** The stored view the parent-group probes edit: the DataSet's own values with
 * the two parent keys as sections — the shape 18.3's child entity reads as. */
export function parentAnswer(withDomain: boolean): EntityView {
    const sections: EntityRelation[] = [];
    if (withDomain) {
        sections.push({
            attribute: "dataDomain",
            entities: [{ guid: "d1", name: "Sales", typeName: "m4i_data_domain", status: "ACTIVE" }],
        });
    }
    sections.push({ attribute: "parentEntity", entities: [] });

    return {
        ...ANSWER,
        attributes: { name: "genomic_variants", owner: "analyst-3" },
        sections,
    };
}

/** The PME-10 search answer for a parent picker: one candidate of the target type. */
export function parentSearchResult(): Record<string, unknown> {
    return {
        cards: [{ guid: "e7", typeName: "DataSet", displayText: "parent_call", status: "ACTIVE", stale: false }],
        facets: {},
        total: 1,
    };
}

/**
 * Bring the drawer up in edit mode at the given guid (or create mode with
 * `create: true`): the route parts arrive through the fake ActivatedRoute, the
 * first `detectChanges` lets the effects fire the reads. The drawer's body
 * appears only after the drawer component renders the panel, so `arrive`
 * flushes the reads and settles the screen.
 */
export function setup({
    guid = "7a1b",
    create = false,
    createType = "",
    atlasWrite = true,
    query = {},
}: {
    guid?: string;
    create?: boolean;
    createType?: string;
    atlasWrite?: boolean;
    query?: Record<string, string>;
} = {}) {
    const paramMap = new Subject<ParamMap>();
    TestBed.configureTestingModule({
        imports: [EntityEditor],
        providers: [
            ...provideScreenTest({ keycloak: { atlasWrite } }),
            {
                provide: ActivatedRoute,
                useValue: {
                    paramMap,
                    queryParamMap: of(convertToParamMap(query)),
                    snapshot: { data: { editorMode: create ? "create" : "edit" } },
                },
            },
        ],
    });
    const fixture = TestBed.createComponent(EntityEditor);
    if (!create) {
        paramMap.next(convertToParamMap({ guid }));
    } else if (createType !== "") {
        paramMap.next(convertToParamMap({ type: createType }));
    }
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    return { fixture, compiled, httpMock: TestBed.inject(HttpTestingController), paramMap };
}

/** One verdict of the live answer (VEV-02, 12.7): the rule measuring `attribute`. */
export function govVerdict(attribute: string, message: string, compliant: boolean) {
    return {
        ruleGuid: `rule-${attribute}`,
        ruleName: `Rule - ${attribute}`,
        attribute,
        dimension: "COMPLETENESS",
        compliant,
        message,
    };
}

/** The engine's verdicts over four corpus rules (EDT-21/EDT-24 as amended by
 * 12.7 and 18.8, VEV-02): the drawer renders the two whose attributes name one
 * of its controls (name, description). */
export const VALIDATION = {
    verdicts: [
        govVerdict("dataEntity", "This entity is missing a dataEntity", false),
        govVerdict("description", "This entity has a description", true),
        govVerdict("domainLead", "This entity is missing a domainLead", false),
        govVerdict("name", "This entity has a name", true),
    ],
    unreadRules: [],
};

/** Answer every validate-entity call in flight (EDT-23): the open round fires
 * as soon as the form is visible, so the helpers settle it like any other
 * read. With no call pending it matches nothing (bare create, the failed
 * read), so the helpers stay honest about the request's absence. */
export function flushValidation(httpMock: HttpTestingController, body = VALIDATION): void {
    for (const request of httpMock.match((req) => req.url === VALIDATE_URL)) {
        request.flush(body);
    }
}

/** Flush the three slices the editor reads on open (VDE-02, DD-611) and settle. */
export function arriveSlices(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    validate = true,
    relationships = RELATIONSHIP_SLICE,
    enums = ENUM_SLICE,
) {
    httpMock.expectOne(CLASSIFICATION_SLICE_URL).flush(CLASSIFICATION_SLICE);
    httpMock.expectOne(ENUM_SLICE_URL).flush(enums);
    httpMock.expectOne(RELATIONSHIP_SLICE_URL).flush(relationships);
    httpMock.expectOne(ENTITY_HEADERS_URL).flush(ENTITY_HEADERS);
    fixture.detectChanges();
    if (validate) {
        flushValidation(httpMock);
        fixture.detectChanges();
    }
}

/** Flush the chain read for one type (VDE-02): the for-type door's answer. */
export function arriveChain(httpMock: HttpTestingController, typeName: string, chain: ViewForTypeAnswer): void {
    httpMock.expectOne(`${CHAIN_URL}${typeName}`).flush(chain);
}

/** Flush the slices and (create mode with a type) the chain: every mode's
 * type material, settled. */
export function arriveTypeDefs(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    createType = "",
    chain: ViewForTypeAnswer = DATASET_CHAIN,
    validate = true,
    relationships = RELATIONSHIP_SLICE,
) {
    arriveSlices(fixture, httpMock, false, relationships);
    if (createType !== "") {
        arriveChain(httpMock, createType, chain);
    }
    fixture.detectChanges();
    if (validate) {
        flushValidation(httpMock);
        fixture.detectChanges();
    }
}

/** Flush every read of edit mode (VDE-01, VDE-02) and settle the drawer: the
 * slices, the view (the chain follows from its type), and the open validation. */
export function arrive(
    fixture: { detectChanges: () => void },
    httpMock: HttpTestingController,
    view: EntityView = ANSWER,
    chain: ViewForTypeAnswer = DATASET_CHAIN,
    validate = true,
    relationships = RELATIONSHIP_SLICE,
    enums = ENUM_SLICE,
) {
    arriveSlices(fixture, httpMock, false, relationships, enums);
    httpMock.expectOne((request) => request.url.startsWith(VIEW_URL)).flush(view);
    // The chain is asked from the view's type (VDE-02): the effect fires on
    // the tick the answer lands on, so the request appears one settle later.
    fixture.detectChanges();
    arriveChain(httpMock, view.typeName, chain);
    fixture.detectChanges();
    if (validate) {
        flushValidation(httpMock);
        fixture.detectChanges();
    }
}

/** The door's answer to a save: the entity's live view (AVW-07, VDE-06). */
export function savedView(overrides: Partial<EntityView> = {}): EntityView {
    return { ...ANSWER, updateTime: 1_700_000_090_000, ...overrides };
}

/** The Atlas v2 audit read (7.35, HST-03): `GET /api/atlas/v2/entity/{guid}/audit`
 * — no `/guid/` segment, unlike the entity reads. Since 7.36 the read names
 * its page size explicitly (HST-08), so the plain URL carries `count=100`. */
export const AUDIT_BASE = "/api/atlas/v2/entity/7a1b/audit";
export const AUDIT_URL = `${AUDIT_BASE}?count=100`;

/** The matcher for the trail's next page (HST-08): the same read with the
 * oldest listed `eventKey` as its inclusive cursor.
 * @param startKey the cursor the pane should send
 */
export function auditPageRequest(startKey: string) {
    return (request: HttpRequest<unknown>) =>
        request.url === AUDIT_BASE &&
        request.params.get("startKey") === startKey &&
        request.params.get("count") === "100";
}

/** A newest-first page of `count` audit events ending at `newest` (HST-08):
 * a full page is the only one that keeps the scroll's sentinel shown, so the
 * scroll tests read a hundred events the way the server's page size gives it. */
export function auditPage(newest: number, count: number): EntityAuditEventV2[] {
    return Array.from({ length: count }, (_, index) => ({
        entityId: "7a1b",
        eventKey: `${newest - index}:0`,
        timestamp: newest - index,
        user: "analyst-3",
        action: "ENTITY_UPDATE",
    }));
}

/** The audit trail of the fixture entity, newest first as the server answers
 * it (AUD-08): the update, then the create. */
export const AUDIT_EVENTS: EntityAuditEventV2[] = [
    {
        entityId: "7a1b",
        eventKey: "1700000021000:0",
        timestamp: 1_700_000_021_000,
        user: "analyst-3",
        action: "ENTITY_UPDATE",
    },
    {
        entityId: "7a1b",
        eventKey: "1700000000000:0",
        timestamp: 1_700_000_000_000,
        user: "analyst-3",
        action: "ENTITY_CREATE",
    },
];

/** Click the drawer's History tab (HST-01): the switch a reader performs. */
export function openHistoryTab(compiled: HTMLElement, fixture: ComponentFixture<EntityEditor>): void {
    compiled.querySelector<HTMLButtonElement>("#editor-history-tab")!.click();
    fixture.detectChanges();
}

/** Click the drawer's Entity tab. */
export function openEntityTab(compiled: HTMLElement, fixture: ComponentFixture<EntityEditor>): void {
    compiled.querySelector<HTMLButtonElement>("#editor-entity-tab")!.click();
    fixture.detectChanges();
}

/**
 * The Delete button's hold directive instance, so a spec can fire `held`
 * the way the pointer sweep would (the hold timing itself is specced at the
 * directive, not re-tested here).
 */
export function holdDirective(fixture: ComponentFixture<EntityEditor>): Holdable {
    return fixture.debugElement.query(By.directive(Holdable)).injector.get(Holdable);
}
