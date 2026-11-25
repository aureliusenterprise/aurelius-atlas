import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { ClassificationChip } from "aurelius-atlas-ui";

import { PropagatedChips, type PropagatedChipEntry } from "../shared/propagated-chips.component";

/**
 * The classification chips row of the header: the opened entity's own tags as
 * plain chips, and the tags propagation brought (VDR-05, VDR-12, DV-197) as the
 * shared propagated-chips control, whose hoverable trigger names the entities
 * each came from (UIC-16, DD-836). The legacy header drew them as two rows; the
 * layout keeps them as one row (DD-834).
 *
 * A painter, not a store: both lists arrive from the screen (the entity's
 * classification names and the propagated entries, each filtered and
 * display-named there), and a source click re-emits its guid for the screen to
 * route — a card mounts the same control but must not open itself, so the mount
 * decides (DD-836). The row hides itself when both lists are empty, which needs
 * no store, only its two inputs. It injects no store, router, or client.
 */
@Component({
    imports: [ClassificationChip, PropagatedChips],
    selector: "aurelius-atlas-webapp-classification-chips",
    template: `
        @if (classifications().length > 0 || propagated().length > 0) {
            <div class="block aurelius-details-classifications field is-grouped is-grouped-multiline">
                @for (name of classifications(); track name) {
                    <div class="control">
                        <aurelius-atlas-ui-classification-chip [label]="name" />
                    </div>
                }
                <!-- The propagated tags ride the same row (VDR-12), marked by the
                     chip's own hoverable trigger (UIC-16) whose dropdown names the
                     entities each came from — the legacy header's separate
                     "Propagated Classifications" row, kept as one row here (DD-834).
                     The whole control is the shared part the cards mount too
                     (DD-836): icon, name and path per source row. -->
                <aurelius-atlas-webapp-propagated-chips
                    [entries]="propagated()"
                    (sourceClicked)="sourceClicked.emit($event)"
                />
            </div>
        }
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClassificationChips {
    /** The entity's own classification labels, display-named by the screen (VDR-05). */
    readonly classifications = input.required<string[]>();

    /** The propagated chips, each with its source entities (VDR-12, DD-836). */
    readonly propagated = input.required<PropagatedChipEntry[]>();

    /** The clicked source's guid (UIC-16) — the screen routes the screen. */
    readonly sourceClicked = output<string>();
}
