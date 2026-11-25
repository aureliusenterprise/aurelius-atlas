import { ChangeDetectionStrategy, Component, inject, input, output } from "@angular/core";
import { DatePipe } from "@angular/common";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import {
    type Breadcrumb,
    Breadcrumbs,
    InfiniteScrollContainer,
    SortableTable,
    TableColumn,
    TableRow,
} from "aurelius-atlas-ui";
import { type EntityAuditEventV2 } from "aurelius-atlas-data-access";

import { typeIcon } from "../../meta/type-icons";
import { EditorState } from "../editor-state";
import { attributeLabels } from "../attribute-labels";
import { fieldLabel, type EditorLabels } from "../form-fields";
import {
    type AuditAttributeChange,
    type AuditProseChange,
    type AuditRelationshipChange,
    restoreOf,
} from "./audit-details";
import { auditActionDisplay } from "./audit-display";
import { type ProsePart, diffProse } from "./description-diff";
import { AuditTrail } from "./audit-state";

/**
 * The History tab's pane (HST-02..HST-16, DD-816, DD-872): the trail the
 * {@link AuditTrail} store holds, rendered in the legacy's Bulma media
 * anatomy — the change's label, the user, the time (HST-04) — inside the
 * results list's infinite-scroll container (UIC-21, HST-08), with each state
 * row's change list openable from the stored bodies the trail already holds
 * (HST-10, DD-821), the two change tables (HST-12, DD-823), the worded prose
 * diff (HST-15, HST-16, DD-825), and the single-attribute restore (HST-11,
 * DD-822).
 *
 * It renders and asks; it navigates and writes nothing. A restore press emits
 * the changed line ({@link restore}) and the shell performs the store's
 * single-attribute write; a relationship crumb press emits the end's guid
 * ({@link endOpened}) and the shell leaves the drawer for that entity. The
 * pane's strings stay byte-identical to the drawer's (the vendored
 * `components.editor.history.*` keys), and the pane's markup ids and classes
 * are what the e2e suite pins — they moved with the markup.
 */
