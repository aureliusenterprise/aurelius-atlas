import type { Meta, StoryObj } from "@storybook/angular";
import { expect } from "storybook/test";

import { GovQualityList, GovQualityRow } from "./gov-quality-list.component";

/**
 * The card's governance-quality column (UIC-38): a warning with the
 * non-compliant count and a hover dropdown of rows, a green check when all
 * pass, a spinner while the caller fetches. 7.25 wires it into the entity
 * cards' quality column (DD-447).
 */
const meta: Meta<GovQualityList> = {
    component: GovQualityList,
    title: "Gov Quality List",
};
export default meta;

type Story = StoryObj<GovQualityList>;

const nonCompliant: GovQualityRow[] = [
    { message: "This entity is missing a kibanaSpace", detail: "attribute: completeness" },
    { message: "The entity has no business owner", detail: "attribute: businessOwner" },
];

/** The warning state: hover the count to open the rows. */
export const NonCompliant: Story = {
    args: {
        nonCompliant,
        loading: false,
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("2x")).toBeVisible();
    },
};

/** All rules pass: the green check. */
export const Compliant: Story = {
    args: {
        nonCompliant: [],
        loading: false,
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByRole("menu", { hidden: true })).toBeNull();
    },
};

/** The verdicts are still in flight. */
export const Loading: Story = {
    args: {
        nonCompliant: [],
        loading: true,
    },
};
