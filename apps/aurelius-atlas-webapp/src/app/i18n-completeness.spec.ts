/**
 * SHL-08: every Aurelius dictionary leaf must be present in both catalogues
 * with its Aurelius text, so a screen ported by a later slice can reference
 * any key and find it translated (DD-039). The vendored dictionaries under
 * tests/fixtures/ are the reference, checked offline. The components
 * dictionaries are the chrome strings of the shared-components library,
 * carried by the `aurelius-atlas-ui` components (DD-047, UIC-04).
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

import componentsEnUs from "../../tests/fixtures/components-en-US.json";
import componentsNlNl from "../../tests/fixtures/components-nl-NL.json";
import enUs from "../../tests/fixtures/en-US.json";
import nlNl from "../../tests/fixtures/nl-NL.json";

/**
 * A parsed XLIFF catalogue: trans-unit id to decoded source/target text.
 */
type Catalogue = Map<string, string>;

/**
 * Read and parse an XLIFF file next to this spec (src/locale/).
 * @param file The XLIFF file name.
 * @param field `source` for the template, `target` for the translated catalogue.
 * @returns A map of trans-unit id to decoded text.
 */
function parseXlf(file: string, field: "source" | "target"): Catalogue {
    // Nx runs vitest from the repo root; __dirname/import.meta.url are not the
    // spec's directory under the Angular builder, so resolve from the root.
    const path = resolve("apps/aurelius-atlas-webapp/src/locale", file);
    const doc = new DOMParser().parseFromString(readFileSync(path, "utf8"), "text/xml");

    const parserError = doc.querySelector("parsererror");
    if (parserError) {
        throw new Error(`${file} is not valid XML: ${parserError.textContent}`);
    }

    const catalogue: Catalogue = new Map();

    for (const unit of doc.querySelectorAll("trans-unit")) {
        const id = unit.getAttribute("id");
        const element = unit.querySelector(field);
        if (!id || !element) {
            throw new Error(`${file}: trans-unit without id or ${field}`);
        }
        if (catalogue.has(id)) {
            throw new Error(`${file}: duplicate trans-unit id ${id}`);
        }
        catalogue.set(id, decodeXliffText(element));
    }

    return catalogue;
}

/**
 * Decode the text of a `<source>`/`<target>` element: `<x id="n"/>` becomes
 * `{{n}}` (the Aurelius placeholder form), XML entity escapes decode to text.
 * @param element The XLIFF element.
 * @returns The decoded string.
 */
function decodeXliffText(element: Element): string {
    const inner = new XMLSerializer()
        .serializeToString(element)
        .replace(/^<[^>]+>/, "")
        .replace(/<\/[^>]+>$/, "");

    return inner
        .replace(/<x\b[^>]*\bid="([^"]*)"[^>]*\s*\/>/g, (_match, name: string) => `{{${name}}}`)
        .replace(/&quot;/g, '"')
        .replace(/&apos;/g, "'")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&amp;/g, "&");
}

/**
 * Flatten a nested dictionary into dotted key paths.
 * @param obj The dictionary.
 * @param prefix The current key path.
 * @param out The accumulator.
 * @returns The accumulator.
 */
function flatten(obj: Record<string, unknown>, prefix: string, out: Record<string, string>): Record<string, string> {
    for (const [key, value] of Object.entries(obj)) {
        const path = prefix ? `${prefix}.${key}` : key;
        if (typeof value === "string") {
            out[path] = value;
        } else {
            flatten(value as Record<string, unknown>, path, out);
        }
    }
    return out;
}

describe("Aurelius dictionary bridge", () => {
    const enLeaves = {
        ...flatten(enUs as Record<string, unknown>, "", {}),
        ...flatten(componentsEnUs as Record<string, unknown>, "", {}),
    };
    const nlLeaves = {
        ...flatten(nlNl as Record<string, unknown>, "", {}),
        ...flatten(componentsNlNl as Record<string, unknown>, "", {}),
    };
    const template = parseXlf("messages.xlf", "source");
    const translated = parseXlf("messages.nl-NL.xlf", "target");

    const enKeys = Object.keys(enLeaves).sort();

    it("has a trans-unit for every dictionary leaf, and no extras (SHL-08)", () => {
        expect([...template.keys()].sort()).toEqual(enKeys);
        expect([...translated.keys()].sort()).toEqual(enKeys);
    });

    it("carries the Aurelius English text in the en-US catalogue (SHL-08)", () => {
        const mismatches = enKeys.filter((key) => template.get(key) !== enLeaves[key]);

        expect(mismatches.map((key) => [key, enLeaves[key], template.get(key)])).toEqual([]);
    });

    it("carries the Aurelius Dutch text in the nl-NL catalogue (SHL-08)", () => {
        const mismatches = enKeys.filter((key) => translated.get(key) !== nlLeaves[key]);

        expect(mismatches.map((key) => [key, nlLeaves[key], translated.get(key)])).toEqual([]);
    });

    it("keeps the placeholder marker round-tripped", () => {
        expect(enLeaves["search.details.loading"]).toBe("Loading {{name}}...");
        expect(template.get("search.details.loading")).toBe("Loading {{name}}...");
        expect(translated.get("search.details.loading")).toBe(nlLeaves["search.details.loading"]);
    });

    it("preserves embedded newlines and line-end spaces in long strings (SHL-08)", () => {
        const key = "search.browse.technicalContext.infoModal.description";

        expect(enLeaves[key]).toContain(" \n\nThe technical data governance model");
        expect(template.get(key)).toBe(enLeaves[key]);
        expect(translated.get(key)).toBe(nlLeaves[key]);
    });

    it("uses only chrome strings the components dictionaries define (UIC-04, DD-047)", () => {
        // Every `@@components.*` id carried by an aurelius-atlas-ui template
        // must be a vendored chrome string — a component may not invent a
        // unit the translations do not have.
        const uiSrc = resolve("libs/angular/aurelius-atlas-ui/src");
        const invented: string[] = [];

        for (const file of readdirSync(uiSrc, { recursive: true })) {
            const name = String(file);
            if (!name.endsWith(".html")) continue;
            const html = readFileSync(join(uiSrc, name), "utf8");
            for (const match of html.matchAll(/@@components\.[\w.]+/g)) {
                const id = match[0].slice(2);
                if (!(id in enLeaves) || !(id in nlLeaves)) invented.push(`${name}: ${id}`);
            }
        }

        expect(invented).toEqual([]);
    });
});
