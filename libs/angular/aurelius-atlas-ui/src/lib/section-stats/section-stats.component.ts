import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";

/**
 * One stat of the bar: its localized label, the section id the heading
 * links to, and the count, rendered as text by the caller (the legacy
 * templates interpolated their stream raw — a count, not a locale-aware
 * number).
 */
export interface SectionStat {
    /** The stat's label, the section's name. The caller localises it. */
    label: string;
    /** The section's id, the href's target: `#target`. */
    target: string;
    /** The count, as the caller renders it. */
    count: string | number;
}

/**
 * The Aurelius section count bar: the `nav.level` of heading-links with
 * counts the legacy details screens repeat — one stat above the
 * properties accordion (`default-details`), three above the
 * governance-quality sections (`gov-quality-details`) (UIC-19, DD-102).
 *
 * A heading click emits `itemClicked(target)` — the legacy
 * `DetailsNavigationItem` directive's anchor, turned into an emit
 * (DD-066's pattern). The anchor's `#target` href is the plain-jump
 * keyboard path; the app's directive smooth-scrolls when it wires them.
 */
@Component({
    selector: "aurelius-atlas-ui-section-stats",
    templateUrl: "./section-stats.component.html",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SectionStats {
    /**
     * The stats, left to right. Empty renders the empty `nav.level`, as
     * the legacy bars did with no counts.
     */
    readonly items = input<SectionStat[]>([]);

    /**
     * Emits the target of a clicked heading. The app scrolls; the lib
     * does not (DD-101's split).
     */
    readonly itemClicked = output<string>();

    /**
     * Handle a heading activation — the legacy directive's click, turned
     * into an emit: the anchor's href is the keyboard path, the click
     * handler emits and cancels the fragment jump (the breadcrumbs'
     * pattern, UIC-11). The app wires the smooth-scroll to the emit.
     * @param event The click event.
     * @param stat The stat activated.
     */
    protected onStatClick(event: Event, stat: SectionStat): void {
        this.itemClicked.emit(stat.target);
        event.preventDefault();
    }
}
