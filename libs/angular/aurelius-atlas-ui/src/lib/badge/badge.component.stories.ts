import type { Meta, StoryObj } from "@storybook/angular";
import { expect } from "storybook/test";
import { Badge } from "./badge.component";

/**
 * A severity dot pinned to the top-right of wrapped content — the
 * notifications marker on a nav item: a bell with an error badge,
 * hidden by default, coloured by severity (ALR-02).
 */
const meta: Meta<Badge> = {
    component: Badge,
    title: "Badge",
};
export default meta;

type Story = StoryObj<Badge>;

const template = `
<div class="buttons are-medium">
    <aurelius-atlas-ui-badge [visible]="visible" [severity]="severity" [label]="label">
        <span class="icon is-medium story-bell">&#128276;</span>
    </aurelius-atlas-ui-badge>
</div>
`;

const host = (args: Record<string, unknown>) => ({ props: args, template });

/**
 * The error state: a red dot on the bell's corner. The play() checks the
 * dot renders and carries the severity class (ALR-02).
 */
export const ErrorSeverity: Story = {
    args: {
        visible: true,
        severity: "error",
        label: "Notifications",
    },
    play: async ({ canvasElement }) => {
        const dot = canvasElement.querySelector(".aurelius-badge-dot");
        expect(dot?.classList.contains("is-error")).toBe(true);
        expect(dot?.getAttribute("aria-hidden")).toBe("true");
    },
    render: host,
};

/**
 * The warning severity: the amber ramp entry.
 */
export const WarningSeverity: Story = {
    args: {
        visible: true,
        severity: "warning",
        label: "Notifications",
    },
    render: host,
};

/**
 * The info severity: the teal-blue ramp entry.
 */
export const InfoSeverity: Story = {
    args: {
        visible: true,
        severity: "info",
        label: "Notifications",
    },
    render: host,
};

/**
 * The hidden state: the content renders, the dot does not (ALR-02).
 */
export const Hidden: Story = {
    args: {
        visible: false,
        severity: "error",
        label: "Notifications",
    },
    play: async ({ canvasElement }) => {
        expect(canvasElement.querySelector(".aurelius-badge-dot")).toBeNull();
    },
    render: host,
};
