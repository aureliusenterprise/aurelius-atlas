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
        expect(labels["optionalField"]).toBe("Optional Field");
    });

    it("carries no label for a tag the type states only as a classification (ACA-05)", () => {
        // The m4i data attribute type retired these three attributes (18.6, DD-829), so the editor builds no
        // field for one and the map and catalogue hold no entry. The bare legacy dictionary keys stay.
        for (const name of ["hasPII", "isKeyData", "riskClassification"]) {
            expect(labels[name]).toBeUndefined();
            expect(name in CATALOGUE).toBe(false);
        }
    });

    it("carries no label for the field content flag the type no longer declares (FFB-05)", () => {
        // The m4i field type dropped `hasContent` (18.7, DD-830), so no field is built for it. Its bare
        // legacy dictionary key stays: the vendored Aurelius dictionary supplies it, and SHL-08 compares the
        // catalogues with each other, not with the model.
        expect(labels["hasContent"]).toBeUndefined();
        expect("hasContent" in CATALOGUE).toBe(false);
        // The flag that stays answers its own key, so the checkbox the boolean type brings is labelled (EDT-03).
        expect(labels["optionalField"]).toBe("Optional Field");
        expect(CATALOGUE["optionalField"]).toBe("Optional Field");
    });

    it("carries no label for the prose attribute the catalogue retired (SPA-07)", () => {
        // 18.8 (ADR 070) dropped `definition` from the m4i model, so no field
        // is built for it and its editor label is gone. Its bare legacy
        // dictionary siblings stay (the Placeholder/Warning pair comes from
        // the vendored Aurelius dictionary, DV-181), and SHL-08 compares the
        // catalogues with each other, not with the model. The one prose
        // attribute answers its own key, so the markdown field stays labelled.
        expect(labels["definition"]).toBeUndefined();
        expect("definition" in CATALOGUE).toBe(false);
        expect(labels["description"]).toBe("Description");
        expect(CATALOGUE["description"]).toBe("Description");
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

    it("gives the two people attributes labels that sort together (EDT-33, DD-727)", () => {
        // The pair that made EDT-03's raw-name order visibly wrong: by name
        // `steward` lands after `source`, but both labels read "Business Data
        // …", so a reader expects them side by side — and DD-727 sorts there.
        expect(labels["businessOwner"]).toBe("Business Data Owner");
        expect(labels["steward"]).toBe("Business Data Steward");
    });

    it("labels every relationship-attribute name the metamodel renders (EDT-34)", () => {
        // The picker labels share the same map (EDT-34): the names with no
        // displayName anywhere in the shipped metamodel.
        for (const name of ["inputToProcesses", "processOwner", "steward", "synonyms", "seeAlso"]) {
            expect(labels[name]).toBeTruthy();
        }
    });
});
