import { Component } from "@angular/core";
import { faTag } from "@fortawesome/free-solid-svg-icons";
import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";

import { EntityCard } from "../entity-card/entity-card.component";
import { CardSortOption, DetailsCardSection } from "./details-card-section.component";

/**
 * The card section (UIC-27, DET-17..DET-22): title, count line, sort
 * select with direction button, keyword input, and a paged grid of
 * projected cards. Every state is an input and every interaction an emit —
 * the app's store seeds, resolves, filters, sorts, and pages.
 */
const meta: Meta<DetailsCardSection> = {
    component: DetailsCardSection,
    title: "Details Card Section",
};
export default meta;

type Story = StoryObj<DetailsCardSection>;

const options: CardSortOption[] = [
    { key: "relevance", label: "Relevance" },
    { key: "name", label: "Name" },
];

/** The reset clicks the play() tests collect. */
let resets = 0;

/** The section's card links: every link but the count line's reset link
 * (always there since UIC-27/DD-374). */
function cardLinks(canvasElement: HTMLElement): HTMLAnchorElement[] {
    return [...canvasElement.querySelectorAll<HTMLAnchorElement>("a")].filter(
        (a) => !a.classList.contains("aurelius-card-section-reset"),
    );
}

/**
 * A host that owns the section's state the way the details store will:
 * the keyword filters the cards, the sort reorders them, and the reset
 * link restores them (DET-20, DET-21). The cards are the ui
 * `entity-card`s the app projects into the grid.
 */
@Component({
    selector: "aurelius-atlas-ui-card-section-story-host",
    imports: [DetailsCardSection, EntityCard],
    template: `
        <aurelius-atlas-ui-details-card-section
            [title]="title"
            [count]="cards.length"
            [sortOptions]="options"
            [(sort)]="sort"
            [(sortDescending)]="descending"
            [(query)]="query"
            [filtered]="query !== null"
            [filteredCount]="shown.length"
            [allLoaded]="shown.length >= cards.length"
            (resetRequested)="reset()"
            (sortDirectionToggled)="descending = !descending"
        >
            @for (card of shown; track card.guid) {
                <div class="column is-half-tablet is-one-third-desktop">
                    <aurelius-atlas-ui-entity-card
                        [guid]="card.guid"
                        [name]="card.name"
                        [typeName]="card.typeName"
                        [typeIcon]="card.typeIcon"
                        [typeIconClass]="card.typeIconClass"
                        [showQuality]="false"
                    />
                </div>
            }
        </aurelius-atlas-ui-details-card-section>
    `,
})
class StoryHost {
    readonly options = options;

    title = "Data Attributes";

    // The badge icons arrive as inputs (UIC-15): the app resolves its
    // type-to-icon map (DD-378); the story passes the entry by hand.
    readonly cards = [
        {
            guid: "a1",
            name: "gene_symbol",
            typeName: "m4i_data_attribute",
            typeIcon: faTag,
            typeIconClass: "business",
        },
        {
            guid: "a2",
            name: "variant_pos",
            typeName: "m4i_data_attribute",
            typeIcon: faTag,
            typeIconClass: "business",
        },
        {
            guid: "a3",
            name: "assembly",
            typeName: "m4i_data_attribute",
            typeIcon: faTag,
            typeIconClass: "business",
        },
    ];

    sort: string | null = "relevance";

    descending = false;

    query: string | null = null;

    /** The filtered, sorted set — the store's job, shown here by the host. */
    get shown() {
        const term = this.query?.toLowerCase() ?? "";
        const matched = this.cards.filter((card) => card.name.toLowerCase().includes(term));
        const sorted = this.sort === "name" ? [...matched].sort((a, b) => a.name.localeCompare(b.name)) : matched;
        return this.descending ? [...sorted].reverse() : sorted;
    }

    reset(): void {
        this.query = null;
        this.sort = "relevance";
        this.descending = false;
        resets++;
    }
}

/** The filled section: three cards, the count line, the sort controls. */
export const Primary: Story = {
    render: () => ({
        moduleMetadata: { imports: [StoryHost] },
        template: `<aurelius-atlas-ui-card-section-story-host></aurelius-atlas-ui-card-section-story-host>`,
    }),
    play: async ({ canvasElement }) => {
        resets = 0;
        const canvas = within(canvasElement);

        await expect(canvas.getByText("Data Attributes")).toBeVisible();
        await expect(canvas.getByText("3 result(s)")).toBeVisible();
        await expect(canvas.getByRole("link", { name: "gene_symbol" })).toBeVisible();

        // DET-21: the Name sort reorders the cards. The count line is a
        // reset link too (UIC-27/DD-374), so the cards are the links minus it.
        await userEvent.selectOptions(canvas.getByRole("combobox"), "name");
        expect(cardLinks(canvasElement).map((link) => link.textContent?.trim())).toEqual([
            "assembly",
            "gene_symbol",
            "variant_pos",
        ]);

        // DET-21: the direction button reverses.
        await userEvent.click(canvas.getByRole("button", { name: "Sort direction" }));
        expect(cardLinks(canvasElement).map((link) => link.textContent?.trim())).toEqual([
            "variant_pos",
            "gene_symbol",
            "assembly",
        ]);
    },
};

