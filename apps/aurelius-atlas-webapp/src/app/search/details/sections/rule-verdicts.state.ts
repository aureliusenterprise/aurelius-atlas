import { computed, inject, Injectable, signal } from "@angular/core";
import { type EntityView, type RuleVerdict, RuleVerdictsService } from "aurelius-atlas-data-access";

/**
 * One verdict row of the opened rule (AVS-12, VDR-15): the door's answer as the
 * screen holds it. Re-exported for the screen's template and tests.
 */
export type { RuleVerdict };

/** The store's record: the opened rule, its rows, and whether a read is in flight. */
interface RuleVerdictsRecord {
    /** The entity the read was asked for — {@link rows}' re-load guard. */
    entity: EntityView | null;
    /** The door's rows, in the store's document id order (ASG-09). */
    rows: RuleVerdict[];
    /** Whether the verdict read is in flight. */
    loading: boolean;
}

/**
 * The rule page's verdict read (DET-51, DET-52, DET-55, DD-850): the opened
 * rule's stored governance verdicts, split into the two sets the legacy drew
 * and counted, and the score the chart shows.
 *
 * The legacy asked the retired `atlas-dev-gov-quality` engine twice — once per
 * verdict value — and read its counts off the engine's page metadata (DV-201).
 * One door call answers both sets now (VDR-14, ADR 071): the rows split on
 * `compliant`, the two counts are the two arrays' lengths, and the score is the
 * legacy's own formula over them. A rule judging nothing scores `0` where the
 * legacy computed `NaN` — the same pixels, no `NaN` (DET-51).
 *
 * The read is the screen's only one for the page (ADR 071 R5): the card lists
 * resolve their entities through the search door like every other box (DET-53),
 * which is the sections store's job (DD-848), not this store's. A failed read
 * keeps the page and renders both boxes empty at count `0` and score `0`,
 * quietly — DET-49's posture, DET-55. The store is per-screen (provided by
 * `Details`): {@link load} re-runs on every entity arrival, and a superseded
 * round paints nothing (the generation guard, DET-08's sibling).
 */
@Injectable()
export class DetailsRuleVerdictsState {
    private readonly verdicts = inject(RuleVerdictsService);

    /** The read generation: a re-load drops every in-flight answer. */
    private generation = 0;

    private readonly record = signal<RuleVerdictsRecord>({ entity: null, rows: [], loading: false });

    /** The door's rows for the opened rule, in store order (ASG-09). Empty without a rule. */
    readonly rows = computed(() => this.record().rows);

    /** Whether a verdict read is in flight (DET-52: the counts sit at `0` until it answers). */
    readonly loading = computed(() => this.record().loading);

    /** The rows the rule refuses — the Non-compliant box's seed (DET-51, DET-53). */
    readonly nonCompliantRows = computed(() => this.record().rows.filter((row) => row.compliant === false));

    /** The rows the rule passes — the Compliant box's seed (DET-51, DET-53). */
    readonly compliantRows = computed(() => this.record().rows.filter((row) => row.compliant === true));

    /**
     * The refused entities' GUIDs in door order — the Non-compliant box's
     * seed as the sections store takes it (DET-51, DET-53, DD-848).
     */
    readonly nonCompliantGuids = computed(() => this.nonCompliantRows().map((row) => row.entity));

    /** The passed entities' GUIDs in door order — the Compliant box's seed. */
    readonly compliantGuids = computed(() => this.compliantRows().map((row) => row.entity));

    /** The Non-compliant count — the stats bar's first heading (DET-52). */
    readonly nonCompliantCount = computed(() => this.nonCompliantRows().length);

    /** The Compliant count — the stats bar's second heading (DET-52). */
    readonly compliantCount = computed(() => this.compliantRows().length);

    /**
     * The chart's score, the legacy's formula (DET-51, DET-54): the compliant
     * share of the judged entities, 0..100, and `0` when the rule judges none.
     */
    readonly score = computed(() => {
        const compliant = this.compliantCount();
        const total = compliant + this.nonCompliantCount();
        return total === 0 ? 0 : (compliant / total) * 100;
    });

    /**
     * (Re-)read the verdicts of one entity (DET-51): the opened rule's GUID, or
     * nothing at all for no entity — a null entity or a non-rule clears the
     * page's two boxes (DD-850). Every arrival re-reads, the editor's save
     * re-read among them, the sections store's rule.
     * @param entity the opened entity, or null for every no-entity state
     */
    load(entity: EntityView | null): void {
        if (entity === null) {
            // The clear is idempotent: every other layout hands null on every
            // arrival (the screen's gate), and a page with nothing held has
            // nothing to drop. Re-setting the record would hand the sections
            // store's seed a new array identity and re-seed its boxes for
            // nothing.
            const held = this.record();
            if (held.entity === null && held.rows.length === 0 && !held.loading) {
                return;
            }
            this.generation++;
            this.record.set({ entity: null, rows: [], loading: false });
            return;
        }

        this.generation++;
        const generation = this.generation;
        this.record.set({ entity, rows: [], loading: true });
        this.verdicts.verdicts(entity.guid).subscribe({
            next: (answer) => {
                if (this.generation !== generation) {
                    return; // a newer arrival superseded this answer
                }
                this.record.set({ entity, rows: answer.verdicts ?? [], loading: false });
            },
            // DET-55 (DET-49's posture): a failed read keeps the page and
            // renders the boxes empty at count 0 — quietly, no alert. The
            // opened rule's own view already answered or the screen would not
            // be showing it.
            error: () => {
                if (this.generation !== generation) {
                    return;
                }
                this.record.set({ entity, rows: [], loading: false });
            },
        });
    }
}
