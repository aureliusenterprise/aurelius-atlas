import { inject, Injectable, signal } from "@angular/core";
import { TypeDefsService, type AtlasEntityDef, type AtlasTypeDef } from "aurelius-atlas-data-access";

import { layoutForTypeName, type TypeLayout } from "./section-config";

/** A typedef answer: the definition, or null for a name without one. */
type TypeDefAnswer = AtlasTypeDef | null;

/**
 * The layout dispatch (DET-15, DD-366): the entity's type name selects a
 * layout — the name itself when it is one of the seven, else the first of
 * the seven found among the type's super types, walking the typedef
 * answers upward. Every other type, and every no-entity state, keeps the
 * DET-01 default layout (the store answers `undefined`).
 *
 * The walk reads `GET /v2/types/typedef/name/{name}` (APC-01: one URL, the
 * base the service carries), memoized per name — the typedef cache DET-15
 * names, kept here because `TypeDefsService` holds none, so no second
 * typedef call is ever made for one name. A name the server answers with
 * an error has no typedef and ends its branch: the built-ins
 * (`Referenceable`, `AtlasEntity`) raise `SYSTEM_TYPE` and the walk stops
 * there, never walking past the m4i roots.
 */
@Injectable()
export class DetailsLayoutState {
    private readonly typeDefs = inject(TypeDefsService);

    /** The typedef answers by name — DET-15's cache, one read per name. */
    private readonly typedefs = new Map<string, Promise<TypeDefAnswer>>();

    /** The entity type the layout answers for — the re-resolve guard. */
    private resolvedFor: string | null = null;

    /** The layout of the resolved entity type, or undefined (the default). */
    readonly layout = signal<TypeLayout | undefined>(undefined);

    /**
     * Resolve the layout for one entity type (DET-15): the direct hit
     * answers synchronously, a supertype walk on the next microtask — the
     * screen keeps the default chrome until the layout is known, so
     * dispatch never flashes a half-layout. Called on every entity
     * arrival; the same type answers from the guard, the cache, or the
     * layout without a second read. A no-entity state (null) resets to the
     * default.
     * @param typeName the entity's type name, or null for no entity
     */
    resolve(typeName: string | null): void {
        if (typeName === null) {
            this.resolvedFor = null;
            this.layout.set(undefined);
            return;
        }
        if (typeName === this.resolvedFor) {
            return;
        }

        const direct = layoutForTypeName(typeName);
        if (direct !== undefined) {
            this.resolvedFor = typeName;
            this.layout.set(direct);
            return;
        }

        this.resolvedFor = typeName;
        // The walk is in flight: the default chrome until it answers (DET-15
        // — dispatch never flashes the previous entity's half-layout).
        this.layout.set(undefined);
        void this.layoutOf(typeName).then((layout) => {
            if (this.resolvedFor === typeName) {
                this.layout.set(layout);
            }
        });
    }

    /**
     * The layout of one type name: a direct hit, else the first layout
     * among its super types' answers (the legacy dispatch's `getSuperTypes`
     * rule), breadth-deep in declaration order.
     * @param typeName the type name
     * @returns the layout, or undefined for the default
     */
    private async layoutOf(typeName: string): Promise<TypeLayout | undefined> {
        const direct = layoutForTypeName(typeName);
        if (direct !== undefined) {
            return direct;
        }

        const typedef = await this.typedefOf(typeName);
        const superTypes =
            typedef !== null && "superTypes" in typedef ? ((typedef as AtlasEntityDef).superTypes ?? []) : [];

        for (const superType of superTypes) {
            const found = await this.layoutOf(superType);
            if (found !== undefined) {
                return found;
            }
        }
        return undefined;
    }

    /**
     * The typedef of one name, memoized (DET-15's cache). A failed read —
     * a built-in's `SYSTEM_TYPE` among them — is a null answer, kept like
     * any other: one read per name.
     * @param typeName the type name
     * @returns the typedef, or null
     */
    private typedefOf(typeName: string): Promise<TypeDefAnswer> {
        const cached = this.typedefs.get(typeName);
        if (cached !== undefined) {
            return cached;
        }

        const answer = new Promise<TypeDefAnswer>((resolve) => {
            this.typeDefs.getTypeDefByName(typeName).subscribe({
                next: (typedef) => resolve(typedef),
                error: () => resolve(null),
            });
        });
        this.typedefs.set(typeName, answer);
        return answer;
    }
}
