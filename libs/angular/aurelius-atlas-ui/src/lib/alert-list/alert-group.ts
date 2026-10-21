/**
 * The severity of an alert: an application error, a warning, or an
 * informational note. The order of the union is the order of precedence —
 * `error` outranks `warning` outranks `info` (ALR-02).
 */
export type AlertSeverity = "error" | "warning" | "info";

/**
 * A group of alerts the feed shows as one row (ALR-03, ALR-10): the
 * consumer's store merges repeats of the same key into a group, the
 * {@link AlertList} only renders what it is given. The model lives in the
 * lib because it is presentation vocabulary — the row's shape — not app
 * state; the caller owns the array.
 */
export type AlertGroup = {
    /** Stable id, the dismiss key. */
    id: string;
    /** The severity, colouring the row (ALR-07). */
    severity: AlertSeverity;
    /** The message, rendered as body text. */
    message: string;
    /** How many alerts merged into this group; the chip shows it above 1. */
    count: number;
    /** When the group's most recent alert arrived, epoch millis — the row's time. */
    lastSeen: number;
};

/** The severities from lowest to highest rank (ALR-02). */
const RANK: readonly AlertSeverity[] = ["info", "warning", "error"];

/**
 * The highest of two severities — `error` > `warning` > `info` (ALR-02).
 * @param a one severity
 * @param b the other severity
 * @returns the higher-ranked of the two
 */
export function maxSeverity(a: AlertSeverity, b: AlertSeverity): AlertSeverity {
    return RANK.indexOf(a) >= RANK.indexOf(b) ? a : b;
}
