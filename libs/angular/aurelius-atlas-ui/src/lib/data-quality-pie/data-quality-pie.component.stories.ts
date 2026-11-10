import type { Meta, StoryObj } from "@storybook/angular";
import { expect } from "storybook/test";

import { DataQualityPie } from "./data-quality-pie.component";

/**
 * The data-quality score circle (UIC-36): a green arc over a red ring, the
 * percent in the tooltip. The caller scales a 0..1 score into the 0..100
 * value. 7.25 wires it into the score boxes and the card badges (DD-447).
 */
const meta: Meta<DataQualityPie> = {
    component: DataQualityPie,
    title: "Data Quality Pie",
};
export default meta;

type Story = StoryObj<DataQualityPie>;

const host = (args: Record<string, unknown>) => ({
    props: { ...args },
    template: `<div style="width: 2rem; height: 2rem;">
    <aurelius-atlas-ui-data-quality-pie [value]="value" [size]="size"></aurelius-atlas-ui-data-quality-pie>
</div>`,
});

/** A healthy score: the green arc nearly closes the red ring. */
export const Primary: Story = {
    args: {
        value: 82,
        size: 4,
    },
    render: host,
    play: async ({ canvas }) => {
        await expect(canvas.getByTitle("82%")).toBeVisible();
    },
};

/** A failing score: the ring stays mostly red. */
export const Low: Story = {
    args: {
        value: 12,
        size: 4,
    },
    render: host,
};

/** A thin ring, as the card badge column renders it. */
export const ThinRing: Story = {
    args: {
        value: 55,
        size: 2,
    },
    render: host,
};
