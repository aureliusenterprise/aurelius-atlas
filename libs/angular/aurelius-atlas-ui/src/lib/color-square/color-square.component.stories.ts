import type { Meta, StoryObj } from "@storybook/angular";
import { expect, waitFor } from "storybook/test";

import { ColorSquare } from "./color-square.component";

/**
 * The colour square (UIC-32, DD-421): the clickable square behind the
 * legend's colour picker — the legacy's `ColorSquareComponent`, driven by
 * a native input so the popover dependency stays out. Click the square and
 * the browser's picker opens; the picked hex leaves through
 * `colorPicked`. The read-only story draws the bare square — the
 * `editable=false` state for a surface that shows a colour but must not
 * change one.
 */
const meta: Meta<ColorSquare> = {
    component: ColorSquare,
    title: "Color Square",
    args: { color: "#3366cc", editable: true, label: "Colour" },
    argTypes: { color: { control: "color" } },
};
export default meta;
type Story = StoryObj<ColorSquare>;

/** The editable square: click it and the platform picker opens. */
export const Default: Story = {
    play: async ({ canvasElement }) => {
        const canvas = canvasElement as HTMLElement;
        const square = canvas.querySelector<HTMLInputElement>("input[type='color']");
        await expect(square?.value).toBe("#3366cc");
    },
};

/** The read-only square (the legacy's `enableColorPicker` off): no picker. */
export const ReadOnly: Story = {
    args: { color: "#dc3912", editable: false },
    play: async ({ canvasElement }) => {
        const canvas = canvasElement as HTMLElement;
        await waitFor(() => expect(canvas.querySelector("span.color-square")).toBeTruthy());
        await expect(canvas.querySelector("input[type='color']")).toBeNull();
    },
};
