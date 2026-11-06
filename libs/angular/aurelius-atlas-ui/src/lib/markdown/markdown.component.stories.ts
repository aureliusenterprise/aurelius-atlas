import type { Meta, StoryObj } from "@storybook/angular";
import { expect } from "storybook/test";

import { Markdown } from "./markdown.component";

/**
 * The markdown block (`models4insight-markdown`, DD-321): markdown text
 * rendered through marked with the legacy Bulma mappings — headings on the
 * title ramp, blockquotes on the message, tables striped, images as
 * figures — inside a Bulma `content` block. The details description box
 * renders entity descriptions through it.
 */
const meta: Meta<Markdown> = {
    component: Markdown,
    title: "Markdown",
};
export default meta;

type Story = StoryObj<Markdown>;

/**
 * The full document: a heading, emphasis, a quote, and a table, each
 * landing on its Bulma shape.
 */
export const FullDocument: Story = {
    args: {
        markdown:
            "## The dataset\n\nThe **daily** feed lands at 06:00.\n\n" +
            "> Owned by the ingestion team.\n\n" +
            "| Column | Type |\n| --- | --- |\n| id | string |\n| ts | timestamp |",
    },
    play: async ({ canvasElement }) => {
        const content = canvasElement.querySelector(".content.aurelius-markdown");
        await expect(content).toBeTruthy();
        const heading = content!.querySelector("h2")!;
        await expect(heading.classList.contains("title")).toBe(true);
        await expect(heading.classList.contains("is-2")).toBe(true);
        await expect(content!.querySelector("strong")!.textContent).toBe("daily");
        await expect(content!.querySelector("article.message .message-body")).toBeTruthy();
        await expect(content!.querySelector("table.table.is-striped")).toBeTruthy();
    },
};

/**
 * A single line of prose: what most entity descriptions actually are —
 * markdown that never leaves the paragraph level.
 */
export const PlainProse: Story = {
    args: {
        markdown: "A seeded description for the visual comparison.",
    },
    play: async ({ canvasElement }) => {
        const paragraph = canvasElement.querySelector(".content.aurelius-markdown p");
        await expect(paragraph!.textContent).toBe("A seeded description for the visual comparison.");
    },
};