@Component({
    imports: [Breadcrumbs, DatePipe, FontAwesomeModule, InfiniteScrollContainer, SortableTable, TableColumn, TableRow],
    selector: "aurelius-atlas-webapp-history-tab",
    templateUrl: "./history-tab.component.html",
    styleUrl: "./history-tab.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HistoryTab {
    readonly trail = input.required<AuditTrail>();

    /** The entity the change lists' crumbs are read against (HST-12): the
     * edited entity's guid, so the crumb of that entity prints as plain text
     * and never as a link back to the screen behind the drawer (UIC-11). */
    readonly activeGuid = input("");

    /** Whether a change-list line can offer a restore at all (HST-11, EDT-09):
     * the edit-mode drawer of a person who holds the entity-write privilege.
     * The shell answers — the pane never reads the write gate itself. */
    readonly restoreShown = input(false);

    /** A changed line's Restore was pressed (HST-11): the shell carries it to
     * the store's single-attribute write. */
    readonly restore = output<AuditAttributeChange>();

    /** A relationship line's crumb was pressed (HST-12): the shell opens that
     * entity's details screen and closes the drawer. */
    readonly endOpened = output<string>();

    /** The store the shell restores through (HST-11): the pane reads its
     * one-write-at-a-time rule for the buttons only — every write goes
     * through the shell. */
    private readonly state = inject(EditorState);

    /** Every field label the catalogue names (EDT-33): the change lists name
     * an attribute with the same localized word the form's field shows (EDT-33
     * again — HST-12), and the labels are locale data, not state. */
    private readonly labels: EditorLabels = attributeLabels();

    /** The audit row's change label (HST-04): the display map over the
     * event's raw action name, the legacy's `| translate` lookup. */
    protected auditActionLabel(event: EntityAuditEventV2): string {
        return auditActionDisplay(event.action) ?? "";
    }

    /** The container's sentinel label (HST-08): the results list's key, so
     * the trail pages with the same words every other paged list uses. */
    protected readonly auditLoadLabel = $localize`:@@search.components.infiniteScrollContainer.loadNextPage:Load next page...`;

    /** The change list's heading (HST-10). */
    protected readonly auditChangeLine = $localize`:@@search.components.editor.history.changes:Changes`;
    /** The change-list tables' page size (HST-12): one change list per audit
     * row is small, and the page is generous enough that the sortable table's
     * pagination bar never appears here — the rows are all shown. */
    protected readonly auditTablePage = 100;
    /** The row's own state, compared with the state before it (HST-10). */
    protected readonly auditNoChangesLine = $localize`:@@search.components.editor.history.noChanges:Nothing changed`;
    /** The row with no older state on screen (HST-10). */
    protected readonly auditNotLoadedLine = $localize`:@@search.components.editor.history.notLoaded:The earlier state is not loaded`;
    /** The row whose body the server cut down (HST-10, AUD-04). */
    protected readonly auditNotRecordedLine = $localize`:@@search.components.editor.history.notRecorded:The details are not recorded`;
    /** The change list's attribute section (HST-10). */
    protected readonly auditAttributesLine = $localize`:@@search.components.editor.history.attributes:Attributes`;
    /** The change list's relationship section (HST-10). */
    protected readonly auditRelationshipsLine = $localize`:@@search.components.editor.history.relationships:Relationships`;
    /** The change list's added line (HST-10). */
    protected readonly auditAddedLine = $localize`:@@search.components.editor.history.added:Added`;
    /** The change list's removed line (HST-10). */
    protected readonly auditRemovedLine = $localize`:@@search.components.editor.history.removed:Removed`;
    /** The change list's changed line (HST-12): the third action of the
     * attribute table, the one the changed row's `del`/`ins` pair shows. */
    protected readonly auditChangedLine = $localize`:@@search.components.editor.history.changed:Changed`;
    /** The attribute table's action header (HST-12). */
    protected readonly auditActionHeader = $localize`:@@search.components.editor.history.action:Action`;
    /** The attribute table's name header (HST-12): the table lists attributes,
     * so its first column names them — the plain word, without the required
     * star the editor's own field label for `name` carries (DD-356). */
    protected readonly auditNameHeader = $localize`:@@search.components.editor.history.name:Name`;
    /** The attribute table's value header (HST-12): the detail screen's own
     * Properties word for a stored value (DET-11). */
    protected readonly auditValueHeader = $localize`:@@search.details.components.properties.value:Value`;
    /** The relationship table's relationship header (HST-12): which relation-
     * ship attribute an end belongs to. */
    protected readonly auditRelationshipHeader = $localize`:@@search.components.editor.history.relationship:Relationship`;
    /** The relationship table's entity header (HST-12). */
    protected readonly auditEntityHeader = $localize`:@@search.components.editor.history.entity:Entity`;
    /** The chevron of an audit row's toggle (HST-10): the accordion's chevron,
     * shown by the state of the row it belongs to. */
    protected readonly faChevronDown = faChevronDown;
    /** The open chevron of an audit row's toggle (HST-10). */
    protected readonly faChevronUp = faChevronUp;

    /** The fold marker's words (HST-16): how many kept words a long run left
     * out. The helper stays locale-free, so the count's words live here. */
    protected wordsLeftOut(count: number): string {
        return $localize`:@@search.components.editor.history.wordsLeftOut:${count}:count: words left out`;
    }

    /** The parts of one prose change (HST-15, HST-16): the stored before and
     * after texts worded as kept, removed and added parts, so a one-sentence
     * fix shows the fix and not two whole texts. */
    protected proseParts(change: AuditProseChange): readonly ProsePart[] {
        return diffProse(change.from, change.to);
    }

    /** The restore button's text (HST-11). */
    protected readonly auditRestoreLine = $localize`:@@search.components.editor.history.restore:Restore`;

    /** The change lists' name for an attribute or relationship attribute
     * (HST-12): the same localized field label the form shows for it (EDT-33),
     * so a table line and the field it describes carry one word. The stored
     * wire name stays underneath — the crumb and the restore send it.
     * @param name the attribute's wire name
     * @returns the label to show */
    protected auditName(name: string): string {
        return fieldLabel(name, this.labels);
    }

    /** What one change-list line restores (HST-11): a changed row with a
     * single value the single-attribute door can take, and nothing else. */
    protected readonly restoreOf = restoreOf;

    /** Whether a restore line asks nothing right now (HST-11): one write at a
     * time, the rule the Save and Delete buttons already hold. The store
     * refuses a second write as well (DD-822). */
    protected restoreDisabled(): boolean {
        return this.state.saving() || this.state.deleting() || this.state.restoring() !== null;
    }

    /** Whether the restore of `change`'s attribute is the write in flight
     * (HST-11): the pressed line goes busy while it travels. */
    protected restoreBusy(change: AuditAttributeChange): boolean {
        return this.state.restoring() === change.name;
    }

    /** The restore's accessible name (HST-11): the button's text alone would
     * read the same for every line of a change list. The attribute rides the
     * table's own localized name, so the line the button sits on and the name
     * a screen reader speaks agree. */
    protected restoreLabel(change: AuditAttributeChange): string {
        return $localize`:@@search.components.editor.history.restoreAria:Restore ${this.auditName(change.name)}:name:`;
    }

    /**
     * The relationship line's entity as one breadcrumb crumb (HST-12):
     * the end's display text and its type icon, the anatomy every other
     * entity mention in the product uses (VDR-06, DET-26). The audit body
     * stores only the end's guid, type and display text, so the crumb is the
     * end alone and never its parent trail (DD-823).
     * @param change one relationship line of a change list
     */
    protected endCrumb(change: AuditRelationshipChange): Breadcrumb[] {
        const found = typeIcon(change.typeName ?? "");
        return [
            {
                guid: change.guid,
                name: change.entity,
                typeName: change.typeName ?? "",
                ...(found !== undefined ? { icon: found.icon, iconClass: found.classIcon } : {}),
            },
        ];
    }
}
