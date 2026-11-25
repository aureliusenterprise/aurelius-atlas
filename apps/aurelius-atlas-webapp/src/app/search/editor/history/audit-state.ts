import { DestroyRef, Injectable, computed, inject, signal } from "@angular/core";
import { type Subscription } from "rxjs";
import { type EntityAuditEventV2, AtlasEntitiesService } from "aurelius-atlas-data-access";

import { type AlertNotice } from "../../shared/alert-on-failure";
import { type AuditChanges, auditRowKey, auditTrailChanges, isStateAction } from "./audit-details";

/** The audit page size (HST-08, DD-820): what the endpoint itself reads an
 * absent `count` as (AUD-08), asked explicitly so the short-page test for the
 * trail's end is exact rather than a guess about the server's default. */
const AUDIT_PAGE = 100;

/** The trail's loading line and its failure alert (HST-05, HST-06): the
 * vendored audit-retrieve string, one key for both states. The shell's
 * loading output reads the same const (the pane's persistent region, LR-002).
 */
export const AUDIT_RETRIEVE_LINE = $localize`:@@search.services.entityAudit.retrieve:Retrieving the audit log`;

/**
 * The History tab's read store (HST-03..HST-10, DD-817, DD-820): the trail of
 * one entity, paged from the Atlas v2 audit endpoint through the same doors
 * the drawer's own audit read rode before 7.46 lifted them out of the
 * component (DD-872). The drawer asks it once per History visit (HST-03: no
 * caching rule applies, and a switch while a read runs does not repeat it),
 * and the infinite-scroll container asks it for the older pages the key
 * cursor still has (HST-08). The rows ride the server's newest-first answer
 * untouched (AUD-08); the open rows (HST-10) and the derived change lists
 * (DD-821) live here because they are state, not markup.
 *
 * A failed read holds its failure for the shell's relay (DD-871's seam,
 * HST-06's alert) — never a second one while one already waits, so a
 * failed-next-page followed by a failed retry groups as the drawer always
 * showed it (ALR-03).
 */
@Injectable()
export class AuditTrail {
    private readonly entities = inject(AtlasEntitiesService);

    /** The trail's events (HST-03), newest first as the server answered them
     * (AUD-08) — the client never re-sorts. */
    readonly audits = signal<readonly EntityAuditEventV2[]>([]);

    /** Whether the audit read is in flight (HST-05's loading line). */
    readonly auditsLoading = signal(false);

    /** Whether the trail is ended: the last page came back short, so the
     * container hides its sentinel and no older read fires (HST-08). */
    readonly auditsAllLoaded = signal(false);

    /** The audit rows whose change list is open (HST-10): keyed by the row's
     * `eventKey`, so more than one row can be open at once and a next page
     * leaves the rows already open alone. */
    readonly auditsOpen = signal<ReadonlySet<string>>(new Set());

    /** The failed read awaiting the shell's relay (DD-871), oldest first. */
    readonly failures = signal<readonly AlertNotice[]>([]);

    /** Mark the held failures shown ({@link alertOnFailure}, DD-871). */
    handled(): void {
        this.failures.set([]);
    }

    /** The change list of every state row (HST-10, DD-821): derived from the
     * trail already loaded, keyed by the row's `eventKey`, so the template
     * reads a row's answer by the key it already tracks on. No request — the
     * stored bodies of the rows on screen are the only input (AUD-06). */
    readonly auditChanges = computed<ReadonlyMap<string, AuditChanges>>(() => auditTrailChanges(this.audits()));

    /** The in-flight audit read (HST-03): a switch while one runs does not
     * repeat it, and the drawer's teardown drops the answer it no longer
     * needs — the constructor's onDestroy unsubscribes. */
    private auditsPending: Subscription | null = null;

    /** The entity the trail was opened for — what {@link loadMore} pages
     * with. Opened afresh on every History visit (HST-03). */
    private guid = "";

    constructor() {
        // The audit read does not outlive the drawer (HST-03).
        inject(DestroyRef).onDestroy(() => this.auditsPending?.unsubscribe());
    }

    /**
     * Open the trail of one entity (HST-03 as amended by 7.36, DD-817,
     * DD-820): every History visit re-reads the newest page — no caching rule
     * applies — and an in-flight read is never repeated. The read is one
     * `GET /v2/entity/{guid}/audit` asked with `count=100` and never an
     * `offset` or `sortBy`, which would move the server onto its sorted,
     * oldest-first path (AUD-07). A failed read holds its failure once and
     * leaves the list empty (HST-06).
     * @param guid the entity whose trail the pane lists
     */
    open(guid: string): void {
        if (!guid || this.auditsPending !== null) {
            return;
        }
        this.guid = guid;
        this.audits.set([]);
        this.auditsAllLoaded.set(false);
        this.read(undefined);
    }

