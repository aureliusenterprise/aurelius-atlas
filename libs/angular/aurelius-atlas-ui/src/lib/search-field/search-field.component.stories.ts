import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";
import { SearchField } from "./search-field.component";

/**
 * A search input with a clear button, optionally a submit button — the
 * query is two-way bound, and submitting emits it.
 */
const meta: Meta<SearchField> = {
    component: SearchField,
    title: "Search Field",
};
export default meta;

type Story = StoryObj<SearchField>;

/**
 * Empty field with a submit button: the play() types a query, then
 * clears it.
 */
export const Primary: Story = {
    args: {
        placeholder: "Search...",
        withSubmitButton: true,
    },
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        const field = canvas.getByPlaceholderText("Search...");

        await userEvent.type(field, "glossary");
        await expect(field).toHaveValue("glossary");

        await userEvent.click(canvas.getByRole("button", { name: "Clear" }));
        await expect(field).toHaveValue("");
    },
};

/** The field pre-filled with a query, the clear button ready. */
export const WithQuery: Story = {
    args: {
        placeholder: "Search...",
        query: "glossary",
        withSubmitButton: true,
    },
};

/** Enter submits; the play() checks no submit button is rendered. */
export const WithoutSubmitButton: Story = {
    args: {
        placeholder: "Search...",
        withSubmitButton: false,
    },
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await expect(canvas.queryByRole("button", { name: "Search" })).toBeNull();
    },
};
