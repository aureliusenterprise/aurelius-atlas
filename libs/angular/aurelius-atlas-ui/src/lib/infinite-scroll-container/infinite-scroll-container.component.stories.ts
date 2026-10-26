import type { Meta, StoryObj } from "@storybook/angular";
import { expect, fireEvent, userEvent, within } from "storybook/test";

import { InfiniteScrollContainer } from "./infinite-scroll-container.component";

/**
 * The infinite-scroll container: the projected list, and a sentinel row —
 * a full-width "Load next page..." button — that emits `nextPage` on click
 * and when scrolled into view. The caller owns the paging (the inputs are
 * the states of its store); `allLoaded` removes the row (UIC-21..23).
 */
const meta: Meta<InfiniteScrollContainer> = {
    component: InfiniteScrollContainer,
    title: "Infinite Scroll Container",
};
export default meta;

type Story = StoryObj<InfiniteScrollContainer>;

/** The nextPage emissions the play() tests collect. */
const emissions: number[] = [];

const host = (args: Record<string, unknown>) => ({
    props: {
        ...args,
        onNextPage: () => emissions.push(Date.now()),
    },
    template: `
<aurelius-atlas-ui-infinite-scroll-container
    [loading]="loading"
    [allLoaded]="allLoaded"
    [loadLabel]="loadLabel"
    (nextPage)="onNextPage()"
    class="story-scroll-host"
>
    <div class="box">Result 1</div>
    <div class="box">Result 2</div>
    <div class="box">Result 3</div>
</aurelius-atlas-ui-infinite-scroll-container>
`,
});

/** A list with pages left: the sentinel row shows its button. */
export const Primary: Story = {
    args: {
        loading: false,
        allLoaded: false,
        loadLabel: "Load next page...",
    },
    render: host,
    play: async ({ canvasElement }) => {
        emissions.length = 0;
        const canvas = within(canvasElement);

        // UIC-21: a click asks for the next page.
        await userEvent.click(canvas.getByRole("button", { name: "Load next page..." }));
        expect(emissions).toHaveLength(1);
    },
};

/** A page in flight: the button carries the spinner and clicks are no-ops. */
export const Loading: Story = {
    args: {
        loading: true,
        allLoaded: false,
        loadLabel: "Load next page...",
    },
    render: host,
    play: async ({ canvasElement }) => {
        emissions.length = 0;
        const canvas = within(canvasElement);

        // UIC-22: a click while loading is suppressed. Bulma's is-loading
        // sets `pointer-events: none` on the button — that is what makes it
        // inert for real users — so userEvent (a real pointer) can't reach
        // it; fireEvent dispatches the DOM event the way keyboard activation
        // does, which is the requestPage() guard under test here.
        fireEvent.click(canvas.getByRole("button", { name: "Load next page..." }));
        expect(emissions).toHaveLength(0);
    },
};

/** Every page loaded: the row is gone (UIC-21). */
export const AllLoaded: Story = {
    args: {
        loading: false,
        allLoaded: true,
        loadLabel: "Load next page...",
    },
    render: host,
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        expect(canvas.queryByRole("button", { name: "Load next page..." })).toBeNull();
    },
};
