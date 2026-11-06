import { Component } from "@angular/core";
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
                <div class="column">
                    <aurelius-atlas-ui-entity-card
                        [guid]="card.guid"
                        [name]="card.name"
                        [typeName]="card.typeName"
                        [showQuality]="false"
                        [showIcon]="false"
                    />
                </div>
            }
        </aurelius-atlas-ui-details-card-section>
    `,
})
class StoryHost {
    readonly options = options;

    title = "Data Attributes";

    readonly cards = [
        { guid: "a1", name: "gene_symbol", typeName: "m4i_data_attribute" },
        { guid: "a2", name: "variant_pos", typeName: "m4i_data_attribute" },
        { guid: "a3", name: "assembly", typeName: "m4i_data_attribute" },
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

        // DET-21: the Name sort reorders the cards.
        await userEvent.selectOptions(canvas.getByRole("combobox"), "name");
        const links = await canvas.findAllByRole("link");
        expect(links.map((link) => link.textContent?.trim())).toEqual(["assembly", "gene_symbol", "variant_pos"]);

        // DET-21: the direction button reverses.
        await userEvent.click(canvas.getByRole("button", { name: "Sort direction" }));
        const reversed = await canvas.findAllByRole("link");
        expect(reversed.map((link) => link.textContent?.trim())).toEqual(["variant_pos", "gene_symbol", "assembly"]);
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
        await expect(canvas.getAllByRole("link")).toHaveLength(1);
        await expect(canvas.getByRole("link", { name: "gene_symbol" })).toBeVisible();
        await expect(canvas.getByText("1 result(s)")).toBeVisible();

        await userEvent.click(canvas.getByRole("link", { name: /result\(s\)/ }));
        await expect(canvas.getAllByRole("link")).toHaveLength(3);
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
    play: async ({ canvas }) => {
        await expect(canvas.getByText("Child Entities")).toBeVisible();
        await expect(canvas.getByText("0 result(s)")).toBeVisible();
        await expect(canvas.queryAllByRole("link", { name: /result\(s\)/ })).toHaveLength(0);
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
    <div class="column">
        <aurelius-atlas-ui-entity-card
            [loading]="true"
            loadingLabel="Loading"
            [name]="'gene_symbol'"
            [showQuality]="false"
        />
    </div>
    <div class="column">
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
