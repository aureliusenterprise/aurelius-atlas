import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { RouterLink } from "@angular/router";
import { SectionStats, type SectionStat } from "aurelius-atlas-ui";

/** One grouped stats-bar box: a heading over its one or two level-item links
 * (DET-40) — the layout's group with the screen's live counts filled in. */
export interface DetailsStatGroup {
    /** The box's heading (the legacy box heading's key's text). */
    readonly heading: string;
    /** The box's stats, in legacy order. */
    readonly items: readonly SectionStat[];
}

/**
 * The stats bar under the layout's first row. A layout that groups its bar
 * (DET-40, DD-518 — the person page's four headed boxes) renders those boxes;
 * every other layout renders the flat bar (DET-24): the layout's `section-stats`
 * in legacy order, or the default layout's single Properties level while no
 * layout is in hand (7.20).
 *
 * A painter, not a store: the screen picks the layout's groups or stats and
 * fills the live counts, and hands both in together with the default Properties
 * title and count (DET-24's fallback). The two bars are mutually exclusive, like
 * the screen left them — a non-empty group list paints the grouped bar, nothing
 * else. Every heading link re-emits its anchor as `statClicked` for the screen
 * to route (DET-25's router anchor, DV-156: scroll only, no section filter). It
 * injects no store, router, or client.
 */
@Component({
    imports: [RouterLink, SectionStats],
    selector: "aurelius-atlas-webapp-details-stats-bar",
    styleUrl: "./stats-bar.component.scss",
    template: `
        @if (statsGroups().length > 0) {
            <div class="columns is-centered has-text-centered aurelius-details-stats-groups">
                @for (group of statsGroups(); track group.heading) {
                    <div class="column">
                        <div class="box aurelius-details-stats-group">
                            <p class="heading">{{ group.heading }}</p>
                            <nav class="level is-mobile" [attr.aria-label]="group.heading">
                                @for (item of group.items; track item.label) {
                                    <div class="level-item has-text-centered">
                                        <div>
                                            <p class="heading">
                                                <a [routerLink]="[]" [fragment]="item.target">{{ item.label }}</a>
                                            </p>
                                            <p class="title">{{ item.count }}</p>
                                        </div>
                                    </div>
                                }
                            </nav>
                        </div>
                    </div>
                }
            </div>
        }

        @if (statsGroups().length === 0) {
            <div class="box aurelius-details-stats">
                @if (hasLayout()) {
                    <aurelius-atlas-ui-section-stats [items]="stats()" (itemClicked)="statClicked.emit($event)" />
                } @else {
                    <nav class="level" [attr.aria-label]="propertiesTitle()">
                        <div class="level-item has-text-centered">
                            <div>
                                <p class="heading">
                                    <a
                                        [routerLink]="[]"
                                        fragment="properties-details"
                                        i18n="@@search.details.default.properties"
                                        >Properties</a
                                    >
                                </p>
                                <p class="title aurelius-details-property-count">{{ propertyCount() }}</p>
                            </div>
                        </div>
                    </nav>
                }
            </div>
        }
    `,
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DetailsStatsBar {
    /** The layout's grouped bar boxes, empty when the layout keeps the flat one (DET-40). */
    readonly statsGroups = input.required<readonly DetailsStatGroup[]>();

    /** The flat bar's stats, in legacy order, empty until a layout is in hand (DET-24). */
    readonly stats = input.required<SectionStat[]>();

    /** Whether a layout is in hand — false only while loading (DET-24's fallback). */
    readonly hasLayout = input.required<boolean>();

    /** The default layout's Properties title (DET-24's fallback heading). */
    readonly propertiesTitle = input.required<string>();

    /** The rendered properties' count (DET-24's fallback number). */
    readonly propertyCount = input.required<number>();

    /** The clicked heading's anchor (DET-25) — the screen routes it as the fragment. */
    readonly statClicked = output<string>();
}
