import { HttpErrorResponse } from "@angular/common/http";
import { Injectable, inject, signal } from "@angular/core";
import { AtlasEntitiesService, type AtlasEntity } from "aurelius-atlas-data-access";

import { AlertsService } from "../../alerts/alerts.service";

/**
 * The details screen's read store (DET-08, DET-13, DD-318): the legacy
 * `EntityDetailsService` ported to signals — the entity for one guid, in
 * flight, and the failure alert.
 *
 * The fetch follows the route's `:guid` (the URL is the screen's whole
 * address, DET-07): {@link load} is the one entry, called whenever the guid
 * changes. The guid is captured per call and compared before an answer
 * paints, so an answer for a superseded guid is dropped — the legacy
 * `latestEntityId` guard (DET-08). A failed read clears the entity and
 * adds an error alert (the `SearchState` idiom, DD-214's visible failure
 * path); a 404 answers no entity, which the screen renders as the DET-02
 * empty state. No route resolver, no cache: the legacy resolver only
 * cleared an API cache this client never had (DD-318).
 */
@Injectable()
export class DetailsState {
    private readonly entities = inject(AtlasEntitiesService);

    private readonly alerts = inject(AlertsService);

    /** The guid of the newest load — the stale-answer guard's key (DET-08). */
    private latestGuid = "";

    /** The entity the newest load answered, or null (DET-09). */
    readonly entity = signal<AtlasEntity | null>(null);

    /** Whether a load is in flight (DET-13's loading line). */
    readonly loading = signal(false);

    /**
     * Fetch the entity for one guid (DET-08): the newest load wins, a
     * superseded answer paints nothing.
     * @param guid the route's entity address
     */
    load(guid: string): void {
        this.latestGuid = guid;
        this.loading.set(true);
        this.entities.getEntityByGuid(guid).subscribe({
            next: (answer) => {
                this.loading.set(false);
                // The legacy stale-fetch guard: an answer for a guid the
                // route already left paints nothing (DET-08).
                if (this.latestGuid !== guid) {
                    return;
                }
                this.entity.set(answer.entity ?? null);
            },
            error: (error: unknown) => {
                this.loading.set(false);
                if (this.latestGuid !== guid) {
                    return;
                }
                // A failed read leaves no entity: the screen renders the
                // DET-02 empty state (DET-13). The server's 404 is the
                // feature's own not-found handling and stays out of the
                // drawer (ALR-05's 4xx rule); every other failure alerts,
                // named by the legacy retrieve line (the SearchState error
                // idiom, DD-214).
                this.entity.set(null);
                if (!isNotFound(error)) {
                    this.alerts.add({
                        severity: "error",
                        message: $localize`:@@search.services.entityDetails.retrieve:Retrieving the entity details`,
                        source: "search",
                    });
                }
            },
        });
    }
}

/**
 * Whether a failed read is the server's 404 (an unknown guid): the
 * screen's empty state answers it, the drawer does not (ALR-05's 4xx
 * rule, DET-13).
 * @param error the failed call's error
 * @returns whether the answer was 404
 */
function isNotFound(error: unknown): boolean {
    return error instanceof HttpErrorResponse && error.status === 404;
}
