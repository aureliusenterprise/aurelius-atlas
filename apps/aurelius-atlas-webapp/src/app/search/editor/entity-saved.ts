import { Injectable, signal } from "@angular/core";

/**
 * The one-way "this entity was saved" tick (DD-327): the editor drawer
 * fires it after a successful save so the details screen that stays mounted
 * underneath (EDT-01) re-reads its own entity — Angular reuses the route
 * (same URL, the drawer outlet only goes away), so without the tick the
 * landed details screen would paint the pre-edit entity.
 *
 * This is the deliberate exception to DD-322's no-shared-store rule: it
 * shares no entity data, only the event that one guid changed. The editor
 * and the details screen keep their separate reads; the tick cannot carry a
 * stale value into a screen (the consumer always re-reads from the server).
 */
@Injectable({ providedIn: "root" })
export class EntitySaved {
    /** The newest save: the guid, and a sequence so a repeat save re-fires. */
    readonly latest = signal<{ guid: string; seq: number } | null>(null);

    private seq = 0;

    /**
     * Announce a saved entity (the editor's save path, after the
     * classifications answer and before the navigation).
     * @param guid the entity that was written
     */
    notify(guid: string): void {
        this.seq += 1;
        this.latest.set({ guid, seq: this.seq });
    }
}
