import { HttpErrorResponse } from "@angular/common/http";
import { Injectable, inject, signal } from "@angular/core";
import { type EntityView, ViewEntityService } from "aurelius-atlas-data-access";

import { AlertsService } from "../../alerts/alerts.service";

/**
 * The details screen's read store (DET-08, DET-13, DD-318, VDR-01): the
 * legacy `EntityDetailsService` ported to signals — the view for one guid,
 * in flight, and the failure alert — now reading the view family's door
 * (ADR 064) instead of the Atlas entity GET.
 *
 * The fetch follows the route's `:guid` (the URL is the screen's whole
 * address, DET-07): {@link load} is the one entry, called whenever the guid
 * changes. The guid is captured per call and compared before an answer
 * paints, so an answer for a superseded guid is dropped — the legacy
 * `latestEntityId` guard (DET-08). A failed read clears the entity and
 * adds an error alert (the `SearchState` idiom, DD-214's visible failure
 * path); a 404 answers no entity, which the screen renders as the DET-02
 * empty state (VDR-08). The view cache ADR 064 schedules lives in
 * {@link ViewEntityService}, not here (DD-605, which supersedes DD-318's
 * no-cache posture); this store keeps DD-318's fetch states untouched and
 * {@link reload} evicts one guid before re-reading, the editor's save tick
 * (DD-327, VDR-07).
 */
@Injectable()
export class DetailsState {
    private readonly views = inject(ViewEntityService);

    private readonly alerts = inject(AlertsService);

    /** The guid of the newest load — the stale-answer guard's key (DET-08). */
    private latestGuid = "";

    /** The view the newest load answered, or null (DET-09). */
    readonly entity = signal<EntityView | null>(null);

    /** Whether a load is in flight (DET-13's loading line). */
    readonly loading = signal(false);

    /**
     * Fetch the entity for one guid (DET-08): the newest load wins, a
     * superseded answer paints nothing. A cached guid answers without a
     * request (VDR-07, DD-605).
     * @param guid the route's entity address
     */
    load(guid: string): void {
        this.latestGuid = guid;
        this.loading.set(true);
        this.views.view(guid).subscribe({
            next: (view) => {
                this.loading.set(false);
                // The legacy stale-fetch guard: an answer for a guid the
                // route already left paints nothing (DET-08).
                if (this.latestGuid !== guid) {
                    return;
                }
                this.entity.set(view);
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

    /**
     * Re-read one guid the screen just saw change (VDR-07, DD-327): the
     * editor's save tick drops the cached view first, so the answer is the
     * door's, not the memory's. Every other arrival rides {@link load}.
     * @param guid the entity the editor saved
     */
    reload(guid: string): void {
        this.views.evict(guid);
        this.load(guid);
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
