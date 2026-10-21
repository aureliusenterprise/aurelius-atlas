import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";
import type { AlertGroup } from "./alert-group";
import { AlertList } from "./alert-list.component";

/**
 * The alert feed (ALR-07, ALR-09, ALR-10): severity-coloured Bulma
 * notifications, newest first, a burst chip on merged repeats, and
 * per-row dismissal. The component is presentational — stories supply
 * the groups the app's store would produce. Clearing the feed is the
 * caller's action, placed in the drawer's head (DD-088).
 */
const meta: Meta<AlertList> = {
    component: AlertList,
    title: "AlertList",
};
export default meta;

type Story = StoryObj<AlertList>;

const alerts: AlertGroup[] = [
    {
        id: "g3",
        severity: "info",
        message: "Draft saved.",
        count: 1,
        lastSeen: Date.UTC(2026, 9, 21, 10, 32),
    },
    {
        id: "g2",
        severity: "warning",
        message: "Search is slow: the query took 8.2s.",
        count: 2,
        lastSeen: Date.UTC(2026, 9, 21, 10, 31),
    },
    {
        id: "g1",
        severity: "error",
        message: "Request failed: GET /api/v2/entity/guid/7 500",
        count: 7,
        lastSeen: Date.UTC(2026, 9, 21, 10, 30),
    },
];

/**
 * The full feed: three rows, the severity colours (danger/warning/info,
 * DD-063), burst chips on the merged rows, the time line, and per-row
 * dismissal — the play() dismisses the error row and sees the output.
 */
export const Primary: Story = {
    args: {
        alerts,
        ariaLabel: "Alerts",
        emptyLabel: "No alerts",
        dismissLabel: "Dismiss",
    },
    play: async ({ canvas, canvasElement, componentInstance }) => {
        const rows = [...canvasElement.querySelectorAll(".notification")] as HTMLElement[];
        expect(rows).toHaveLength(3);
        expect(rows[0].classList.contains("is-info")).toBe(true);
        expect(rows[2].classList.contains("is-danger")).toBe(true);
        // The burst chip marks merged repeats (ALR-03, ALR-07).
        await expect(canvas.findByText("×7")).resolves.toBeInTheDocument();

        const dismissed: string[] = [];
        componentInstance.dismiss.subscribe((id: string) => dismissed.push(id));
        await userEvent.click(within(rows[2] as HTMLElement).getByRole("button", { name: "Dismiss" }));
        expect(dismissed).toEqual(["g1"]);
    },
};

/**
 * The empty state: a centered line and no rows (ALR-07). The list never
 * carries a clear control — that action rides the drawer head (DD-088).
 */
export const Empty: Story = {
    args: {
        alerts: [],
        ariaLabel: "Alerts",
        emptyLabel: "No alerts",
    },
    play: async ({ canvas, canvasElement }) => {
        expect(canvasElement.querySelectorAll(".notification")).toHaveLength(0);
        expect(canvas.queryByRole("log")).toBeNull();
        expect(canvas.getByText("No alerts")).toBeInTheDocument();
    },
};
