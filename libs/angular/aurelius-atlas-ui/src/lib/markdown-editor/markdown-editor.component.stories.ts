import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";

import { MarkdownEditor } from "./markdown-editor.component";

/**
 * The markdown-writing field (UIC-26, DD-352): Bulma `tabs` over a textarea
 * (Write) and the shared {@link Markdown} block (Preview), a Signal Forms
 * control (DD-354). The entity editor's description keys ride it (EDT-20);
 * the caller supplies every string (UIC-04). The story renders the bare
 * field — loose, it edits its own value; the bound loop lives in the unit
 * spec.
 */
const meta: Meta<MarkdownEditor> = {
    component: MarkdownEditor,
    title: "Markdown Editor",
};
export default meta;

type Story = StoryObj<MarkdownEditor>;

/**
 * The empty field, the legacy first shape: Write active, the placeholder
 * shown. The play() types a heading, switches to Preview, and finds the
 * rendered Bulma title — the write-then-preview circle in one pass.
 */
export const Primary: Story = {
    args: {
        writeLabel: "Write",
        previewLabel: "Preview",
        placeholder: "Please type some markdown to get started...",
        textareaId: "story-description",
    },
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        const area = canvas.getByPlaceholderText("Please type some markdown to get started...");
        await expect(area).toHaveAttribute("id", "story-description");

        await userEvent.type(area, "# Heading from the story");

        await userEvent.click(canvas.getByRole("tab", { name: "Preview" }));
        const previewPane = canvasElement.querySelector(".aurelius-markdown-editor-preview");
        const heading = previewPane?.querySelector("h1");
        await expect(heading?.classList.contains("title")).toBe(true);
        await expect(heading?.textContent).toBe("Heading from the story");

        // Back to Write: the source is where it was — the pane only hid.
        await userEvent.click(canvas.getByRole("tab", { name: "Write" }));
        await expect(area).toHaveValue("# Heading from the story");
    },
};

/** A seeded document, shown straight in the Preview tab. */
export const PreviewOpen: Story = {
    args: {
        writeLabel: "Write",
        previewLabel: "Preview",
        placeholder: "Please type some markdown to get started...",
    },
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await userEvent.click(canvas.getByRole("tab", { name: "Preview" }));
        await expect(canvas.getByRole("tab", { name: "Preview" })).toHaveAttribute("aria-selected", "true");
    },
};
