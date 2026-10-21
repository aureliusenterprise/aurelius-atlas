import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";
import { faProjectDiagram, faTable } from "@fortawesome/free-solid-svg-icons";

import { Breadcrumb, Breadcrumbs } from "./breadcrumbs.component";

const meta: Meta<Breadcrumbs> = {
    component: Breadcrumbs,
    title: "Breadcrumbs",
};
export default meta;

type Story = StoryObj<Breadcrumbs>;

const items: Breadcrumb[] = [
    { guid: "g1", name: "Sales Domain", typeName: "m4i_data_domain", icon: faProjectDiagram, iconClass: "business" },
    { guid: "g2", name: "Orders Dataset", typeName: "m4i_dataset", icon: faTable, iconClass: "technical" },
];

/** The template binding the inputs, with the itemClicked spy. */
const template = `
<aurelius-atlas-ui-breadcrumbs
    [items]="items"
    [activeGuid]="activeGuid"
    [warning]="warning"
    (itemClicked)="onCrumb($event)"
></aurelius-atlas-ui-breadcrumbs>
`;

/** The guids the play() tests collect from itemClicked. */
const clicked: string[] = [];

const host = (args: Record<string, unknown>) => ({
    props: { ...args, onCrumb: (guid: string) => clicked.push(guid) },
    template,
});

export const Primary: Story = {
    args: {
        items,
        activeGuid: "g2",
    },
    play: async ({ canvas }) => {
        clicked.length = 0;
        const nav = canvas.getByRole("navigation", { name: "breadcrumbs" });
        const crumbs = within(nav).getAllByRole("link");
        await expect(crumbs).toHaveLength(2);
        await expect(crumbs[1].closest("li")).toHaveClass("is-active");
        await expect(crumbs[1]).toHaveTextContent("Orders Dataset");

        // The anchors carry an href, so Enter activates them natively —
        // the keyboard path UIC-11 promises.
        crumbs[0].focus();
        await userEvent.keyboard("{Enter}");
        await expect(clicked).toEqual(["g1"]);
    },
    render: host,
};

export const Warning: Story = {
    args: {
        items,
        warning: "Breadcrumb path could not be determined",
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("Breadcrumb path could not be determined")).toBeVisible();
    },
    render: host,
};

export const Empty: Story = {
    args: {
        items: [],
    },
    play: async ({ canvas }) => {
        await expect(canvas.queryByRole("navigation")).toBeNull();
    },
    render: host,
};

/**
 * The dark scheme (DD-068): the trail on the dark surface. The legacy
 * pure-blue technical ink lifts to Bulma's dark-adapted lightness; the
 * business orange is dark-safe and stays.
 */
export const OnDark: Story = {
    args: {
        items,
        activeGuid: "g2",
    },
    globals: { theme: "dark" },
    play: async ({ canvasElement }) => {
        const iconColor = (selector: string) => {
            const el = canvasElement.querySelector<HTMLElement>(selector);
            if (!el) throw new Error(`${selector} is missing`);
            return getComputedStyle(el).color;
        };
        // The icon classes ride the fa-icon (the component's template),
        // coloured by the SCSS .business/.technical rules.
        await expect(iconColor(".icon .business")).toBe("rgb(255, 165, 0)");
        await expect(iconColor(".icon .technical")).toBe("rgb(128, 128, 255)");
    },
    render: host,
};
