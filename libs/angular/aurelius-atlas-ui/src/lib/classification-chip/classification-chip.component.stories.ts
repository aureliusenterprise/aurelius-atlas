import type { Meta, StoryObj } from "@storybook/angular";
import { expect } from "storybook/test";

import { ClassificationChip } from "./classification-chip.component";

/**
 * The Bulma addons chip a classification renders as: a lead tag (type
 * icon), the name with the type's description as tooltip, and — when the
 * classification is propagated — a trigger tag whose hoverable dropdown
 * lists the sources. The sources rows are caller-projected content.
 */
const meta: Meta<ClassificationChip> = {
    component: ClassificationChip,
    title: "Classification Chip",
};
export default meta;

type Story = StoryObj<ClassificationChip>;

/** The template binding the inputs, with the projected sources. */
const template = `
<aurelius-atlas-ui-classification-chip
    [label]="label"
    [tooltip]="tooltip"
    [leadLabel]="leadLabel"
    [leadColor]="leadColor"
    [loading]="loading"
    [propagated]="propagated"
>
    <div class="dropdown-divider" chip-sources></div>
    <div class="dropdown-item" chip-sources>
        <strong>Orders Dataset</strong> — m4i_dataset
    </div>
</aurelius-atlas-ui-classification-chip>
`;

const host = (args: Record<string, unknown>) => ({ props: { ...args }, template });

/**
 * A plain classification: the hashtag lead and the name. Hovering the
 * lead does nothing — only a propagated chip has a dropdown.
 */
export const Primary: Story = {
    args: {
        label: "PII",
        tooltip: "Personally identifiable information",
    },
    play: async ({ canvasElement }) => {
        await expect(canvasElement.querySelectorAll(".tags .tag")).toHaveLength(2);
        await expect(canvasElement.querySelector(".dropdown")).toBeNull();
    },
    render: host,
};

/**
 * The same chip carrying its tooltip: the label tag's title is the type's
 * description, the legacy chip's hover text.
 */
export const WithDescription: Story = {
    args: {
        label: "Internal",
        tooltip: "For internal use only",
    },
    play: async ({ canvasElement }) => {
        const label = [...canvasElement.querySelectorAll(".tags .tag")].at(-1) as HTMLElement;
        await expect(label.getAttribute("title")).toBe("For internal use only");
    },
    render: host,
};

/**
 * The type definition is being fetched: the lead tag stays, the label is
 * the loader tag.
 */
export const Loading: Story = {
    args: {
        label: "PII",
        loading: true,
    },
    play: async ({ canvasElement }) => {
        await expect(canvasElement.querySelector(".tag .loader")).toBeTruthy();
        await expect(canvasElement.querySelector(".tags")).not.toHaveTextContent("PII");
    },
    render: host,
};

/**
 * A propagated classification: the third tag (angle-double-right) is the
 * hoverable trigger; its dropdown lists the sources the app projected —
 * rows the chip does not own (DD-099).
 */
export const Propagated: Story = {
    args: {
        label: "PII",
        tooltip: "Personally identifiable information",
        propagated: true,
    },
    play: async ({ canvasElement }) => {
        const trigger = canvasElement.querySelector(".tag.is-primary.dropdown.is-hoverable");
        await expect(trigger).toBeTruthy();
        await expect(trigger!.getAttribute("title")).toBe("Is propagated");
        await expect(trigger!.querySelector("strong")!.textContent).toBe("PII");
        await expect(trigger!.textContent).toContain("originates from the following sources:");
        await expect(trigger!.textContent).toContain("Orders Dataset");
    },
    render: host,
};

/**
 * The glossary-term chip: the same atom with the kind's word as lead and
 * the info colour (DD-099) — a twin input set, not a twin component.
 */
export const Term: Story = {
    args: {
        label: "Revenue",
        tooltip: "The agreed definition of revenue",
        leadLabel: "Term",
        leadColor: "is-info",
    },
    play: async ({ canvasElement }) => {
        const lead = canvasElement.querySelector(".tag.is-info");
        await expect(lead).toBeTruthy();
        await expect(lead!.textContent).toContain("Term");
        await expect(canvasElement.textContent).toContain("Revenue");
    },
    render: host,
};
