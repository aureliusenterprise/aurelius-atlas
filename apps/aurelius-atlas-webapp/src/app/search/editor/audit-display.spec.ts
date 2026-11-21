/**
 * The audit-action display map (HST-04, DD-128): the legacy's
 * `audit.action | translate` over the Aurelius dictionary, ported the way
 * `type-display.ts` ported the type names. The values are checked against the
 * vendored dictionary itself (`tests/fixtures/en-US.json`, DD-128) — the
 * source the catalogue XLIFF is generated from — so the English fallbacks
 * here and the `nl-NL` translations there can never drift apart.
 */
import enUs from "../../../../tests/fixtures/en-US.json";

import { AUDIT_ACTION_DISPLAY, auditActionDisplay } from "./audit-display";

/** The dictionary's audit-action top-levels (the raw action names the legacy
 * looked up). `CLASSIFICATION_UDATE` is the legacy's own misspelling of
 * `CLASSIFICATION_UPDATE` — kept on both sides so the lookup lands exactly
 * where the legacy's landed. */
const AUDIT_KEYS = Object.keys(enUs as Record<string, unknown>).filter(
    (key) => /^[A-Z][A-Z_]+$/.test(key) && key.includes("_"),
);

describe("audit-display (HST-04, DD-128)", () => {
    it("says every audit action by its dictionary value", () => {
        const dictionary = enUs as Record<string, unknown>;

        expect(Object.keys(AUDIT_ACTION_DISPLAY).sort()).toEqual(AUDIT_KEYS.sort());
        for (const key of AUDIT_KEYS) {
            expect(AUDIT_ACTION_DISPLAY[key]).toBe(dictionary[key]);
        }
    });

    it("answers a mapped action with its display string", () => {
        expect(auditActionDisplay("ENTITY_CREATE")).toBe("Entity created");
        expect(auditActionDisplay("ENTITY_UPDATE")).toBe("Entity updated");
        expect(auditActionDisplay("CLASSIFICATION_ADD")).toBe("Classification added");
        expect(auditActionDisplay("PROPAGATED_CLASSIFICATION_DELETE")).toBe("Propagated classification deleted");
        expect(auditActionDisplay("CLASSIFICATION_UDATE")).toBe("Classification updated");
    });

    it("leaves an action the dictionary never saw raw, as ngx-translate's missing key did (HST-04)", () => {
        // The server's own spelling of the classification update is the
        // legacy's bug's twin: the dictionary never carried `CLASSIFICATION_UPDATE`,
        // so the legacy rendered the raw name and so does this map.
        expect(auditActionDisplay("CLASSIFICATION_UPDATE")).toBe("CLASSIFICATION_UPDATE");
        expect(auditActionDisplay("SOMETHING_NEW")).toBe("SOMETHING_NEW");
    });

    it("passes nothing through as nothing", () => {
        expect(auditActionDisplay(undefined)).toBeUndefined();
        expect(auditActionDisplay(null)).toBeUndefined();
    });

    it("never answers a mapped action with its raw spelling (the wire stays raw, AUD-06)", () => {
        // The map is display-only: the audit wire is read-only to the client
        // and every row keeps the event's own `action` untouched.
        for (const [key, display] of Object.entries(AUDIT_ACTION_DISPLAY)) {
            expect(typeof display).toBe("string");
            expect(display).not.toBe("");
            expect(display).not.toBe(key);
            expect(auditActionDisplay(key)).toBe(display);
        }
    });
});
