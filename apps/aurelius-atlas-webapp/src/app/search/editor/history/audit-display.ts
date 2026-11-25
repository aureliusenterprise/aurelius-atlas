/**
 * The display string of every audit action — the legacy's `| translate` over
 * the audit event's `action` field (`editor.component.html`, its history
 * template), ported to the `$localize` catalogue bridge (DD-128, DD-379) the
 * way `type-display.ts` did for type names.
 *
 * The audit actions are the legacy's own dictionary top-levels, so the keys
 * are the raw action names. The catalogue carries nineteen of them in both
 * locales, `CLASSIFICATION_UDATE` among them: that key is the legacy's own
 * misspelling of `CLASSIFICATION_UPDATE`, kept on both sides so the lookup
 * still lands. An action outside the map keeps its raw spelling, the answer
 * the legacy's translate pipe gives a key the catalogue never saw.
 *
 * The resolver answers display strings only: the values stored or sent never
 * change (the audit wire is read-only to the client, AUD-06).
 */
export const AUDIT_ACTION_DISPLAY: Record<string, string> = {
    BUSINESS_ATTRIBUTE_UPDATE: $localize`:@@BUSINESS_ATTRIBUTE_UPDATE:Business attribute updated`,
    CLASSIFICATION_ADD: $localize`:@@CLASSIFICATION_ADD:Classification added`,
    CLASSIFICATION_DELETE: $localize`:@@CLASSIFICATION_DELETE:Classification deleted`,
    CLASSIFICATION_UDATE: $localize`:@@CLASSIFICATION_UDATE:Classification updated`,
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
 * Resolve an audit action's display string (HST-04): the legacy's
 * `action | translate` lookup over the dictionary above.
 * @param action the raw action name the audit event carries, or nothing
 */
export function auditActionDisplay(action: string): string;
export function auditActionDisplay(action: string | null | undefined): string | undefined;
export function auditActionDisplay(action: string | null | undefined): string | undefined {
    return action !== undefined && action !== null && Object.hasOwn(AUDIT_ACTION_DISPLAY, action)
        ? AUDIT_ACTION_DISPLAY[action]
        : (action ?? undefined);
}
