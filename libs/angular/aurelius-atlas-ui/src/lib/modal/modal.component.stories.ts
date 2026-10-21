import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";
import { Modal } from "./modal.component";

const meta: Meta<Modal> = {
    component: Modal,
    title: "Modal",
};
export default meta;

type Story = StoryObj<Modal>;

const primaryTemplate = `
<aurelius-atlas-ui-modal #modal [active]="active" [showCloseButton]="showCloseButton">
    <ng-container modal-content>
        <figure class="image is-square">
            <img
                src="/assets/logo.jpg"
                alt="Modal Image"
            />
        </figure>
    </ng-container>
</aurelius-atlas-ui-modal>
<button class="button is-primary" (click)="modal.open()">Open Modal</button>
`;

const emptyTemplate = `
<aurelius-atlas-ui-modal #modal [active]="active" [showCloseButton]="showCloseButton"></aurelius-atlas-ui-modal>
<button class="button is-primary" (click)="modal.open()">Open Modal</button>
`;

const cardTemplate = `
<aurelius-atlas-ui-modal
    #modal
    [active]="active"
    [title]="title"
    [confirmLabel]="confirmLabel"
    [cancelLabel]="cancelLabel"
    [showCloseButton]="false"
>
    <ng-container modal-content>
        <p>Removing a branch cannot be undone.</p>
    </ng-container>
</aurelius-atlas-ui-modal>
<button class="button is-primary" (click)="modal.open()">Open Modal</button>
`;

export const Primary: Story = {
    args: {
        active: false,
        showCloseButton: true,
    },
    render: (args) => ({
        props: args,
        template: primaryTemplate,
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await userEvent.click(canvas.getByRole("button", { name: "Open Modal" }));
        await expect(canvas.getByRole("img", { name: "Modal Image" })).toBeInTheDocument();
        await userEvent.click(canvas.getByRole("button", { name: "Close" }));
        await expect(canvas.queryByRole("img", { name: "Modal Image" })).toBeNull();
    },
};

export const CardAnatomy: Story = {
    args: {
        active: false,
        title: "Delete branch",
        confirmLabel: "Delete",
        cancelLabel: "Cancel",
    },
    render: (args) => ({
        props: args,
        template: cardTemplate,
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await userEvent.click(canvas.getByRole("button", { name: "Open Modal" }));
        await expect(canvas.getByText("Delete branch")).toBeInTheDocument();
        await userEvent.click(canvas.getByRole("button", { name: "Cancel" }));
        await expect(canvas.queryByText("Delete branch")).toBeNull();
    },
};

export const Empty: Story = {
    args: {
        active: false,
        showCloseButton: true,
    },
    render: (args) => ({
        props: args,
        template: emptyTemplate,
    }),
};
