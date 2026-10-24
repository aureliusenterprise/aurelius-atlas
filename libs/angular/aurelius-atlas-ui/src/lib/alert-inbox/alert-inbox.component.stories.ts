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

/** The severities the play() tests collect from toggleSeverity (the render-template spy). */
const toggled: string[] = [];

/** The template binding the inputs, with the toggleSeverity spy. */
const template = `
<aurelius-atlas-ui-alert-inbox
    [alerts]="alerts"
    [hidden]="hidden"
    [ariaLabel]="ariaLabel"
    [unreadLabel]="unreadLabel"
    (toggleSeverity)="onToggle($event)"
></aurelius-atlas-ui-alert-inbox>
`;

const host = (args: Record<string, unknown>) => ({
    props: { ...args, onToggle: (s: string) => toggled.push(s) },
    template,
});

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
 * to urgent, DD-182): three severity-coloured chips with totals, the
 * unread dots on the severities with unread groups (warning, error),
 * every chip pressed (nothing hidden). The play() toggles the warning
 * chip off and sees the output. The caller's clear-all action joins the
 * bar as an expanded member (DD-180, DD-182) — the host test in the
 * spec covers the projection.
 */
export const Primary: Story = {
    args: {
        alerts,
        hidden: [],
        ariaLabel: "Alert filters",
        unreadLabel: "Unread",
    },
    play: async ({ canvasElement }) => {
        const chips = [...(canvasElement.querySelectorAll(".aurelius-alert-inbox-chip") as NodeListOf<HTMLElement>)];
        expect(chips).toHaveLength(3);
        expect(chips.map((c) => c.getAttribute("aria-pressed"))).toEqual(["true", "true", "true"]);
        // The pressed chips ride their severity's fill (DD-182).
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

        // The toggle spy rides the render template: under zoneless,
        // componentInstance is not handed to play() (the breadcrumbs pattern).
        toggled.length = 0;
        const warning = within(canvasElement).getByRole("button", { name: /Warnings/ });
        await userEvent.click(warning);
        expect(toggled).toEqual(["warning"]);
    },
    render: host,
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
 * Every filter off: the chips are all flat, the bar unchanged (DD-185
 * — no show-all control appears; the bar's shape never shifts). The
 * way back is a chip: play() clicks info and sees the toggle output.
 */
export const AllHidden: Story = {
    args: {
        alerts,
        hidden: ["error", "warning", "info"],
    },
    play: async ({ canvasElement }) => {
        expect(canvasElement.querySelector(".aurelius-alert-inbox-show-all")).toBeNull();
        const chips = [...(canvasElement.querySelectorAll(".aurelius-alert-inbox-chip") as NodeListOf<HTMLElement>)];
        expect(chips.map((c) => c.getAttribute("aria-pressed"))).toEqual(["false", "false", "false"]);
        toggled.length = 0;
        await userEvent.click(within(canvasElement).getByRole("button", { name: /Info/ }));
        expect(toggled).toEqual(["info"]);
    },
    render: host,
};

/**
 * The empty feed: the bar keeps its shape, every count zero — and every
 * chip reads grey, disabled (DD-184): a filter with nothing to show has
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
