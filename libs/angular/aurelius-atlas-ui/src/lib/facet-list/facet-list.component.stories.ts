import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";

import { FacetItem, FacetList } from "./facet-list.component";

/**
 * The search sidebar's facet menu: a Bulma menu of value rows with counts,
 * a checkbox per row when `selectable`, and a five-row cap with the legacy
 * "Show more" link. The caller (the results screen) owns the selection and
 * the facet data (SDX); the component only renders and emits.
 */
const meta: Meta<FacetList> = {
    component: FacetList,
    title: "Facet List",
};
export default meta;

type Story = StoryObj<FacetList>;

/** The quick-search type facet's values, the m4i sample's shape. */
const typeItems: FacetItem[] = [
    { value: "m4i_data_attribute", label: "Data Attribute", count: 75 },
    { value: "m4i_gov_data_quality", label: "Gov. Quality", count: 32 },
    { value: "m4i_data_domain", label: "Data Domain", count: 9 },
    { value: "m4i_field", label: "Data Field", count: 8 },
    { value: "m4i_dataset", label: "Dataset", count: 5 },
    { value: "m4i_person", label: "Person", count: 2 },
];

/** The emissions the play() tests collect. */
const emissions: { value: string; checked: boolean }[] = [];

const host = (args: Record<string, unknown>) => ({
    props: {
        ...args,
        onToggled: (event: { value: string; checked: boolean }) => emissions.push(event),
    },
    template: `
<aurelius-atlas-ui-facet-list
    [title]="title"
    [items]="items"
    [selectable]="selectable"
    [showMoreLabel]="showMoreLabel"
    [showLessLabel]="showLessLabel"
    (toggled)="onToggled($event)"
/>
`,
});

/** The interactive type facet: six values, five rows and the show-more link. */
export const Selectable: Story = {
    args: {
        title: "Type",
        items: typeItems,
        selectable: true,
    },
    render: host,
    play: async ({ canvasElement }) => {
        emissions.length = 0;
        const canvas = within(canvasElement);

        // UIC-34's five-row cap: the sixth value waits behind the link.
        await expect(canvas.queryByText("Person")).toBeNull();

        // UIC-34: ticking a row emits the wire value and the new state.
        await userEvent.click(canvas.getByRole("checkbox", { name: "Data Domain (9)" }));
        expect(emissions).toEqual([{ value: "m4i_data_domain", checked: true }]);
    },
};

/** A ticked selection: the checked rows mirror the caller's store (SDX-04). */
export const WithSelection: Story = {
    args: {
        title: "Type",
        items: typeItems.map((item) => ({ ...item, checked: item.value === "m4i_data_domain" })),
        selectable: true,
    },
    render: host,
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await expect(canvas.getByRole("checkbox", { name: "Data Domain (9)" })).toBeChecked();
        await expect(canvas.getByRole("checkbox", { name: "Data Attribute (75)" })).not.toBeChecked();
    },
};

/** "Show more" reveals the hidden rows and flips to "Show less" (UIC-34). */
export const ShowMore: Story = {
    args: {
        title: "Type",
        items: typeItems,
        selectable: true,
        showMoreLabel: "Show more",
        showLessLabel: "Show less",
    },
    render: host,
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);

        await userEvent.click(canvas.getByText("Show more"));
        await expect(canvas.getByText("Person")).toBeTruthy();

        await userEvent.click(canvas.getByText("Show less"));
        await expect(canvas.queryByText("Person")).toBeNull();
    },
};

/** The read-only state facet (SDX-05): the same rows, no checkboxes. */
export const ReadOnly: Story = {
    args: {
        title: "State",
        items: [{ value: "ACTIVE", label: "ACTIVE", count: 141 }],
        selectable: false,
    },
    render: host,
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await expect(canvas.queryByRole("checkbox")).toBeNull();
        await expect(canvas.getByText("ACTIVE")).toBeTruthy();
        await expect(canvas.getByText("(141)")).toBeTruthy();
    },
};
