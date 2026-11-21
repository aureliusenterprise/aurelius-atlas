import { Injectable, signal } from "@angular/core";

/** What one finished write did to its entity (WFE-02, DD-803). */
export type EntityWriteOutcome = "saved" | "deleted";

/**
 * The one-way "this entity was written" tick (DD-327, DD-803): the editor
 * fires it after a successful save or delete so the screens that hear it
 * learn the outcome from the code that performed the write — never by
 * reading the alerts store (WFE-01, DD-802).
 *
 * The save half is DD-327's tick: the details screen that stays mounted
 * underneath (EDT-01) re-reads its own entity, because Angular reuses the
 * route and the landed details screen would otherwise paint the pre-edit
 * entity. The delete half (WFE-02) carries its outcome on the same event
 * rather than a second signal type, so one pattern covers "my write
 * finished" (DD-803's rejected alternative).
 *
 * This is the deliberate exception to DD-322's no-shared-store rule: it
 * shares no entity data, only the event that one guid changed. The editor
 * and the details screen keep their separate reads; the tick cannot carry a
 * stale value into a screen (the consumer always re-reads from the server).
 */
@Injectable({ providedIn: "root" })
export class EntityWritten {
    /** The newest write: the guid, its outcome, and a sequence so a repeat re-fires. */
    readonly latest = signal<{ guid: string; seq: number; outcome: EntityWriteOutcome } | null>(null);

    private seq = 0;

    /**
     * Announce a finished write (the editor's save and delete paths, after
     * the answer and before the navigation — a refusal fires nothing).
     * @param guid the entity that was written
     * @param outcome whether it was saved or deleted
     */
    notify(guid: string, outcome: EntityWriteOutcome): void {
        this.seq += 1;
        this.latest.set({ guid, seq: this.seq, outcome });
    }
}
