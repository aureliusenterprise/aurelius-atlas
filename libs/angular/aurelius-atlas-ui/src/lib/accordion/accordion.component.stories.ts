import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";
import { Accordion } from "./accordion.component";

/**
 * A collapsible panel: a header bar with a toggle, and a content area the
 * caller projects. Starts open; the toggle collapses it.
 */
const meta: Meta<Accordion> = {
    component: Accordion,
    title: "Accordion",
};
export default meta;

type Story = StoryObj<Accordion>;

const primaryTemplate = `
<aurelius-atlas-ui-accordion [expanded]="expanded">
    <ng-container header>
        <p>Accordion Header</p>
    </ng-container>
    <ng-container content>
        <p>Accordion Content</p>
    </ng-container>
</aurelius-atlas-ui-accordion>
`;

/** Open: the content shows, and the play() collapses it with a click. */
export const Primary: Story = {
    args: {
        expanded: true,
    },
    render: (args) => ({
        props: args,
        template: primaryTemplate,
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await userEvent.click(canvas.getByRole("button", { name: "Toggle content" }));
        await expect(canvas.queryByText("Accordion Content")).toBeNull();
    },
};

/** Collapsed: only the header shows, and the play() opens the content. */
export const Collapsed: Story = {
    args: {
        expanded: false,
    },
    render: (args) => ({
        props: args,
        template: primaryTemplate,
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await expect(canvas.queryByText("Accordion Content")).toBeNull();
        await userEvent.click(canvas.getByRole("button", { name: "Toggle content" }));
        await expect(canvas.getByText("Accordion Content")).toBeInTheDocument();
    },
};

/** No header or content projected: the empty shell. */
export const Empty: Story = {
    args: {
        expanded: false,
    },
};
