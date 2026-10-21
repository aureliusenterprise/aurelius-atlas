import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent } from "storybook/test";
import { faProjectDiagram } from "@fortawesome/free-solid-svg-icons";

import { EntityCard } from "./entity-card.component";

const meta: Meta<EntityCard> = {
    component: EntityCard,
    title: "Entity Card",
};
export default meta;

type Story = StoryObj<EntityCard>;

/** The template projecting the card's slots, with the entityClicked spy. */
const template = `
<aurelius-atlas-ui-entity-card
    [guid]="guid"
    [name]="name"
    [typeName]="typeName"
    [typeAlias]="typeAlias"
    [typeIcon]="typeIcon"
    [typeIconClass]="typeIconClass"
    [showBaseTypeName]="showBaseTypeName"
    [loading]="loading"
    (entityClicked)="onClick($event)"
>
    <dl card-content>
        <dt>Owner</dt>
        <dd>Aurelius Writer</dd>
    </dl>
    <span card-quality>★★★★☆</span>
</aurelius-atlas-ui-entity-card>
`;

/** The guids the play() tests collect from entityClicked. */
const clicked: string[] = [];

const host = (args: Record<string, unknown>) => ({
    props: {
        ...args,
        onClick: (guid: string) => clicked.push(guid),
        faProjectDiagram,
    },
    template,
});

export const Primary: Story = {
    args: {
        guid: "g1",
        name: "Sales Domain",
        typeName: "m4i_data_domain",
        typeIcon: faProjectDiagram,
        typeIconClass: "business",
    },
    play: async ({ canvas }) => {
        clicked.length = 0;
        await expect(canvas.getByText("Sales Domain")).toBeVisible();
        await expect(canvas.getByText("m4i_data_domain")).toBeVisible();
        await expect(canvas.getByText("Owner")).toBeVisible(); // [card-content] slot
        await expect(canvas.getByText("★★★★☆")).toBeVisible(); // [card-quality] slot

        // The title anchor carries an href, so Enter activates it natively.
        const title = canvas.getByRole("link", { name: "Sales Domain" });
        title.focus();
        await userEvent.keyboard("{Enter}");
        await expect(clicked).toEqual(["g1"]);
    },
    render: host,
};

export const Aliased: Story = {
    args: {
        guid: "g1",
        name: "Sales Domain",
        typeName: "m4i_data_domain",
        typeAlias: "Domain",
        showBaseTypeName: true,
        typeIcon: faProjectDiagram,
        typeIconClass: "business",
    },
    play: async ({ canvas }) => {
        // The badge's text is split across spans (alias, suffix), so the
        // parts are asserted separately.
        await expect(canvas.getByText("Domain", { exact: true })).toBeVisible();
        await expect(canvas.getByText(/\(m4i_data_domain\)/)).toBeVisible();
    },
    render: host,
};

export const Loading: Story = {
    args: {
        guid: "g1",
        name: "Sales Domain",
        loading: true,
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText("Loading Sales Domain...")).toBeVisible();
    },
    render: host,
};
