import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";

import type { AlertGroup } from "../alert-list/alert-group";
import { AlertInbox } from "./alert-inbox.component";

/**
 * The inbox bar (ALR-11, ALR-12): severity chips with counts, an unread
 * dot per severity, filter toggling, and the caller's clear-all action
 * projected in. Presentational — stories supply the feed the app's
 * store would produce; the panel applies the filter.
 */
const meta: Meta<AlertInbox> = {
    component: AlertInbox,
    title: "AlertInbox",
};
export default meta;

type Story = StoryObj<AlertInbox>;

const alerts: AlertGroup[] = [
    {
        id: "e1",
        severity: "error",
        message: "Request failed: GET /api/entity/guid/7 500",
        count: 7,
        lastSeen: Date.UTC(2026, 9, 21, 10, 30),
        read: false,
    },
    {
        id: "e2",
        severity: "error",
        message: "Request failed: POST /api/search 502",
        count: 1,
        lastSeen: Date.UTC(2026, 9, 21, 10, 29),
        read: true,
    },
    {
        id: "w1",
        severity: "warning",
        message: "Search is slow: the query took 8.2s.",
        count: 2,
        lastSeen: Date.UTC(2026, 9, 21, 10, 28),
        read: false,
    },
    {
        id: "i1",
        severity: "info",
        message: "Draft saved.",
        count: 1,
        lastSeen: Date.UTC(2026, 9, 21, 10, 27),
        read: true,
    },
];

/**
 * The full bar, in inbox order (info, warning, error — the ramp, calm
 * to urgent, DD-092): three severity-coloured chips with totals, the
 * unread dots on the severities with unread groups (warning, error),
 * every chip pressed (nothing hidden). The play() toggles the warning
 * chip off and sees the output. The caller's clear-all action joins the
 * bar as an expanded member (DD-090, DD-092) — the host test in the
 * spec covers the projection.
 */
export const Primary: Story = {
    args: {
        alerts,
        hidden: [],
        ariaLabel: "Alert filters",
        unreadLabel: "Unread",
        showAllLabel: "Show all",
    },
    play: async ({ canvasElement, componentInstance }) => {
        const chips = [...(canvasElement.querySelectorAll(".aurelius-alert-inbox-chip") as NodeListOf<HTMLElement>)];
        expect(chips).toHaveLength(3);
        expect(chips.map((c) => c.getAttribute("aria-pressed"))).toEqual(["true", "true", "true"]);
        // The pressed chips ride their severity's fill (DD-092).
        expect(chips.map((c) => [...c.classList].find((k) => k.startsWith("is-sev-")))).toEqual([
            "is-sev-info",
            "is-sev-warning",
            "is-sev-error",
        ]);
        // The unread dots: warning and error have unread groups (ALR-12).
        expect(canvasElement.querySelectorAll(".aurelius-alert-inbox-unread")).toHaveLength(2);
        // The chips' totals (ALR-11), inbox order.
        const counts = [...(canvasElement.querySelectorAll(".aurelius-alert-inbox-count") as NodeListOf<HTMLElement>)];
        expect(counts.map((c) => c.textContent.trim())).toEqual(["1", "1", "2"]);

        const toggled: string[] = [];
        componentInstance.toggleSeverity.subscribe((s: string) => toggled.push(s));
        const warning = within(canvasElement).getByRole("button", { name: /Warnings/ });
        await userEvent.click(warning);
        expect(toggled).toEqual(["warning"]);
    },
};

/**
 * A filtered feed: warnings hidden, its chip flat and unpressed while
 * the others stay filled.
 */
export const Filtered: Story = {
    args: {
        alerts,
        hidden: ["warning"],
    },
    play: async ({ canvasElement }) => {
        const chips = [...(canvasElement.querySelectorAll(".aurelius-alert-inbox-chip") as NodeListOf<HTMLElement>)];
        expect(chips.map((c) => c.getAttribute("aria-pressed"))).toEqual(["true", "false", "true"]);
        expect(chips[1].classList.contains("is-selected")).toBe(false);
    },
};

/**
 * Every filter off: the chips are all flat and the show-all control
 * appears (ALR-11's escape hatch).
 */
export const AllHidden: Story = {
    args: {
        alerts,
        hidden: ["error", "warning", "info"],
    },
    play: async ({ canvas, canvasElement, componentInstance }) => {
        expect(canvasElement.querySelector(".aurelius-alert-inbox-show-all")).toBeTruthy();
        const calls: number[] = [];
        componentInstance.showAll.subscribe(() => calls.push(1));
        await userEvent.click(canvas.getByRole("button", { name: "Show all" }));
        expect(calls).toEqual([1]);
    },
};

/**
 * The empty feed: the bar keeps its shape, every count zero — and every
 * chip reads grey, disabled (DD-094): a filter with nothing to show has
 * nothing to toggle. (In the app the bar shows at the store's first
 * alert; the story renders the component bare.)
 */
export const Empty: Story = {
    args: {
        alerts: [],
        hidden: [],
    },
    play: async ({ canvasElement }) => {
        const counts = [...(canvasElement.querySelectorAll(".aurelius-alert-inbox-count") as NodeListOf<HTMLElement>)];
        expect(counts.map((c) => c.textContent.trim())).toEqual(["0", "0", "0"]);
        expect(canvasElement.querySelector(".aurelius-alert-inbox-unread")).toBeNull();
        const chips = [
            ...(canvasElement.querySelectorAll(".aurelius-alert-inbox-chip") as NodeListOf<HTMLButtonElement>),
        ];
        expect(chips.every((c) => c.disabled)).toBe(true);
    },
};
