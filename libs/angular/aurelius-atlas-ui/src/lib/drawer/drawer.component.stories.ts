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
 * checks the title, the projected content and the slide-in (DD-162), and
 * closes it with the header's close button. `toBeNull` does not poll, so
 * the closed assertions wait out the 200ms exit animation, which is what
 * removes the layer (DD-162).
 */
export const Primary: Story = {
    args: {
        active: false,
        title: "Settings",
        ariaLabel: "Close",
    },
    play: async ({ canvas }) => {
        await expect(canvas.queryByRole("dialog")).toBeNull();

        await userEvent.click(canvas.getByRole("button", { name: "Open settings" }));
        const dialog = canvas.getByRole("dialog", { name: "Settings" });
        await expect(dialog).toBeInTheDocument();
        await expect(within(dialog).getByText("Appearance")).toBeInTheDocument();
        // The panel slides in from the right edge (DD-162); Angular scopes
        // the keyframe name, so match it unanchored.
        await expect(getComputedStyle(dialog).animationName).toMatch(/aurelius-drawer-in/);
        // ...and is anchored to it: the native <dialog>'s sheet pins both
        // edges (`left: 0; right: 0`) for its centered card, and the
        // over-constrained rule drops the END edge, parking a margin-0
        // panel on the LEFT. The style resets the start inset to auto
        // (S6819 fix, 2026-11-05). The rect is the honest pin — Chromium
        // reports a positioned box's computed insets as used px, never
        // `auto` — but it rides the slide-in transform while the entry
        // animation runs, so the check waits for the panel to settle. The
        // client width is the right edge: the scrollbar sits outside the
        // fixed layer, so innerWidth would not match.
        await waitFor(() =>
            expect(Math.round(dialog.getBoundingClientRect().right)).toBe(document.documentElement.clientWidth),
        );

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
        // at once, while the panel is still sliding out (DD-162).
        await expect(canvasElement.ownerDocument.activeElement).toBe(opener);
        // The layer goes when the exit animation ends (DD-162).
        await waitFor(() => expect(canvas.queryByRole("dialog")).toBeNull());
    },
    render: host,
};

/**
 * The panel on the dark theme: the surface and ink follow Bulma's dark
 * scheme (the brand's dark ink ramp, DD-156). It opens dark — the toolbar
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

const actionsTemplate = `
<aurelius-atlas-ui-drawer #drawer [active]="active" title="Alerts" ariaLabel="Close">
    <button type="button" drawer-actions class="button is-small is-text">Clear all</button>
    <div class="notification is-danger">
        <p>Request failed: GET /api/atlas/admin/session 502</p>
    </div>
    <div class="notification is-warning">
        <p>Search is slow: the query took 8.2s.</p>
    </div>
</aurelius-atlas-ui-drawer>
`;

/**
 * The head's action slot (DD-176): content carrying `drawer-actions`
 * projects between the title and the close button, so the escape hatch
 * (Clear all on an alerts feed) rides the sticky head and a long body
 * never buries it. The play() checks the slot's order in the head.
 */
export const HeadActions: Story = {
    args: { active: true },
    play: async ({ canvas }) => {
        const dialog = canvas.getByRole("dialog", { name: "Alerts" });
        const head = dialog.querySelector(".aurelius-drawer-head");
        const clear = canvas.getByRole("button", { name: "Clear all" });
        // In the head, before the close control — not in the scrolling body.
        await expect(head?.contains(clear)).toBe(true);
        await expect(dialog.querySelector(".aurelius-drawer-body button")).toBeNull();
    },
    render: () => ({
        template: actionsTemplate,
        props: { active: true as boolean },
    }),
};

const footerTemplate = `
<aurelius-atlas-ui-drawer #drawer [active]="active" title="Edit entity" ariaLabel="Close">
    <div class="content">
        <p class="title is-6">Name</p>
        <input class="input" value="sales_process" />
    </div>
    <div drawer-footer>
        <div class="buttons is-right">
            <button type="button" class="button is-danger is-outlined" title="Hold for 3 seconds">Delete</button>
            <button type="button" class="button is-primary">Save</button>
        </div>
    </div>
</aurelius-atlas-ui-drawer>
`;

/**
 * The foot slot (UIC-25): content carrying `drawer-footer` sits in a fixed
 * bar below the scrolling body, so a drawer's commit actions (the editor's
 * Save / Delete) never scroll away and never crowd the head. The play()
 * checks the bar's place in the panel — after the body, outside it.
 */
export const FooterCommit: Story = {
    args: { active: true },
    play: async ({ canvas }) => {
        const dialog = canvas.getByRole("dialog", { name: "Edit entity" });
        const foot = dialog.querySelector(".aurelius-drawer-foot");
        const body = dialog.querySelector(".aurelius-drawer-body");
        const save = canvas.getByRole("button", { name: "Save" });
        // The foot holds the actions and sits after the body, in the panel
        // — not inside it, so a long form cannot push the bar away.
        await expect(foot?.contains(save)).toBe(true);
        await expect(foot?.parentElement).toBe(dialog);
        await expect(body?.contains(save)).toBe(false);
        const after = [...(dialog?.children ?? [])].indexOf(foot as HTMLElement);
        await expect(after).toBe([...(dialog?.children ?? [])].indexOf(body as HTMLElement) + 1);
    },
    render: () => ({
        template: footerTemplate,
        props: { active: true as boolean },
    }),
};
