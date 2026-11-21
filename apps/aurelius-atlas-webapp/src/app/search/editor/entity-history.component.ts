import { DatePipe } from "@angular/common";
import { ChangeDetectionStrategy, Component, effect, inject, input, signal, untracked } from "@angular/core";
import { AtlasEntitiesService, EntityAuditEventV2 } from "aurelius-atlas-data-access";
import { firstValueFrom } from "rxjs";

/** How many events one audit read asks for (EDP-20, the legacy's `retrieveAuditsPaged`). */
export const HISTORY_PAGE = 100;

/**
 * The action labels (EDP-21): the legacy dictionary's top-level keys, one per
 * audit action. The legacy keys the classification update as `CLASSIFICATION_UDATE`.
 */
const ACTION_LABELS: Readonly<Record<string, string>> = {
    BUSINESS_ATTRIBUTE_UPDATE: $localize`:@@BUSINESS_ATTRIBUTE_UPDATE:Business attribute updated`,
    CLASSIFICATION_ADD: $localize`:@@CLASSIFICATION_ADD:Classification added`,
    CLASSIFICATION_DELETE: $localize`:@@CLASSIFICATION_DELETE:Classification deleted`,
    CLASSIFICATION_UPDATE: $localize`:@@CLASSIFICATION_UDATE:Classification updated`,
    CUSTOM_ATTRIBUTE_UPDATE: $localize`:@@CUSTOM_ATTRIBUTE_UPDATE:Custom attribute updated`,
    ENTITY_CREATE: $localize`:@@ENTITY_CREATE:Entity created`,
    ENTITY_DELETE: $localize`:@@ENTITY_DELETE:Entity deleted`,
    ENTITY_IMPORT_CREATE: $localize`:@@ENTITY_IMPORT_CREATE:Entity created by import`,
    ENTITY_IMPORT_DELETE: $localize`:@@ENTITY_IMPORT_DELETE:Entity deleted by import`,
    ENTITY_IMPORT_UPDATE: $localize`:@@ENTITY_IMPORT_UPDATE:Entity updated by import`,
    ENTITY_PURGE: $localize`:@@ENTITY_PURGE:Entity purged`,
    ENTITY_UPDATE: $localize`:@@ENTITY_UPDATE:Entity updated`,
    LABEL_ADD: $localize`:@@LABEL_ADD:Label added`,
    LABEL_DELETE: $localize`:@@LABEL_DELETE:Label deleted`,
    PROPAGATED_CLASSIFICATION_ADD: $localize`:@@PROPAGATED_CLASSIFICATION_ADD:Propagated classification added`,
    PROPAGATED_CLASSIFICATION_DELETE: $localize`:@@PROPAGATED_CLASSIFICATION_DELETE:Propagated classification deleted`,
    PROPAGATED_CLASSIFICATION_UPDATE: $localize`:@@PROPAGATED_CLASSIFICATION_UPDATE:Propagated classification updated`,
    TERM_ADD: $localize`:@@TERM_ADD:Term added`,
    TERM_DELETE: $localize`:@@TERM_DELETE:Term deleted`,
};

/**
 * The label of one audit action (EDP-21): the dictionary's, or the action itself when the dictionary has none.
 * @param action the event's action
 * @returns the label to show
 */
export function actionLabel(action: string | null | undefined): string {
    return action ? (ACTION_LABELS[action] ?? action) : "";
}

/**
 * The editor page's History tab (EDP-19 to EDP-22): the entity's audit events,
 * newest first, each its action, its user and its time. Every page of
 * {@link HISTORY_PAGE} events is read until one comes back short, the legacy's
 * walk. A changed `reload` reads them again (after a save on the page); a
 * failed read shows an empty list and says nothing (EDP-22).
 */
@Component({
    imports: [DatePipe],
    selector: "aurelius-atlas-webapp-entity-history",
    template: `
        @for (event of events(); track $index) {
            <div class="media aurelius-editor-history-event">
                <div class="media-content">
                    <div class="content">
                        <h6 class="title is-6">{{ label(event.action) }}</h6>
                        <p>
                            <small>
                                <span>{{ event.user }}</span>
                                ·
                                <span>{{ event.timestamp | date: "yyyy-MM-dd HH:mm:ss" }}</span>
                            </small>
                        </p>
                    </div>
                </div>
            </div>
        }
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityHistory {
    /** The entity whose history the tab lists. */
    readonly guid = input.required<string>();

    /** A counter the page bumps after a save, so the list is read again (EDP-22). */
    readonly reload = input(0);

    private readonly entities = inject(AtlasEntitiesService);

    /** The events read, newest first. */
    protected readonly events = signal<readonly EntityAuditEventV2[]>([]);

    protected readonly label = actionLabel;

    constructor() {
        effect(() => {
            const guid = this.guid();
            this.reload();
            untracked(() => void this.read(guid));
        });
    }

    private async read(guid: string): Promise<void> {
        const all: EntityAuditEventV2[] = [];
        try {
            for (let offset = 0; ; offset += HISTORY_PAGE) {
                const page = await firstValueFrom(
                    this.entities.getAuditEvents(guid, { count: HISTORY_PAGE, offset, sortOrder: "DESC" }),
                );
                all.push(...page);
                if (page.length < HISTORY_PAGE) {
                    break;
                }
            }
        } catch {
            this.events.set([]);
            return;
        }
        this.events.set(all);
    }
}
