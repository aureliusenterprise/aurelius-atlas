/**
 * WFE-06: the badge alias is a shared rule, not details' (DD-807). The unit
 * cases prove the rule itself (DET-26), and the last case proves the shape the
 * rule moved for: the editor tree never imports from the details feature, so a
 * details refactor cannot break the editor over a display rule.
 */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { cardTypeAlias } from "./type-alias";

describe("the badge alias (DET-26, WFE-06)", () => {
    it("reads the alias out of the entity's attributes (DET-26)", () => {
        expect(cardTypeAlias({ attributes: { typeAlias: "Dataset" } })).toBe("Dataset");
    });

    it("gives nothing when there is no usable alias (DET-26)", () => {
        expect(cardTypeAlias({ attributes: {} })).toBeUndefined();
        expect(cardTypeAlias({ attributes: undefined })).toBeUndefined();
        // An empty string is no alias: the badge shows the type name alone.
        expect(cardTypeAlias({ attributes: { typeAlias: "" } })).toBeUndefined();
        // A non-string is a broken metamodel value, not a badge.
        expect(cardTypeAlias({ attributes: { typeAlias: 7 } })).toBeUndefined();
    });

    it("reads it from the view shape too, the door the editor rides (DET-26, WFE-06)", () => {
        // Both doors give the same shape, so neither screen converts (WFE-06's point).
        expect(cardTypeAlias({ attributes: { typeAlias: "Data Entity" } })).toBe("Data Entity");
    });
});

describe("the editor's feature boundary (WFE-06, DD-807)", () => {
    it("the editor tree imports nothing from the details feature (WFE-06)", () => {
        // The shape app.config.spec.ts's APC-07 scan sets: the webapp's source,
        // read from disk, so the guard cannot be satisfied by a deleted test.
        const editorDir = join(process.cwd(), "apps/aurelius-atlas-webapp/src/app/search/editor");
        const sources = readdirSync(editorDir)
            .filter((entry) => entry.endsWith(".ts"))
            .map((entry) => ({ path: entry, text: readFileSync(join(editorDir, entry), "utf8") }));

        expect(sources.length).toBeGreaterThan(0);

        // `details/` (any path through it) is the details feature's tree.
        const reaching = sources
            .filter((source) => /from\s+["'][^"']*details\//.test(source.text))
            .map((source) => source.path);

        expect(reaching).toEqual([]);
    });
});
