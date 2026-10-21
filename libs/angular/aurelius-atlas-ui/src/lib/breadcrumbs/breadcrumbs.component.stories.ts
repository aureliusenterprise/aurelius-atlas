import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";
import { faProjectDiagram, faTable } from "@fortawesome/free-solid-svg-icons";

import { Breadcrumb, Breadcrumbs } from "./breadcrumbs.component";

/**
 * A trail of links from a root entity down to the current one: each crumb
 * carries its type icon and colour, the active crumb is marked, long names
 * truncate, and clicking a crumb emits `itemClicked` with its guid.
 */
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

/**
 * A domain and a dataset, the second the active crumb. Its icon is coloured
 * by its type class; Enter on a crumb emits the click.
 */
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

/**
 * The trail has a gap and cannot be resolved: a warning chip precedes it.
 */
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

/** No items: the component renders nothing at all. */
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
 * The trail on the dark theme: the crumb links brighten and the technical
 * blue lifts for the dark surface. It opens dark — the toolbar Theme switch
 * (top bar) flips it to light or Auto at any time.
 */
export const OnDark: Story = {
    args: {
        items,
        activeGuid: "g2",
    },
    parameters: { theme: "dark" },
    play: async ({ canvasElement }) => {
        const iconColor = (selector: string) => {
            const el = canvasElement.querySelector<HTMLElement>(selector);
            if (!el) throw new Error(`${selector} is missing`);
            return getComputedStyle(el).color;
        };
        // The icon classes ride the fa-icon (the component's template),
        // coloured by the SCSS .business/.technical rules. The toolbar
        // Theme switch can move this story to either scheme, so assert the
        // blue of whichever one is active — the business orange is shared.
        const dark = document.documentElement.dataset["theme"] !== "light";
        await expect(iconColor(".icon .business")).toBe("rgb(255, 165, 0)");
        await expect(iconColor(".icon .technical")).toBe(dark ? "rgb(128, 128, 255)" : "rgb(0, 0, 255)");
    },
    render: host,
};
