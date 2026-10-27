import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent } from "storybook/test";

import { DetailsNavigation } from "./details-navigation.component";

/**
 * The sticky section navigation: a round toggle at the bottom-right
 * opens an upward Bulma dropdown holding the menu — the details screen's
 * section links, projected by the caller. The scroll behaviour the items
 * anchor is app-side (DD-191).
 */
const meta: Meta<DetailsNavigation> = {
    component: DetailsNavigation,
    title: "Details Navigation",
};
export default meta;

type Story = StoryObj<DetailsNavigation>;

/** The template binding the inputs, with the legacy default items. */
const template = `
<div class="story-tall-host">
    <aurelius-atlas-ui-details-navigation [label]="label" [toggleLabel]="toggleLabel">
        <li><a href="#properties-details">Properties</a></li>
    </aurelius-atlas-ui-details-navigation>
</div>
`;

const host = (args: Record<string, unknown>) => ({ props: { ...args }, template });

/**
 * The closed shell: the round bars toggle, sticky bottom-right. Clicking
 * it opens the menu upward; the toggle keeps no focus ring — the legacy
 * blur.
 */
export const Primary: Story = {
    args: {
        label: "Details",
        toggleLabel: "navigation",
    },
    play: async ({ canvas, canvasElement }) => {
        const button = canvas.getByRole("button", { name: "navigation" });
        await expect(button).toBeVisible();

        await userEvent.click(button);
        const menu = canvasElement.querySelector(".menu");
        await expect(menu).toBeInTheDocument();
        await expect(canvasElement.querySelector(".dropdown.is-active")).toBeTruthy();
        await expect(canvas.getByRole("link", { name: "Properties" })).toBeVisible();

        await userEvent.click(button);
        await expect(canvasElement.querySelector(".dropdown.is-active")).toBeNull();
    },
    render: host,
};

/**
 * The menu with the section links a populated details screen carries —
 * the items are caller markup, so the app's anchors and directives ride
 * them unchanged (DD-191).
 */
export const WithSections: Story = {
    args: {
        label: "Details",
    },
    play: async ({ canvas, canvasElement }) => {
        await userEvent.click(canvas.getByRole("button"));
        const links = canvas.getAllByRole("link");
        await expect(links).toHaveLength(4);
        await expect(canvasElement.querySelector(".menu-list")!.textContent).toContain("Description");
    },
    render: (args) => ({
        props: { ...args },
        template: `
<div class="story-tall-host">
    <aurelius-atlas-ui-details-navigation [label]="label">
        <li><a href="#description-details">Description</a></li>
        <li><a href="#properties-details">Properties</a></li>
        <li><a href="#classifications-details">Classifications</a></li>
        <li><a href="#terms-details">Terms</a></li>
    </aurelius-atlas-ui-details-navigation>
</div>`,
    }),
};
