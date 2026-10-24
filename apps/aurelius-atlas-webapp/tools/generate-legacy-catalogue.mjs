/**
 * Generate the XLIFF catalogues from the vendored Aurelius dictionaries.
 *
 * The Aurelius interface localises through `@ngx-translate/core` with nested
 * flat-JSON dictionaries (DD-128). This workspace localises with the built-in
 * `@angular/localize`, whose catalogues the build compiles. This generator is
 * the bridge: it converts every dictionary leaf into one `<trans-unit>` whose
 * id is the dictionary key path, so a screen ported in a later slice can
 * reference a string with `i18n="@@<key.path>"` and the id lines up.
 *
 * Keying by the key path (not the English text) is deliberate: five English
 * values in the Aurelius dictionary repeat with differing Dutch translations,
 * so an id derived from the source text would collide.
 *
 * Run from the workspace root:
 *   node apps/aurelius-atlas-webapp/tools/generate-legacy-catalogue.mjs
 *
 * Idempotent: the output is a pure function of the two fixture JSON files.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const appRoot = join(here, "..");
const fixtures = join(appRoot, "tests", "fixtures");
const localeDir = join(appRoot, "src", "locale");

const en = JSON.parse(readFileSync(join(fixtures, "en-US.json"), "utf8"));
const nl = JSON.parse(readFileSync(join(fixtures, "nl-NL.json"), "utf8"));

// The Aurelius shared-components library shipped its own dictionary (the
// chrome strings of accordion, table shell, etc.). The `aurelius-atlas-ui`
// components carry those strings as `i18n="@@components.*"` units (DD-136),
// so the same keys must exist in the catalogues.
const enComponents = JSON.parse(readFileSync(join(fixtures, "components-en-US.json"), "utf8"));
const nlComponents = JSON.parse(readFileSync(join(fixtures, "components-nl-NL.json"), "utf8"));

// The Aurelius shell library shipped its own dictionary (the header/footer
// chrome strings). The webapp's shell chrome carries them as
// `i18n="@@shell.*"` units (7.11, SHC-07), so the same keys must exist in
// the catalogues.
const enShell = JSON.parse(readFileSync(join(fixtures, "shell-en-US.json"), "utf8"));
const nlShell = JSON.parse(readFileSync(join(fixtures, "shell-nl-NL.json"), "utf8"));

/**
 * Flatten a nested dictionary into `{ "a.b.c": "value" }`.
 * @param {Record<string, unknown>} obj The (sub)object to flatten.
 * @param {string} prefix The dotted key path of `obj`.
 * @param {Record<string, string>} out The accumulator.
 * @returns {Record<string, string>} The accumulator, filled in.
 */
function flatten(obj, prefix, out) {
    for (const [key, value] of Object.entries(obj)) {
        const path = prefix ? `${prefix}.${key}` : key;
        if (typeof value === "string") {
            out[path] = value;
        } else {
            flatten(value, path, out);
        }
    }
    return out;
}

/**
 * Escape a string for XML text content.
 * @param {string} text The raw string.
 * @returns {string} The XML-escaped string.
 */
function escapeXml(text) {
    return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

/**
 * Render a source/target string, turning Aurelius `{{placeholder}}` markers
 * into the XLIFF `<x>` placeholder element @angular/localize expects.
 * @param {string} text The raw string.
 * @param {boolean} isTarget When true, emit the target form (no equiv-text).
 * @returns {string} The rendered inner text of a `<source>`/`<target>`.
 */
function renderText(text, isTarget) {
    const escaped = escapeXml(text);
    // prettier-ignore
    return escaped.replace(/\{\{\s*([^}]+?)\s*\}\}/g, (_full, name) => // NOSONAR S5852: `[^}]+?` is bounded by the closing `}}` — Aurelius placeholders are short identifiers.
        isTarget
            ? `<x id="${escapeXml(String(name).trim())}"/>`
            : `<x id="${escapeXml(String(name).trim())}" equiv-text="{{${name}}}"/>`,
    );
}

/**
 * Encode spaces at the end of a physical line as `&#32;`.
 *
 * Aurelius strings contain embedded newlines, and some segments end in a
 * space ("...quality. \n\nThe technical..."). The pre-commit trailing-whitespace
 * hook (and Prettier) strip physical trailing spaces, which would silently
 * change the translated text; `&#32;` decodes to the same space in every XML
 * parser, so the text survives byte-faithfully.
 * @param {string} text The generated document.
 * @returns {string} The document with line-end spaces encoded.
 */
function encodeLineEndSpaces(text) {
    return (
        text
            .split("\n")
            // prettier-ignore
            .map((line) => line.replace(/ +$/, (spaces) => "&#32;".repeat(spaces.length))) // NOSONAR S5852: ` +$` scans one line (the split above) — bounded, no nested quantifier.
            .join("\n")
    );
}

const enFlat = { ...flatten(en, "", {}), ...flatten(enComponents, "", {}), ...flatten(enShell, "", {}) };
const nlFlat = { ...flatten(nl, "", {}), ...flatten(nlComponents, "", {}), ...flatten(nlShell, "", {}) };
// The keys are ASCII dotted paths; code-unit sort is the stable, review-friendly
// order the committed catalogues are keyed by.
const keys = Object.keys(enFlat).sort(); // NOSONAR S3798: see the note above.
const missingInNl = Object.keys(nlFlat).filter((k) => !(k in enFlat));
if (missingInNl.length > 0) {
    console.error(`ERROR: ${missingInNl.length} keys exist only in nl-NL:`, missingInNl.slice(0, 10));
    process.exit(1);
}

/**
 * Build a full XLIFF document for the given locale.
 * @param {string | null} targetLanguage `null` for the template (source-only).
 * @returns {string} The XLIFF document text.
 */
function buildXlf(targetLanguage) {
    const fileAttrs =
        `source-language="en-US" ` +
        (targetLanguage ? `target-language="${targetLanguage}" ` : "") +
        `datatype="plaintext" original="ng2.template"`;

    const units = keys.map((key) => {
        const id = escapeXml(key);
        const source = renderText(enFlat[key], false);
        const target = targetLanguage ? `        <target>${renderText(nlFlat[key], true)}</target>\n` : "";
        return (
            `      <trans-unit id="${id}" datatype="html">\n` +
            `        <source>${source}</source>\n` +
            target +
            `        <note priority="1" from="description">Aurelius dictionary key: ${id}</note>\n` +
            `      </trans-unit>\n`
        );
    });

    return (
        `<?xml version="1.0" encoding="UTF-8" ?>\n` +
        `<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">\n` +
        `  <file ${fileAttrs}>\n` +
        `    <body>\n` +
        units.join("") +
        `    </body>\n` +
        `  </file>\n` +
        `</xliff>\n`
    );
}

mkdirSync(localeDir, { recursive: true });
writeFileSync(join(localeDir, "messages.xlf"), encodeLineEndSpaces(buildXlf(null)));
writeFileSync(join(localeDir, "messages.nl-NL.xlf"), encodeLineEndSpaces(buildXlf("nl-NL")));

const missing = keys.filter((k) => typeof nlFlat[k] !== "string");
console.log(`Wrote ${keys.length} trans-units to messages.xlf and messages.nl-NL.xlf.`);
if (missing.length > 0) {
    console.error(`ERROR: ${missing.length} keys have no nl-NL translation:`, missing.slice(0, 10));
    process.exit(1);
}
