import { describe, expect, it } from "vitest";

import {
    addTextMetadata,
    binaryStringToBytes,
    bytesToBinaryString,
    createChunk,
    crc32,
    isPng,
    joinChunk,
    splitChunk,
} from "./png-metadata";

/**
 * LDG-31: the PNG tEXt writer, over a minimal real PNG — the signature,
 * one IHDR, one IDAT, and the IEND the metadata lands before. The bytes
 * are built with the module's own join so the roundtrip pins both halves.
 */
/** A minimal, well-formed PNG: signature + IHDR + IDAT + IEND. */
function minimalPng(): string {
    // A 1x1 transparent image's real chunk payloads.
    const ihdr = String.fromCharCode(...[0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0]);
    const idat = String.fromCharCode(0x78, 0x9c, 0x62, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01);
    return joinChunk([createChunk("IHDR", ihdr), createChunk("IDAT", idat), createChunk("IEND", "")]);
}

describe("png-metadata (LDG-31)", () => {
    it("LDG-31: crc32 matches the standard check vector", () => {
        // The canonical CRC-32 test: "123456789" → 0xCBF43926 (the value
        // every table-driven implementation must answer).
        expect(crc32("123456789")).toBe(0xcbf43926);
        // The empty string's CRC is 0.
        expect(crc32("")).toBe(0);
    });

    it("LDG-31: a PNG splits into its chunks and rejoins byte-identically", () => {
        const png = minimalPng();
        expect(isPng(png)).toBe(true);
        const chunks = splitChunk(png);
        expect(chunks.map((chunk) => chunk.type)).toEqual(["IHDR", "IDAT", "IEND"]);
        // Each chunk's stored CRC is the one the writer computed over
        // type+data (the PNG spec's rule the legacy carries).
        for (const chunk of chunks) {
            expect(chunk.crc).toBe(crc32(chunk.type + chunk.data));
        }
        expect(joinChunk(chunks)).toBe(png);
    });

    it("LDG-31: the metadata lands as tEXt chunks before IEND (roundtrip)", () => {
        const png = minimalPng();
        const out = addTextMetadata(png, {
            Title: "Lineage",
            Author: "analyst-3@example.com",
            "Creation Time": "1780000000000",
        });

        // Re-split: the original chunks first, one tEXt per field, IEND last.
        const chunks = splitChunk(out);
        expect(chunks.map((chunk) => chunk.type)).toEqual(["IHDR", "IDAT", "tEXt", "tEXt", "tEXt", "IEND"]);
        const texts = chunks.filter((chunk) => chunk.type === "tEXt");
        // The keyword NUL value shape, verbatim.
        expect(texts[0]?.data).toBe("Title\u0000Lineage");
        expect(texts[1]?.data).toBe("Author\u0000analyst-3@example.com");
        expect(texts[2]?.data).toBe("Creation Time\u00001780000000000");
        for (const text of texts) {
            expect(text.crc).toBe(crc32("tEXt" + text.data));
        }
    });

    it("LDG-31: fields with no value ship no chunk (the legacy's skip)", () => {
        const png = minimalPng();
        const out = addTextMetadata(png, {
            Title: "Lineage",
            Author: "",
            Description: "",
            Software: "Aurelius Atlas/atlas/1.0.0",
        });
        const texts = splitChunk(out).filter((chunk) => chunk.type === "tEXt");
        expect(texts.map((chunk) => chunk.data)).toEqual([
            "Title\u0000Lineage",
            "Software\u0000Aurelius Atlas/atlas/1.0.0",
        ]);
    });

    it("LDG-31: non-PNG bytes are refused", () => {
        expect(() => splitChunk("GIF89a....")).toThrow();
        expect(() => addTextMetadata("not a png", { Title: "x" })).toThrow();
        // A PNG that lost its IEND cannot host the chunks either.
        const noIend = joinChunk([createChunk("IHDR", "")]);
        expect(() => addTextMetadata(noIend, { Title: "x" })).toThrow();
    });

    it("LDG-31: bytes ride to and from the binary string unchanged", () => {
        const png = minimalPng();
        const bytes = binaryStringToBytes(png);
        expect(bytes).toBeInstanceOf(Uint8Array);
        // High bytes survive the & 0xff mask (the signature's 0x89).
        expect(bytes[0]).toBe(137);
        expect(bytesToBinaryString(bytes)).toBe(png);
    });
});
