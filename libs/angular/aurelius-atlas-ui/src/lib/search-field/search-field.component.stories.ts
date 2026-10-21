import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";
import { SearchField } from "./search-field.component";

const meta: Meta<SearchField> = {
    component: SearchField,
    title: "Search Field",
};
export default meta;

type Story = StoryObj<SearchField>;

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

export const WithQuery: Story = {
    args: {
        placeholder: "Search...",
        query: "glossary",
        withSubmitButton: true,
    },
};

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