/** The filtered shape: a keyword narrows the cards and the count line
 * becomes the reset link; clicking it restores everything (DET-20). */
export const Filtered: Story = {
    render: () => ({
        moduleMetadata: { imports: [StoryHost] },
        template: `<aurelius-atlas-ui-card-section-story-host></aurelius-atlas-ui-card-section-story-host>`,
    }),
    play: async ({ canvasElement }) => {
        resets = 0;
        const canvas = within(canvasElement);

        const search = canvas.getByRole("searchbox");
        await userEvent.type(search, "gene");
        await userEvent.click(canvas.getByRole("button", { name: "Search" }));
        expect(cardLinks(canvasElement)).toHaveLength(1);
        await expect(canvas.getByRole("link", { name: "gene_symbol" })).toBeVisible();
        await expect(canvas.getByText("1 result(s)")).toBeVisible();

        await userEvent.click(canvas.getByRole("link", { name: /result\(s\)/ }));
        expect(cardLinks(canvasElement)).toHaveLength(3);
        expect(resets).toBe(1);
    },
};

/** The empty section: a zero-count box with its count line and no cards
 * (DET-17 renders at zero; DET-27's Child Entities case). */
export const Empty: Story = {
    args: {
        title: "Child Entities",
        count: 0,
        sortOptions: options,
        allLoaded: true,
    },
    play: async ({ canvas, canvasElement }) => {
        await expect(canvas.getByText("Child Entities")).toBeVisible();
        await expect(canvas.getByText("0 result(s)")).toBeVisible();
        // DET-17 renders at zero and the count line is always the reset link
        // (UIC-27/DD-374): the section's one link, with no cards behind it.
        expect(cardLinks(canvasElement)).toHaveLength(0);
        await expect(canvas.getByRole("link", { name: /result\(s\)/ })).toBeVisible();
    },
};

/** The loading shape: cards that answer later show the loading row
 * (DET-18's pre-resolve state — the loading card, the count already set). */
export const Loading: Story = {
    args: {
        title: "Data Attributes",
        count: 2,
        sortOptions: options,
        allLoaded: true,
    },
    render: (args: Record<string, unknown>) => ({
        moduleMetadata: { imports: [DetailsCardSection, EntityCard] },
        props: args,
        template: `<aurelius-atlas-ui-details-card-section
    [title]="title"
    [count]="count"
    [sortOptions]="sortOptions"
    [allLoaded]="allLoaded"
>
    <div class="column is-half-tablet is-one-third-desktop">
        <aurelius-atlas-ui-entity-card
            [loading]="true"
            loadingLabel="Loading"
            [name]="'gene_symbol'"
            [showQuality]="false"
        />
    </div>
    <div class="column is-half-tablet is-one-third-desktop">
        <aurelius-atlas-ui-entity-card
            [loading]="true"
            loadingLabel="Loading"
            [name]="'variant_pos'"
            [showQuality]="false"
        />
    </div>
</aurelius-atlas-ui-details-card-section>`,
    }),
    play: async ({ canvas }) => {
        await expect(canvas.getByText("Loading gene_symbol...")).toBeVisible();
        await expect(canvas.getByText("2 result(s)")).toBeVisible();
    },
};

/** More cards than one page: the sentinel button asks for the next page
 * (DET-22, the UIC-22 contract). */
export const NextPage: Story = {
    args: {
        title: "Data Attributes",
        count: 31,
        sortOptions: options,
        allLoaded: false,
        loadLabel: "Load next page...",
    },
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        const button = canvas.getByRole("button", { name: "Load next page..." });
        await expect(button).toBeVisible();
        await userEvent.click(button);
    },
};

/** The narrow section: the container query stacks it — the funnel rides
 * left of the sort row and the search box spans the line under it
 * (DD-618's place "before the sort control", kept in both layouts; the
 * first cut stacked the funnel on its own line above the controls).
 * The wrapper's width drives the container, so the snapshot holds at
 * any Chromatic viewport. */
export const Stacked: Story = {
    render: () => ({
        moduleMetadata: { imports: [StoryHost] },
        template: `<div style="width: 380px">
    <aurelius-atlas-ui-card-section-story-host></aurelius-atlas-ui-card-section-story-host>
</div>`,
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await expect(canvas.getByText("Data Attributes")).toBeVisible();

        // The funnel sits beside the sort row, not above it: their boxes
        // ride the same line (the funnel's centre is inside the select's).
        const funnel = canvas.getByRole("button", { name: "Filter" });
        const select = canvas.getByRole("combobox");
        const funnelCentre = (funnel.getBoundingClientRect().top + funnel.getBoundingClientRect().bottom) / 2;
        expect(funnelCentre).toBeGreaterThan(select.getBoundingClientRect().top);
        expect(funnelCentre).toBeLessThan(select.getBoundingClientRect().bottom);
        // And left of it.
        expect(funnel.getBoundingClientRect().right).toBeLessThan(select.getBoundingClientRect().left);
        // The search wraps to its own full-width line below both.
        const search = canvas.getByRole("searchbox");
        expect(search.getBoundingClientRect().top).toBeGreaterThan(select.getBoundingClientRect().bottom);
    },
};
