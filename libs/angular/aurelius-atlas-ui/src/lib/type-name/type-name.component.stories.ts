import type { Meta, StoryObj } from "@storybook/angular";
import { expect } from "storybook/test";
import { faProjectDiagram, faTable } from "@fortawesome/free-solid-svg-icons";

import { TypeName } from "./type-name.component";

/**
 * The type badge: the entity type's icon (coloured by its type class) and
 * name, with the alias overriding the name and an optional base-type
 * suffix. The details header's type line, the card badge, the
 * propagated-sources rows, and 7.7's editor all render this (DD-100).
 */
const meta: Meta<TypeName> = {
    component: TypeName,
    title: "Type Name",
};
export default meta;

type Story = StoryObj<TypeName>;

const host = (args: Record<string, unknown>) => ({ props: { ...args } });

/**
 * A technical type: the table icon in the technical blue, the raw type
 * name as text, and the name as the badge's title.
 */
export const Primary: Story = {
    args: {
        typeName: "m4i_dataset",
        icon: faTable,
        iconClass: "technical",
    },
    play: async ({ canvasElement }) => {
        const badge = canvasElement.querySelector("span.icon-text");
        await expect(badge).toBeTruthy();
        await expect(badge!.getAttribute("title")).toBe("m4i_dataset");
        await expect(badge!.querySelector(".icon svg")).toBeTruthy();
        await expect(badge!.textContent).toContain("m4i_dataset");
    },
    render: host,
};

/**
 * The alias display form: the friendly name replaces the raw type, and
 * `showBaseTypeName` keeps the raw type in parentheses — the legacy
 * header's `.subtitle.name` line renders this form.
 */
export const AliasedWithBaseType: Story = {
    args: {
        typeName: "m4i_data_domain",
        typeAlias: "Domain",
        showBaseTypeName: true,
        icon: faProjectDiagram,
        iconClass: "business",
    },
    play: async ({ canvasElement }) => {
        const badge = canvasElement.querySelector("span.icon-text")!;
        await expect(badge.getAttribute("title")).toBe("Domain");
        await expect(badge.textContent).toContain("Domain");
        await expect(badge.textContent).toContain("(m4i_data_domain)");
    },
    render: host,
};

/**
 * Text only: no icon, no alias, no suffix — the badge inside a dense row.
 */
export const TextOnly: Story = {
    args: {
        typeName: "m4i_data_entity",
        showIcon: false,
    },
    play: async ({ canvasElement }) => {
        await expect(canvasElement.querySelector(".icon")).toBeNull();
        await expect(canvasElement.textContent).toContain("m4i_data_entity");
    },
    render: host,
};

/**
 * The badge on the dark theme: the legacy pure blue lifts to Bulma's
 * dark-adapted lightness for the dark surface (DD-068), the shared
 * business orange stays. It opens dark — the toolbar Theme switch flips
 * it at any time.
 */
export const OnDark: Story = {
    args: {
        typeName: "m4i_dataset",
        icon: faTable,
        iconClass: "technical",
    },
    parameters: { theme: "dark" },
    play: async ({ canvasElement }) => {
        const el = canvasElement.querySelector<HTMLElement>(".icon.technical");
        if (!el) throw new Error(".icon.technical is missing");
        // The toolbar Theme switch can move this story to either scheme, so
        // the play() asserts the blue of whichever one is active.
        const dark = document.documentElement.dataset["theme"] !== "light";
        await expect(getComputedStyle(el).color).toBe(dark ? "rgb(128, 128, 255)" : "rgb(0, 0, 255)");
    },
    render: host,
};
