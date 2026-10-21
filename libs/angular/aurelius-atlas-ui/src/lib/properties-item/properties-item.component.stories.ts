import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent } from "storybook/test";

import { PropertiesItemLink } from "./properties-item.component";

import { PropertiesItem } from "./properties-item.component";

const meta: Meta<PropertiesItem> = {
    component: PropertiesItem,
    title: "Properties Item",
};
export default meta;

type Story = StoryObj<PropertiesItem>;

const template = `
<aurelius-atlas-ui-properties-item [value]="value" (itemClicked)="onLink($event)"></aurelius-atlas-ui-properties-item>
`;

/** The guids the play() tests collect from itemClicked. */
const clicked: string[] = [];

const host = (args: Record<string, unknown>) => ({
    props: { ...args, onLink: (guid: string) => clicked.push(guid) },
    template,
});

export const Text: Story = {
    args: {
        value: "sales domain",
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("Sales Domain")).toBeVisible();
    },
    render: host,
};

const links: PropertiesItemLink[] = [
    { guid: "g1", displayText: "Alice" },
    { guid: "g2", displayText: "Bob" },
];

export const Links: Story = {
    args: {
        value: links,
    },
    play: async ({ canvas }) => {
        clicked.length = 0;
        const anchors = canvas.getAllByRole("link");
        await expect(anchors).toHaveLength(2);

        anchors[1].focus();
        await userEvent.keyboard("{Enter}");
        await expect(clicked).toEqual(["g2"]);
    },
    render: host,
};

export const Empty: Story = {
    args: {
        value: [],
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("N/A")).toBeVisible();
    },
    render: host,
};
