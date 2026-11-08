import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent } from "storybook/test";

import { PeopleBox, PeopleRow } from "./people-box.component";

/**
 * The People box (UIC-28, DET-23): labelled rows of person links. A click
 * emits `personClicked(guid)` — the app routes to that entity.
 */
const meta: Meta<PeopleBox> = {
    component: PeopleBox,
    title: "People Box",
};
export default meta;

type Story = StoryObj<PeopleBox>;

const fullRows: PeopleRow[] = [
    { label: "Domain Lead(s)", people: [{ guid: "d1", displayText: "Ada Lovelace" }] },
    {
        label: "Data Owner(s)",
        people: [
            { guid: "o1", displayText: "Grace Hopper" },
            { guid: "o2", displayText: "Alan Turing" },
        ],
    },
    { label: "Data Steward(s)", people: [{ guid: "s1", displayText: "Barbara Liskov" }] },
];

/** The guids the play() tests collect from personClicked. */
const clicked: string[] = [];

const host = (args: Record<string, unknown>) => ({
    props: { ...args, onPerson: (guid: string) => clicked.push(guid) },
    template: `
<aurelius-atlas-ui-people-box
    [rows]="rows"
    [emptyLabel]="emptyLabel"
    [showEmpty]="showEmpty"
    (personClicked)="onPerson($event)"
></aurelius-atlas-ui-people-box>
`,
});

/** The filled box: all three rows, several owners comma-joined. */
export const Primary: Story = {
    args: {
        rows: fullRows,
        emptyLabel: "No people assigned.",
        showEmpty: true,
    },
    play: async ({ canvas }) => {
        clicked.length = 0;
        await expect(canvas.getByText("Domain Lead(s)")).toBeVisible();
        await expect(canvas.getByText("Grace Hopper")).toBeVisible();
        await expect(canvas.getByText("Alan Turing")).toBeVisible();

        await userEvent.click(canvas.getByRole("link", { name: "Barbara Liskov" }));
        await expect(clicked).toEqual(["s1"]);
    },
    render: host,
};

/** The empty box: every row empty shows the italic centered line. */
export const Empty: Story = {
    args: {
        rows: [
            { label: "Domain Lead(s)", people: [] },
            { label: "Data Owner(s)", people: [] },
            { label: "Data Steward(s)", people: [] },
        ],
        emptyLabel: "No people assigned.",
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("No people assigned.")).toBeVisible();
        await expect(canvas.queryAllByRole("link")).toHaveLength(0);
    },
    render: host,
};

/** The card body: no rows and `showEmpty` off renders nothing at all. */
export const CardBodySilent: Story = {
    args: {
        rows: [],
        showEmpty: false,
        emptyLabel: "No people assigned.",
    },
    play: async ({ canvas }) => {
        await expect(canvas.queryByText("No people assigned.")).toBeNull();
    },
    render: host,
};
