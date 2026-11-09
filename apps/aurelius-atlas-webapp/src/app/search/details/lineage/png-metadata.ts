/**
 * The PNG `tEXt` metadata writer (LDG-31, DD-398): the legacy
 * `modelview2/utils/png-metadata.ts` ported as pure functions over binary
 * strings (each char codes one byte — the legacy's shape, kept so the
 * chunk walk stays a string walk). The save flow splits a finished PNG at
 * its chunk boundaries, appends one `tEXt` chunk per metadata field before
 * `IEND`, and rejoins (the legacy's `addMetadata`).
 *
 * The bytes never leave this module as strings: {@link binaryStringToBytes}
 * and {@link bytesToBinaryString} carry them to and from the Blob the
 * download wraps ({@link ./save-view-as-image}).
 */

/** One decoded PNG chunk: length, type, payload, and stored CRC. */
export interface PngChunk {
    readonly size: number;
    readonly type: string;
    readonly data: string;
    readonly crc: number;
}

/** The eight-byte PNG signature, as a binary string. */
const PNG_SIG = String.fromCodePoint(137, 80, 78, 71, 13, 10, 26, 10);

/** Raised when the bytes handed to {@link splitChunk} are not a PNG. */
export class PngSignatureError extends Error {
    constructor() {
        super("The given bytes are not a PNG");
    }
}

/**
 * The CRC32 table, generated at load — the legacy's vendored 256-entry
 * `HEX_TABLE` computed (the same polynomial, `0xedb88320` reflected).
 */
const CRC_TABLE: number[] = [];
for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
        c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    CRC_TABLE.push(c >>> 0);
}

/**
 * CRC32 over a binary string (the legacy's table-driven util, verbatim
 * arithmetic): `crc32("123456789")` is the standard check vector
 * `0xCBF43926`.
 * @param s the bytes as a binary string
 * @returns the unsigned CRC32
 */
export function crc32(s: string): number {
    let crc = 0 ^ -1;
    for (let i = 0; i < s.length; i++) {
        // The string is binary (every code point one byte, ≤ 0xff), so
        // codePointAt reads exactly what charCodeAt would.
        crc = (crc >>> 8) ^ CRC_TABLE[(crc ^ (s.codePointAt(i) ?? 0)) & 0xff];
    }
    return (crc ^ -1) >>> 0;
}

/** A number as a big-endian binary string of `size` bytes (legacy `itos`). */
function itos(value: number, size: number): string {
    const bytes: number[] = [];
    let rest = value;
    for (let i = size - 1; i >= 0; i--) {
        bytes[i] = rest & 0xff;
        rest = rest >> 8;
    }
    return bytes.map((byte) => String.fromCodePoint(byte)).join("");
}

/** A big-endian binary string as an unsigned number (legacy `stoi`). */
function stoi(s: string): number {
    let value = 0;
    for (let i = 0; i < s.length; i++) {
        // `<<` keeps the result signed; the legacy's `unpack('N')` is
        // unsigned, so the top bit must not become a minus sign.
        value = ((value << 8) | ((s.codePointAt(i) ?? 0) & 0xff)) >>> 0;
    }
    return value;
}

/** Whether the bytes start with the PNG signature. */
export function isPng(s: string): boolean {
    return s.startsWith(PNG_SIG);
}

/**
 * A chunk record: the CRC covers the type and data together, as the PNG
 * spec requires (the legacy's `createChunk`).
 */
export function createChunk(type: string, data: string): PngChunk {
    return { type, data, size: data.length, crc: crc32(type + data) };
}

/**
 * Split a PNG into its chunks (the legacy's `splitChunk`): the signature
 * checked, then length/type/data/CRC read chunk by chunk. A corrupt length
 * reads as an empty chunk and the walk continues — the legacy's posture,
 * the caller decides what to keep.
 * @throws {PngSignatureError} when the bytes carry no PNG signature
 */
export function splitChunk(s: string): PngChunk[] {
    if (!isPng(s)) {
        throw new PngSignatureError();
    }
    let rest = s.slice(PNG_SIG.length);
    const chunks: PngChunk[] = [];
    while (rest !== "") {
        let size = stoi(rest.slice(0, 4));
        if (size < 0) {
            size = 0;
        }
        const buf = rest.slice(0, size + 12);
        rest = rest.slice(size + 12);
        chunks.push({
            size,
            type: buf.slice(4, 8),
            data: buf.slice(8, 8 + size),
            crc: stoi(buf.slice(8 + size, 12 + size)),
        });
    }
    return chunks;
}

/** Rejoin chunks under the PNG signature (the legacy's `joinChunk`). */
export function joinChunk(chunks: readonly PngChunk[]): string {
    let out = PNG_SIG;
    for (const chunk of chunks) {
        out += itos(chunk.size, 4) + chunk.type + chunk.data + itos(chunk.crc, 4);
    }
    return out;
}

/**
 * Append one `tEXt` chunk per metadata field before `IEND` (the legacy's
 * `addMetadata`): keyword NUL value, and the empty-field skip the legacy
 * wrote as `if (!value) continue` — a field with no value ships no chunk
 * (LDG-31).
 * @param png the finished PNG as a binary string
 * @param metadata the keyword → value pairs, in chunk order
 * @returns the PNG with its metadata, as a binary string
 * @throws {PngSignatureError} when `png` carries no signature
 */
export function addTextMetadata(png: string, metadata: Readonly<Record<string, string>>): string {
    const chunks = splitChunk(png);
    const iend = chunks.pop();
    if (iend?.type !== "IEND") {
        throw new PngSignatureError();
    }
    for (const [keyword, value] of Object.entries(metadata)) {
        if (!value) {
            continue;
        }
        chunks.push(createChunk("tEXt", `${keyword}\u0000${value}`));
    }
    chunks.push(iend);
    return joinChunk(chunks);
}

/** A byte array as a binary string (the save flow hands canvas bytes over). */
export function bytesToBinaryString(bytes: Uint8Array): string {
    // Chunked apply: a string built char-by-char over megabytes would be
    // quadratic; fromCodePoint per slice keeps it linear.
    const parts: string[] = [];
    const slice = 8192;
    for (let i = 0; i < bytes.length; i += slice) {
        parts.push(String.fromCodePoint(...bytes.subarray(i, i + slice)));
    }
    return parts.join("");
}

/** A binary string as a byte array (the download's Blob payload). */
export function binaryStringToBytes(s: string): Uint8Array<ArrayBuffer> {
    const bytes = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) {
        bytes[i] = (s.codePointAt(i) ?? 0) & 0xff;
    }
    return bytes;
}
