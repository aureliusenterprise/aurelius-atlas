import enUs from "../../../../tests/fixtures/en-US.json";

import { NAME_DISPLAY, nameDisplay } from "./type-display";

/**
 * The name-to-display map (DET-26, DET-19, DD-379). Parity source: the
 * legacy `| translate` over the Aurelius dictionary of `.scratch/aurelius`
 * (commit b057389828c10497dd52d9efd4c16547c282c005); the values below are
 * checked against the vendored dictionary itself (`tests/fixtures/
 * en-US.json`, DD-128) — the source the catalogue XLIFF is generated from,
 * so the English fallbacks here and the `nl-NL` translations there can
 * never drift from the dictionary apart.
 */
describe("type-display (DET-26, DET-19, DD-379)", () => {
    it("says every dictionary type and classification name by its dictionary value", () => {
        // The dictionary's own name keys: every m4i_* type and every
        // classification, with the English value the catalogue carries.
        const dictionary = enUs as Record<string, unknown>;
        const nameKeys = Object.keys(dictionary).filter(
            (key) => /^m4i_/.test(key) || key === "PII" || /_risk/.test(key) || key === "key_data",
        );
        expect(Object.keys(NAME_DISPLAY).sort()).toEqual(nameKeys.sort());
        for (const key of nameKeys) {
            expect(NAME_DISPLAY[key]).toBe(dictionary[key]);
        }
    });

    it("answers a mapped name with its display name", () => {
        expect(nameDisplay("m4i_data_attribute")).toBe("Data Attribute");
        expect(nameDisplay("m4i_dataset")).toBe("Dataset");
        expect(nameDisplay("PII")).toBe("Has PII");
        expect(nameDisplay("low_risk")).toBe("Low risk");
        expect(nameDisplay("key_data")).toBe("Is key");
    });

    it("leaves a name the dictionary never saw raw, as ngx-translate's missing key did", () => {
        expect(nameDisplay("DataSet")).toBe("DataSet");
        expect(nameDisplay("spark_process")).toBe("spark_process");
        expect(nameDisplay("CONFIDENTIAL")).toBe("CONFIDENTIAL");
    });

    it("passes nothing through as nothing", () => {
        expect(nameDisplay(undefined)).toBeUndefined();
    });

    it("never answers a mapped name with its raw spelling (the store stays raw, EDT-16)", () => {
        // The display map is display-only: consumers keep sending the raw
        // `typeName`; only these strings reach the rendered badge or chip.
        for (const [key, display] of Object.entries(NAME_DISPLAY)) {
            expect(typeof display).toBe("string");
            expect(display).not.toBe("");
            expect(nameDisplay(key)).toBe(display);
        }
    });
});
