/**
 * EDT-33: every attribute label the editor can show rides the Aurelius
 * dictionary key `search.components.editor.attribute.<name>` in both locales.
 * This spec is the bridge between the code map and the catalogues: it reads
 * the same English fixture the completeness spec checks, so a label the map
 * carries without a catalogue entry, or with fallback text the catalogue does
 * not agree with, fails here (7-33, DD-722). The two catalogues themselves are
 * proven equal by `i18n-completeness.spec.ts`.
 */
import { describe, expect, it } from "vitest";

import attributeLabelsJson from "../../../../tests/fixtures/en-US.json";
import { attributeLabels } from "./attribute-labels";

/** The catalogue's editor attribute strings (SHL-08's reference fixture). */
const CATALOGUE = (
    attributeLabelsJson as unknown as {
        search: { components: { editor: { attribute: Record<string, string> } } };
    }
).search.components.editor.attribute;

describe("editor attribute labels (EDT-33, 7-33)", () => {
    const labels = attributeLabels();

    it("names only catalogue keys (EDT-33)", () => {
        const invented = Object.keys(labels).filter((name) => !(name in CATALOGUE));

        expect(invented).toEqual([]);
    });

    it("carries the catalogue's English text as every fallback (SHL-08)", () => {
        // The $localize fallback must match the catalogue's English source or
        // the completeness spec's "carries the Aurelius English text" rule and
        // the runtime label disagree for a missing translation.
        const drifted = Object.entries(labels).filter(([name, text]) => CATALOGUE[name] !== text);

        expect(drifted).toEqual([]);
    });

    it("labels the attributes the dictionary carries no displayName for (EDT-33)", () => {
        // The names the shipped typedefs never humanize (the dictionary leaves
        // them raw or absent): the map alone makes them readable (DD-722).
        expect(labels["processOwner"]).toBe("Process Owner");
        expect(labels["source"]).toBe("Source");
        expect(labels["system"]).toBe("System");
        expect(labels["hasPII"]).toBe("Has PII");
        expect(labels["isKeyData"]).toBe("Is Key Data");
        expect(labels["hasContent"]).toBe("Has Content");
        expect(labels["optionalField"]).toBe("Optional Field");
    });

    it("labels the base-model attributes the vendored Area0 never names (EDT-33)", () => {
        // Area0 is vendored and byte-pinned: its attributes carry no
        // displayName at all, so the catalogue is the only readable label.
        expect(labels["description"]).toBe("Description");
        expect(labels["owner"]).toBe("Owner");
        expect(labels["displayName"]).toBe("Display Name");
        expect(labels["userDescription"]).toBe("User Description");
    });

    it("fixes the dictionary's two legacy typos (DV-181)", () => {
        expect(labels["compliantMessage"]).toBe("Compliant Message");
        expect(labels["nonCompliantMessage"]).toBe("Non-compliant Message");
    });

    it("labels every relationship-attribute name the metamodel renders (EDT-34)", () => {
        // The picker labels share the same map (EDT-34): the names with no
        // displayName anywhere in the shipped metamodel.
        for (const name of ["inputToProcesses", "processOwner", "steward", "synonyms", "seeAlso"]) {
            expect(labels[name]).toBeTruthy();
        }
    });
});
