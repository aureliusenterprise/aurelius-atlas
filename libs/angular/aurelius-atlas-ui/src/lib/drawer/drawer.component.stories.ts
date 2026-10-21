import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { Drawer } from "./drawer.component";

/**
 * A settings-style panel that slides in from the right over a scrim:
 * a title, a close button, projected content, and dismissal by scrim
 * click, close button, or Escape.
 */
const meta: Meta<Drawer> = {
    component: Drawer,
    title: "Drawer",
};
export default meta;

type Story = StoryObj<Drawer>;

const template = `
<aurelius-atlas-ui-drawer #drawer [active]="active" [title]="title" [ariaLabel]="ariaLabel">
    <div class="content">
        <p class="title is-6">Appearance</p>
        <label class="radio"><input type="radio" name="theme" checked /> Auto</label>
        <label class="radio"><input type="radio" name="theme" /> Light</label>
        <label class="radio"><input type="radio" name="theme" /> Dark</label>
    </div>
</aurelius-atlas-ui-drawer>
<button class="button is-primary" (click)="drawer.open()">Open settings</button>
`;

const host = (args: Record<string, unknown>) => ({ props: args, template });

/**
 * The panel closed behind an "Open settings" button: the play() opens it,
 * checks the title, the projected content and the slide-in (DD-074), and
 * closes it with the header's close button. `toBeNull` does not poll, so
 * the closed assertions wait out the 200ms exit animation, which is what
 * removes the layer (DD-074).
 */
export const Primary: Story = {
    args: {
        active: false,
        title: "Settings",
        ariaLabel: "Close",
    },
    play: async ({ canvas }) => {
        expect(canvas.queryByRole("dialog")).toBeNull();

        await userEvent.click(canvas.getByRole("button", { name: "Open settings" }));
        const dialog = canvas.getByRole("dialog", { name: "Settings" });
        await expect(dialog).toBeInTheDocument();
        await expect(within(dialog).getByText("Appearance")).toBeInTheDocument();
        // The panel slides in from the right edge (DD-074); Angular scopes
        // the keyframe name, so match it unanchored.
        expect(getComputedStyle(dialog).animationName).toMatch(/aurelius-drawer-in/);

        await userEvent.click(within(dialog).getByRole("button", { name: "Close" }));
        await waitFor(() => expect(canvas.queryByRole("dialog")).toBeNull());
    },
    render: host,
};

/**
 * Escape is the keyboard dismissal path: the play() opens the panel and
 * presses Escape, which closes it and returns focus to the opener.
 */
export const EscapeCloses: Story = {
    args: {
        active: false,
        title: "Settings",
        ariaLabel: "Close",
    },
    play: async ({ canvas, canvasElement }) => {
        const opener = canvas.getByRole("button", { name: "Open settings" });
        await userEvent.click(opener);
        const dialog = canvas.getByRole("dialog", { name: "Settings" });
        await expect(dialog).toBeInTheDocument();

        await userEvent.keyboard("{Escape}");
        // Focus returns to the button that opened the panel (SPL-02) —
        // at once, while the panel is still sliding out (DD-074).
        await expect(canvasElement.ownerDocument.activeElement).toBe(opener);
        // The layer goes when the exit animation ends (DD-074).
        await waitFor(() => expect(canvas.queryByRole("dialog")).toBeNull());
    },
    render: host,
};

/**
 * The panel on the dark theme: the surface and ink follow Bulma's dark
 * scheme (the brand's dark ink ramp, DD-068). It opens dark — the toolbar
 * Theme switch (top bar) flips it to light or Auto at any time.
 */
export const OnDark: Story = {
    args: {
        active: true,
        title: "Settings",
        ariaLabel: "Close",
    },
    parameters: { theme: "dark" },
    play: async ({ canvasElement }) => {
        const panel = canvasElement.querySelector<HTMLElement>(".aurelius-drawer-panel");
        if (!panel) throw new Error("the panel is missing");
        // The toolbar Theme switch can move this story to either scheme, so
        // assert the surface of whichever one is active.
        const dark = document.documentElement.dataset["theme"] !== "light";
        await expect(panel).toHaveStyle({
            "background-color": dark ? "rgb(20, 22, 26)" : "rgb(255, 255, 255)",
        });
        const title = canvasElement.querySelector<HTMLElement>(".aurelius-drawer-title");
        if (!title) throw new Error("the title is missing");
        await expect(getComputedStyle(title).color).toBe(dark ? "rgb(237, 237, 237)" : "rgb(54, 54, 54)");
    },
    render: host,
};
