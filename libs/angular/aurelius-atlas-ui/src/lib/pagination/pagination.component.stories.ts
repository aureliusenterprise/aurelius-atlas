import type { Meta, StoryObj } from "@storybook/angular";
import { Pagination } from "./pagination.component";

/**
 * Bulma pagination: previous/next buttons around a row of page numbers,
 * the current page marked. It collapses long page runs to the first, last
 * and a window around the current page.
 */
const meta: Meta<Pagination> = {
    component: Pagination,
    title: "Pagination",
};

export default meta;

type Story = StoryObj<Pagination>;

/** Page 1 of 5: Previous disabled, next enabled, pages 1–5 listed. */
export const Primary: Story = {
    args: {
        pageIndex: 0,
        pageSize: 4,
        totalItems: 20,
    },
    render: (args) => ({
        props: args,
    }),
};

/** Mid-run: both arrows enabled, the current page marked. */
export const SecondPage: Story = {
    args: {
        pageIndex: 1,
        pageSize: 4,
        totalItems: 20,
    },
    render: (args) => ({
        props: args,
    }),
};

/** The last page: Next is disabled. */
export const LastPage: Story = {
    args: {
        pageIndex: 4,
        pageSize: 4,
        totalItems: 20,
    },
    render: (args) => ({
        props: args,
    }),
};

/** 100 items: the page run collapses around the current page. */
export const LongForm: Story = {
    args: {
        pageIndex: 12,
        pageSize: 4,
        totalItems: 100,
    },
    render: (args) => ({
        props: args,
    }),
};

/** No items: both arrows disabled, no page numbers. */
export const Empty: Story = {
    args: {
        pageIndex: 0,
        pageSize: 4,
        totalItems: 0,
    },
    render: (args) => ({
        props: args,
    }),
};
