import { faCogs, faTable } from "@fortawesome/free-solid-svg-icons";
import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";

import { TokenPicker, type TokenChip, type TokenRow } from "./token-picker.component";

/**
 * The chip-and-suggest box (UIC-44, DD-713): chosen tokens ride inside the
 * box as chips, the input sits beside them, and the panel of rows opens while
 * the box holds focus. The story hands the box its rows; the search that
 * answers a picker's typing is the caller's job and lives in the webapp.
 */
const meta: Meta<TokenPicker> = {
    component: TokenPicker,
    title: "Token Picker",
    args: {
        label: "Related processes",
        placeholder: "Add a relationship...",
        singlePlaceholder: "Select a relationship...",
        deleteLabel: "Delete",
        idBase: "story",
    },
};
export default meta;

type Story = StoryObj<TokenPicker>;

const CHIPS: TokenChip[] = [
    { key: "a", label: "load_events", leadLabel: "Generic Process" },
    { key: "b", label: "nightly_orders", leadLabel: "DataSet" },
];

const ROWS: TokenRow[] = [
    {
        key: "r1",
        name: "load_events",
        type: "Generic Process",
        icon: faCogs,
        iconClass: "technical-process",
        trail: [
            { guid: "d1", name: "Sales Domain", typeName: "m4i_data_domain", icon: faTable, iconClass: "business" },
            {
                guid: "s1",
                name: "Order Processing",
                typeName: "m4i_data_entity",
                icon: faCogs,
                iconClass: "technical-process",
            },
        ],
    },
    { key: "r2", name: "load_orders", type: "Process" },
    { key: "r3", name: "a_process_with_a_rather_long_display_name_for_the_panel", type: "Process" },
];

/** The required-field host: the picker between its label and its error line,
 * the pairing the editor renders (EDT-17, FORM-ERR-002). */
const invalidTemplate = `
<p class="label" id="story-label">Model</p>
<aurelius-atlas-ui-token-picker
    [selected]="selected"
    [rows]="rows"
    [single]="single"
    [invalid]="invalid"
    [label]="label"
    [singlePlaceholder]="singlePlaceholder"
    [labelId]="labelId"
    [errorId]="errorId"
    idBase="story"
></aurelius-atlas-ui-token-picker>
<p class="help is-danger" id="story-error">A model is required.</p>
`;

const invalidHost = (args: Record<string, unknown>) => ({ props: { ...args }, template: invalidTemplate });

/**
 * Two chips and a full row set. The play() focuses the box (the panel is
 * focus-gated, DD-335), moves the active row with the arrows (DD-336), types,
 * and deletes a chip — the box's own behaviour, no caller state.
 */
export const Primary: Story = {
    args: { selected: CHIPS, rows: ROWS },
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        const field = canvas.getByRole("combobox", { hidden: true });

        await userEvent.click(field);
        await expect(canvas.getByRole("listbox", { hidden: true })).toBeVisible();
        await expect(canvas.getAllByRole("option", { hidden: true })).toHaveLength(3);

        // The first row is the active one until the arrows move it (DD-336).
        await expect(canvas.getAllByRole("option", { hidden: true })[0]).toHaveAttribute("aria-selected", "true");
        await userEvent.type(field, "{arrowdown}");
        await expect(canvas.getAllByRole("option", { hidden: true })[1]).toHaveAttribute("aria-selected", "true");

        await userEvent.type(field, "load");
        await expect(field).toHaveValue("load");

        // Every chip carries a delete (UIC-24); the box keeps them until the
        // caller answers the removal (DD-713 — the dumb box never self-removes).
        await expect(canvasElement.querySelectorAll(".aurelius-token-chip")).toHaveLength(2);
        await expect(canvas.getAllByRole("button", { name: "Delete" })).toHaveLength(2);
    },
};

/** The badge and trail a rich row carries (EDT-33): the type badge with the
 * app's icon and colour class, and the trail under the name. */
export const RichRow: Story = {
    args: { selected: [], rows: [ROWS[0]] },
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await userEvent.click(canvas.getByRole("combobox", { hidden: true }));
        const row = canvas.getAllByRole("option", { hidden: true })[0];
        await expect(row.querySelector(".aurelius-token-row-type")).toHaveTextContent("Generic Process");
        // The trail is the Breadcrumbs component with its links off (DD-714):
        // two plain crumbs and the arrow separators Bulma draws.
        const trail = row.querySelector(".aurelius-token-row-trail");
        await expect(trail).toHaveTextContent("Sales Domain");
        await expect(trail).toHaveTextContent("Order Processing");
        await expect(trail?.querySelectorAll("a")).toHaveLength(0);
    },
};

/** A single box with nothing chosen: the input shows the select placeholder. */
export const Single: Story = {
    args: { selected: [], rows: ROWS, single: true },
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await expect(canvas.getByPlaceholderText("Select a relationship...")).toBeVisible();
    },
};

/** A single box that is full: the input is gone (the change is delete, then pick). */
export const SingleFull: Story = {
    args: { selected: [CHIPS[0]], rows: ROWS, single: true },
    play: async ({ canvasElement }) => {
        await expect(canvasElement.querySelectorAll(".aurelius-token-chip")).toHaveLength(1);
        await expect(canvasElement.querySelector(".aurelius-token-input")).toBeNull();
    },
};

/** The required field with nothing chosen (EDT-17): the box takes the danger
 * border and the input names the error line below it. */
export const Invalid: Story = {
    args: {
        selected: [],
        rows: ROWS,
        single: true,
        invalid: true,
        label: "Model",
        labelId: "story-label",
        errorId: "story-error",
    },
    render: invalidHost,
    play: async ({ canvasElement }) => {
        await expect(canvasElement.querySelector(".aurelius-token-box")?.classList.contains("is-danger")).toBe(true);
        await expect(canvasElement.querySelector('[role="combobox"]')?.getAttribute("aria-describedby")).toBe(
            "story-error",
        );
    },
};
