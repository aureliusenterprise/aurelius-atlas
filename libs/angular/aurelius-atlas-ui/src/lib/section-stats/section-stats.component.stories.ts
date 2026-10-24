import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent } from "storybook/test";

import { SectionStat, SectionStats } from "./section-stats.component";

/**
 * The section count bar: a heading-link and a count per section, the
 * Aurelius pattern above the details screen's sections. Clicking a
 * heading emits `itemClicked(target)` — the app smooth-scrolls (DD-191).
 */
const meta: Meta<SectionStats> = {
    component: SectionStats,
    title: "Section Stats",
};
export default meta;

type Story = StoryObj<SectionStats>;

const govQuality: SectionStat[] = [
    { label: "Non-compliant", target: "related-non-compliants", count: 3 },
    { label: "Compliant", target: "related-compliants", count: 12 },
    { label: "Properties", target: "properties-details", count: 27 },
];

/** The guids/targets the play() tests collect from itemClicked. */
const clicked: string[] = [];

const host = (args: Record<string, unknown>) => ({
    props: { ...args, onStat: (target: string) => clicked.push(target) },
    template: `
<aurelius-atlas-ui-section-stats
    [items]="items"
    (itemClicked)="onStat($event)"
></aurelius-atlas-ui-section-stats>
`,
});

/**
 * The governance-quality bar: three stats, each heading a jump link to
 * its section, the counts above the fold. Clicking a heading emits its
 * target (DD-154's pattern — the lib emits, the app scrolls).
 */
export const Primary: Story = {
    args: {
        items: govQuality,
    },
    play: async ({ canvas }) => {
        clicked.length = 0;
        await expect(canvas.getByText("3")).toBeVisible();
        await expect(canvas.getByText("12")).toBeVisible();
        await expect(canvas.getByText("27")).toBeVisible();

        await userEvent.click(canvas.getByRole("link", { name: "Compliant" }));
        await expect(clicked).toEqual(["related-compliants"]);
    },
    render: host,
};

/**
 * The default-details bar: a single Properties stat, the shape the 7.6
 * skeleton's inline bar becomes when the wiring increment lands (DD-192).
 */
export const SingleStat: Story = {
    args: {
        items: [{ label: "Properties", target: "properties-details", count: 0 }],
    },
    play: async ({ canvas }) => {
        await expect(canvas.getAllByRole("link")).toHaveLength(1);
        await expect(canvas.getByRole("link", { name: "Properties" })).toHaveAttribute("href", "#properties-details");
        await expect(canvas.getByText("0")).toBeVisible();
    },
    render: host,
};

/**
 * The empty bar: the `nav.level` with no items — the state a section
 * carries before its count resolves, as the legacy bars rendered empty.
 */
export const Empty: Story = {
    args: {
        items: [],
    },
    play: async ({ canvas }) => {
        await expect(canvas.queryAllByRole("link")).toHaveLength(0);
    },
    render: host,
};