    /**
     * The container's ask (HST-08): one more page of the trail, from the
     * oldest listed `eventKey` as the endpoint's inclusive cursor (AUD-08),
     * appended minus the one event that cursor repeats. A page shorter than
     * the ask ends the trail, so the container hides its sentinel. A failed
     * page holds its failure and keeps the rows and the sentinel, so the ask
     * can be made again. The container suppresses its own triggers while a
     * page is in flight, and the in-flight guard below repeats that, so one
     * scroll asks for one page.
     */
    loadMore(): void {
        if (!this.guid || this.auditsAllLoaded() || this.auditsPending !== null) {
            return;
        }
        // The cursor is the oldest listed eventKey (AUD-08). With nothing
        // listed there is no cursor to send, which is the fresh first-page ask
        // the sentinel's retry of a failed first read needs (HST-06). An event
        // listed without a key can carry no cursor, so the pane stops paging
        // rather than re-asking for the page it already holds.
        const listed = this.audits();
        const oldestKey = listed.at(-1)?.eventKey ?? undefined;
        if (listed.length > 0 && oldestKey === undefined) {
            this.auditsAllLoaded.set(true);
            return;
        }
        this.read(oldestKey);
    }

    /** One page of the trail, fresh (no cursor) or older (`startKey` the
     * oldest listed event). The shared body of {@link open} and
     * {@link loadMore} — the guard of the caller that reached here ran. */
    private read(startKey: string | undefined): void {
        const query = startKey === undefined ? { count: AUDIT_PAGE } : { count: AUDIT_PAGE, startKey };
        this.auditsLoading.set(true);
        this.auditsPending = this.entities.getAuditEvents(this.guid, query).subscribe({
            next: (events) => {
                this.auditsPending = null;
                this.auditsLoading.set(false);
                const listed = new Set(this.audits().map((event) => event.eventKey));
                const fresh = events.filter((event) => !listed.has(event.eventKey));
                this.audits.update((current) => [...current, ...fresh]);
                // The short page is the entity's oldest one (HST-08): the
                // sentinel goes, and nothing older is asked for. A full page
                // keeps the sentinel even when the trail ends there — a dead
                // ask costs one read and no data (DD-820).
                this.auditsAllLoaded.set(events.length < AUDIT_PAGE);
            },
            error: () => {
                this.auditsPending = null;
                this.auditsLoading.set(false);
                this.failures.update((held) => [...held, { severity: "error", message: AUDIT_RETRIEVE_LINE }]);
            },
        });
    }

    /** What an open row says (HST-10): the trail's answer for it, or the
     * not-recorded line for a state row whose stored body cannot be read —
     * a row that offers a toggle never opens onto nothing. */
    changeOf(event: EntityAuditEventV2): AuditChanges {
        return this.auditChanges().get(auditRowKey(event)) ?? { kind: "partial" };
    }

    /** Whether a row shows a change list toggle (HST-10): the four
     * entity-state actions carry a stored state to open, and only their rows
     * offer it. Any other row keeps the label, the user and the time of 7.35
     * (HST-04). */
    changeShown(event: EntityAuditEventV2): boolean {
        return isStateAction(event.action);
    }

    /** Whether a row's change list is open (HST-10). */
    changeOpen(event: EntityAuditEventV2): boolean {
        return this.auditsOpen().has(auditRowKey(event));
    }

    /** Open or close one row's change list (HST-10). The other rows keep
     * whatever state they are in — a trail can hold several open rows. */
    toggleChanges(event: EntityAuditEventV2): void {
        const key = auditRowKey(event);
        this.auditsOpen.update((open) => {
            const next = new Set(open);
            if (next.has(key)) {
                next.delete(key);
            } else {
                next.add(key);
            }

            return next;
        });
    }

    /** The id of the row at `index`'s change list (HST-10), paired with its
     * toggle's `aria-controls` the way the accordion pairs them
     * (FORM-CUSTOM-001). The pane's index in the list is unique among the rows
     * and does not move when a next page appends, so it is the stable half of
     * the pair — an event's `eventKey` would be, but it can be absent. */
    paneId(index: number): string {
        return `aurelius-editor-audit-changes-${index}`;
    }
}
