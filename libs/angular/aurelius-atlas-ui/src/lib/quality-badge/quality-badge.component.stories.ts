import type { Meta, StoryObj } from "@storybook/angular";
import { expect } from "storybook/test";

import { QualityBadge } from "./quality-badge.component";

/**
 * The card's data-quality badge (UIC-39): the pie beside the percent, the
 * legacy rule card's `dqscore` line. It is the `entity-card`
 * `[card-quality]` content once 7.25 turns the quality column on (DD-447).
 */
const meta: Meta<QualityBadge> = {
    component: QualityBadge,
    title: "Quality Badge",
};
export default meta;

type Story = StoryObj<QualityBadge>;

/** A healthy rule score. */
export const Primary: Story = {
    args: {
        score: 0.92,
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("92%")).toBeVisible();
    },
};

/** The failing end. */
export const Low: Story = {
    args: {
        score: 0.12,
    },
};
