import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent } from "storybook/test";

import { Select } from "./select.component";

/**
 * A labelled dropdown over a list of rows, with a search button beside
 * it: selecting writes to the value, the button emits `searchRequested`.
 * Placeholder, no-data and required-help texts are all caller inputs.
 */
const meta: Meta<Select> = {
    component: Select,
    title: "Select",
    // The shared template binds searchVisible; on by default, as the
    // component's input and the legacy modal opener are (DD-164).
    args: {
        searchVisible: true,
    },
};
export default meta;

type Story = StoryObj<Select>;

type Row = { name: string; kind: string };

const rows: Row[] = [
    { name: "Glossary", kind: "term" },
    { name: "Domain", kind: "domain" },
    { name: "Lineage", kind: "process" },
];

const template = `
<aurelius-atlas-ui-select
    [options]="options"
    [displayField]="displayField"
    [label]="label"
    [invalid]="invalid"
    [disabled]="disabled"
    [searchLoading]="searchLoading"
    [searchVisible]="searchVisible"
    (searchRequested)="onSearch()"
></aurelius-atlas-ui-select>
`;

/** The searchRequested hits the play() tests collect. */
let searches = 0;

const host = (args: Record<string, unknown>) => ({
    props: { ...args, onSearch: () => searches++ },
    template,
});

/**
 * Three options: the play() picks one and presses Search, checking the
 * value lands and the event fires.
 */
export const Primary: Story = {
    args: {
        options: rows,
        displayField: "name",
        label: "Entity type",
    },
    play: async ({ canvas }) => {
        searches = 0;
        const control = canvas.getByLabelText("Entity type");
        await expect(control).toBeVisible();
        await expect(canvas.getByText("Glossary")).toBeVisible();

        await userEvent.selectOptions(control, "Domain");
        await expect(control).toHaveDisplayValue("Domain");

        await userEvent.click(canvas.getByRole("button", { name: "Search" }));
        await expect(searches).toBe(1);
    },
    render: host,
};

/** No options: the select shows the no-data message. */
export const NoData: Story = {
    args: {
        options: [],
        displayField: "name",
        label: "Entity type",
    },
    play: async ({ canvas }) => {
        // The placeholder option is hidden by the native select; the option
        // text is the assertion (toBeVisible cannot apply to a hidden option).
        await expect(canvas.getByRole("combobox")).toHaveTextContent(/No data available/);
    },
    render: host,
};

/** Marked invalid: the control is red and the required-help shows. */
export const Invalid: Story = {
    args: {
        options: rows,
        displayField: "name",
        label: "Entity type",
        invalid: true,
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("Please select a value")).toBeVisible();
    },
    render: host,
};

/** Both the control and the search button disabled. */
export const Disabled: Story = {
    args: {
        options: rows,
        displayField: "name",
        label: "Entity type",
        disabled: true,
    },
    play: async ({ canvas }) => {
        searches = 0;
        await expect(canvas.getByLabelText("Entity type")).toBeDisabled();

        const search = canvas.getByRole("button", { name: "Search" });
        await expect(search).toBeDisabled();
        await userEvent.click(search).catch(() => undefined);
        await expect(searches).toBe(0);
    },
    render: host,
};

/** A search in flight: the button spins and ignores clicks. */
export const SearchLoading: Story = {
    args: {
        options: rows,
        displayField: "name",
        label: "Entity type",
        searchLoading: true,
    },
    play: async ({ canvas }) => {
        searches = 0;
        const search = canvas.getByRole("button", { name: "Search" });
        await expect(search).toHaveAttribute("aria-busy", "true");
        await userEvent.click(search).catch(() => undefined);
        await expect(searches).toBe(0);
    },
    render: host,
};

/**
 * The plain dropdown (`searchVisible` off, DD-164): the settings panel's
 * theme picker form — a labelled select with no search button beside it.
 */
export const NoSearch: Story = {
    args: {
        options: rows,
        displayField: "name",
        label: "Entity type",
        searchVisible: false,
    },
    play: async ({ canvas }) => {
        const control = canvas.getByLabelText("Entity type");
        await expect(control).toBeVisible();
        await expect(canvas.queryByRole("button", { name: "Search" })).toBeNull();

        await userEvent.selectOptions(control, "Domain");
        await expect(control).toHaveDisplayValue("Domain");
    },
    render: host,
};
