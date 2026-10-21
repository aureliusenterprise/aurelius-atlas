import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent } from "storybook/test";

import { PropertiesItemLink } from "./properties-item.component";

import { PropertiesItem } from "./properties-item.component";

/**
 * One entity property value: text is title-cased, a list of linked values
 * renders as clickable anchors (emitting each guid), and an empty list
 * shows "N/A".
 */
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

/** A plain text value: "sales domain" renders title-cased. */
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

/**
 * Two linked people: anchors that emit the clicked guid (Enter works).
 */
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

/** An empty value list renders the "N/A" placeholder. */
export const Empty: Story = {
    args: {
        value: [],
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("N/A")).toBeVisible();
    },
    render: host,
};
