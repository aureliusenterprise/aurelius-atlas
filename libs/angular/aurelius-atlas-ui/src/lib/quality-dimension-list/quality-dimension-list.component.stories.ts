import type { Meta, StoryObj } from "@storybook/angular";
import { expect } from "storybook/test";

import { QualityDimensionList, QualityDimensionRow } from "./quality-dimension-list.component";

/**
 * The data-quality dimension rows (UIC-37): a pie, a percent, the
 * dimension, and the count per row — the legacy list above the details
 * fold. The caller selects the dimensions it carries; the empty set shows
 * the placeholder. 7.25 wires it when the scores return (DD-437).
 */
const meta: Meta<QualityDimensionList> = {
    component: QualityDimensionList,
    title: "Quality Dimension List",
};
export default meta;

type Story = StoryObj<QualityDimensionList>;

const dimensions: QualityDimensionRow[] = [
    { dimension: "accuracy", score: 0.92, count: 34 },
    { dimension: "completeness", score: 0.66, count: 12 },
    { dimension: "timeliness", score: 0.5, count: 3 },
    { dimension: "uniqueness", score: 1, count: 8 },
    { dimension: "validity", score: 0.25, count: 2 },
];

/** The legacy's five dimensions, the scores a healthy entity carried. */
export const Primary: Story = {
    args: {
        dimensions,
        notAvailable: "No data quality results available",
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("(34)")).toBeVisible();
    },
};

/** No scores: the italic placeholder, the legacy's `notAvailable`. */
export const NotAvailable: Story = {
    args: {
        dimensions: [],
        notAvailable: "No data quality results available",
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("No data quality results available")).toBeVisible();
    },
};
