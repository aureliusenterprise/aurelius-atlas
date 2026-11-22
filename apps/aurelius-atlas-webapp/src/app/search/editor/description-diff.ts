/**
 * The word diff of a prose change (HST-15, HST-16, DD-825).
 *
 * A change list answers which attribute changed and shows its old and new text
 * (7.37). For the two prose attributes the editor paints as markdown (EDT-20),
 * a one-sentence fix prints both whole texts and the reader has to find the fix
 * by eye. This helper answers the same change as the parts of one text: the
 * words that stayed are `kept`, the words the write took away are `removed`, the
 * words it put in are `added`, and a long run of kept words folds to one marker
 * so the lines that hold the change are what shows (HST-16).
 *
 * The helper is pure and locale-free: it takes two texts and returns parts. The
 * component owns the marks, the count's words and the rest of the screen.
 * Nothing here sends or reads anything (AUD-06).
 */

/** One part of a prose diff, in the order it prints. A folded part carries the
 * size of the run it replaced and no text (HST-16), so the component words it. */
export type ProsePart = { kind: "kept" | "removed" | "added"; text: string } | { kind: "folded"; words: number };

/** How many kept words print around a change before a run folds (HST-16).
 * Three gives the reader the words on both sides of the edit. */
const KEEP_WORDS = 3;

/** At most this many words go through the exact word diff. The table below is
 * that search, and a drawer read must not wait for a big one. Past the ceiling
 * the answer falls back to the whole text out and the whole text in: the row of
 * 7.37, never wrong, only less kind.
 * shortcut: a definition over about 1,000 words swaps as a whole; upgrade to a
 * linear diff (Myers) if a stored definition reaches that size in practice. */
const MAX_WORDS = 1000;

/** One word with the whitespace that follows it. Keeping the whitespace with
 * its word means the parts join back into the stored text with no guess. */
type Token = { text: string };

/**
 * The diff of one prose attribute (HST-15): the text the state before the write
 * held and the text the write stored, answered as the parts of one text. A text
 * the write filled for the first time is all added and one it cleared is all
 * removed, because then every word moved.
 * @param from the text before, empty when the attribute held none
 * @param to the text after, empty when the write cleared it
 * @returns the parts to print, in order; nothing when nothing changed
 */
export function diffProse(from: string, to: string): readonly ProsePart[] {
    if (from === to) {
        return [];
    }
    if (from.trim() === "") {
        return [{ kind: "added", text: to }];
    }
    if (to.trim() === "") {
        return [{ kind: "removed", text: from }];
    }

    const before = tokenize(from);
    const after = tokenize(to);
    if (before.length > MAX_WORDS || after.length > MAX_WORDS) {
        return [
            { kind: "removed", text: from },
            { kind: "added", text: to },
        ];
    }

    return foldRuns(diffTokens(before, after));
}

/** Split a text into word-plus-following-whitespace tokens, so the parts of a
 * diff concatenate back into the stored text. A leading whitespace run, if the
 * text carries one, becomes the first token. */
function tokenize(text: string): readonly Token[] {
    return (text.match(/\S+\s*|\s+/g) ?? []).map((piece) => ({ text: piece }));
}

/** The word of a token: its text without the whitespace it carries. */
function wordOf(token: Token): string {
    return token.text.trim();
}

/** Answer two token lists as kept, removed and added parts in reading order. A
 * changed stretch prints its removed words before its added words, the order
 * the change list's old and new marks already use (HST-10). */
function diffTokens(before: readonly Token[], after: readonly Token[]): ProsePart[] {
    const common = commonTable(before, after);
    const width = after.length + 1;
    const parts: ProsePart[] = [];
    let i = 0;
    let j = 0;

    /** Append a part, joined onto the previous one when they are the same kind. */
    const push = (part: ProsePart): void => {
        const last = parts.at(-1);
        if (last !== undefined && last.kind === part.kind && last.kind !== "folded" && part.kind !== "folded") {
            last.text += part.text;
            return;
        }
        parts.push(part);
    };

    while (i < before.length || j < after.length) {
        if (i < before.length && j < after.length && wordOf(before[i]) === wordOf(after[j])) {
            push({ kind: "kept", text: before[i].text });
            i += 1;
            j += 1;
            continue;
        }
        // One changed stretch: walk it to its end so its words print as one
        // removed part and one added part instead of one part per word.
        let removed = "";
        let added = "";
        while (
            (i < before.length || j < after.length) &&
            !(i < before.length && j < after.length && wordOf(before[i]) === wordOf(after[j]))
        ) {
            const dropBefore =
                j >= after.length || (i < before.length && common[(i + 1) * width + j] >= common[i * width + (j + 1)]);
            if (dropBefore) {
                removed += before[i].text;
                i += 1;
            } else {
                added += after[j].text;
                j += 1;
            }
        }
        if (removed !== "") {
            push({ kind: "removed", text: removed });
        }
        if (added !== "") {
            push({ kind: "added", text: added });
        }
    }

    return parts;
}

/** The longest-common-subsequence table of two token lists, by word. The cell
 * at row i and column j answers how many words `before` from i and `after` from
 * j still share, which is what tells the walk which side to drop. */
function commonTable(before: readonly Token[], after: readonly Token[]): Uint16Array {
    const width = after.length + 1;
    const table = new Uint16Array((before.length + 1) * width);
    for (let i = before.length - 1; i >= 0; i -= 1) {
        for (let j = after.length - 1; j >= 0; j -= 1) {
            table[i * width + j] =
                wordOf(before[i]) === wordOf(after[j])
                    ? table[(i + 1) * width + (j + 1)] + 1
                    : Math.max(table[(i + 1) * width + j], table[i * width + (j + 1)]);
        }
    }

    return table;
}

/** Fold the kept runs longer than what prints around a change (HST-16): the
 * words on each side stay and the middle states how many words it holds. A run
 * short enough to print whole stays whole, so a small edit prints in full. */
function foldRuns(parts: readonly ProsePart[]): readonly ProsePart[] {
    const out: ProsePart[] = [];
    for (const part of parts) {
        const words = part.kind === "kept" ? wordsIn(part.text) : 0;
        if (part.kind !== "kept" || words <= KEEP_WORDS * 2 + 1) {
            out.push(part);
            continue;
        }
        const pieces = part.text.split(/(\s+)/).filter((piece) => piece !== "");
        const edge = KEEP_WORDS * 2 - 1;
        out.push({ kind: "kept", text: pieces.slice(0, edge).join("") });
        out.push({ kind: "folded", words: words - KEEP_WORDS * 2 });
        out.push({ kind: "kept", text: pieces.slice(-edge).join("") });
    }

    return out;
}

/** How many words a text holds. */
function wordsIn(text: string): number {
    const trimmed = text.trim();

    return trimmed === "" ? 0 : trimmed.split(/\s+/).length;
}
