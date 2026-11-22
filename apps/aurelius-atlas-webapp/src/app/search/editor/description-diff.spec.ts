import { describe, expect, it } from "vitest";

import { diffProse, type ProsePart } from "./description-diff";

/** The kinds of the parts, for a compact assertion (HST-15). */
function kinds(parts: readonly ProsePart[]): readonly string[] {
    return parts.map((part) => part.kind);
}

/** The text of the parts that carry one, joined (HST-15). */
function textOf(parts: readonly ProsePart[]): string {
    return parts
        .filter((part) => part.kind !== "folded")
        .map((part) => part.text)
        .join("");
}

/** The kept text, which must rebuild the stored text after the write. */
function textWithout(parts: readonly ProsePart[], ...drop: readonly string[]): string {
    return parts
        .filter((part) => !drop.includes(part.kind))
        .map((part) => (part.kind === "folded" ? "" : part.text))
        .join("");
}

describe("descriptionDiff word diff (HST-15)", () => {
    it("answers no parts when neither text differs (HST-15)", () => {
        expect(diffProse("The same text.", "The same text.")).toEqual([]);
    });

    it("marks the words the write added and leaves the rest kept (HST-15)", () => {
        const parts = diffProse("The dataset is owned by the team.", "The dataset is now owned by the team.");

        expect(kinds(parts)).toEqual(["kept", "added", "kept"]);
        expect(textWithout(parts, "added")).toBe("The dataset is owned by the team.");
        expect(textWithout(parts, "removed")).toBe("The dataset is now owned by the team.");
    });

    it("marks the words the write took away, before the words it put in (HST-15)", () => {
        const parts = diffProse("The report runs nightly.", "The report runs hourly.");

        expect(kinds(parts)).toEqual(["kept", "removed", "added"]);
        expect(textWithout(parts, "added")).toBe("The report runs nightly.");
        expect(textWithout(parts, "removed")).toBe("The report runs hourly.");
    });

    it("marks a filled attribute as all added and a cleared one as all removed (HST-15)", () => {
        expect(diffProse("", "A first definition.")).toEqual([{ kind: "added", text: "A first definition." }]);
        expect(diffProse("A cleared definition.", "")).toEqual([{ kind: "removed", text: "A cleared definition." }]);
        // A whitespace-only text holds no word, so it reads as nothing too.
        expect(diffProse("   ", "Now it holds a word.")).toEqual([{ kind: "added", text: "Now it holds a word." }]);
    });

    it("keeps one part per changed run, not one per word (HST-15)", () => {
        const parts = diffProse("a b c d e f", "a b X Y Z f");

        expect(kinds(parts)).toEqual(["kept", "removed", "added", "kept"]);
        expect(textWithout(parts, "added")).toBe("a b c d e f");
        expect(textWithout(parts, "removed")).toBe("a b X Y Z f");
    });

    it("folds a long run of kept words and keeps the words around it (HST-15, HST-16)", () => {
        const before = [...Array.from({ length: 40 }, (_, index) => `w${index}`), "old"].join(" ");
        const after = [...Array.from({ length: 40 }, (_, index) => `w${index}`), "new"].join(" ");
        const parts = diffProse(before, after);

        // The fold lands between the two changes' context: kept words, a folded
        // run, kept words, then the changed word itself (HST-16).
        expect(kinds(parts)).toEqual(["kept", "folded", "kept", "removed", "added"]);
        const folded = parts.find((part) => part.kind === "folded");
        expect(folded?.kind === "folded" ? folded.words : 0).toBeGreaterThan(30);
        // The kept head and tail are words of the stored text, not markers.
        expect(textWithout(parts, "added", "removed").trim().split(/\s+/).length).toBeLessThan(10);
        expect(textOf(parts).includes("w0")).toBe(true);
    });

    it("prints a short text in full, with no fold (HST-16)", () => {
        const parts = diffProse("one two three four five six", "one two three four five SEVEN");

        expect(kinds(parts)).not.toContain("folded");
    });

    it("answers a very long change as the whole text out and in (HST-16)", () => {
        // Past the helper's ceiling an exact word search costs more than a
        // drawer read may wait for, so the answer falls back to 7.37's row.
        const long = Array.from({ length: 1200 }, (_, index) => `w${index}`).join(" ");
        const parts = diffProse(long, `${long} one more word`);

        expect(kinds(parts)).toEqual(["removed", "added"]);
    });

    it("rebuilds both stored texts from its parts (HST-15)", () => {
        const before = "Orders land in the lake hourly. The team reviews them weekly.";
        const after = "Orders land in the lake hourly. The platform team reviews them daily.";
        const parts = diffProse(before, after);

        expect(textWithout(parts, "added", "folded")).toBe(before);
        expect(textWithout(parts, "removed", "folded")).toBe(after);
    });
});
