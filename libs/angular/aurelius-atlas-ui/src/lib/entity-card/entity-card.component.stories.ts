import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent } from "storybook/test";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faProjectDiagram, faTable, faUser } from "@fortawesome/free-solid-svg-icons";

import { Breadcrumb, Breadcrumbs } from "../breadcrumbs/breadcrumbs.component";
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

/**
 * The 7.6 composition: a search-result card whose body is a breadcrumb
 * trail, a description, and the owner/steward row — the anatomy of the
 * legacy `entity-details-card` (each search result renders this card),
 * assembled from the lib's dumb pieces. The icon classes come from the
 * caller's `iconsByType` (app meta).
 */
export const SearchResult: Story = {
    args: {
        guid: "g2",
        name: "hourly data",
        typeName: "m4i_dataset",
        typeAlias: "Data Entity",
        typeIcon: faTable,
        typeIconClass: "business",
        showQuality: false,
    },
    play: async ({ canvas, canvasElement }) => {
        clicked.length = 0;
        await expect(canvas.getByRole("navigation", { name: "breadcrumbs" })).toBeVisible();
        await expect(canvas.getByText("This data entity yields the hourly statistics.")).toBeVisible();
        await expect(canvas.getByText("Jane Martens")).toBeVisible();

        // The title and the trail's last crumb share the name (as in the
        // demo), so pick the card's own anchor out of the two.
        const titleLink = canvasElement.querySelector<HTMLElement>(".title.is-4 a");
        if (!titleLink) throw new Error("the card title link is missing");
        await userEvent.click(titleLink);
        await expect(clicked).toEqual(["g2"]);
    },
    render: (args) => ({
        moduleMetadata: { imports: [Breadcrumbs, FontAwesomeModule] },
        props: {
            ...args,
            faUser,
            trail: [
                {
                    guid: "g1",
                    name: "plant data",
                    typeName: "Data Domain",
                    icon: faProjectDiagram,
                    iconClass: "business",
                },
                { guid: "g2", name: "hourly data", typeName: "Data Entity", icon: faTable, iconClass: "business" },
            ] as Breadcrumb[],
            onClick: (guid: string) => clicked.push(guid),
            onCrumb: (guid: string) => clicked.push(guid),
        },
        template: `
<aurelius-atlas-ui-entity-card
    [guid]="guid"
    [name]="name"
    [typeName]="typeName"
    [typeAlias]="typeAlias"
    [typeIcon]="typeIcon"
    [typeIconClass]="typeIconClass"
    [showQuality]="showQuality"
    (entityClicked)="onClick($event)"
>
    <div card-content>
        <div class="block">
            <aurelius-atlas-ui-breadcrumbs
                [items]="trail"
                [activeGuid]="guid"
                (itemClicked)="onCrumb($event)"
            ></aurelius-atlas-ui-breadcrumbs>
        </div>
        <p class="block">This data entity yields the hourly statistics.</p>
        <div class="block">
            <p><span class="icon has-text-warning"><fa-icon [icon]="faUser"></fa-icon></span> Data Owner(s) : <a>Jane Martens</a></p>
            <p><span class="icon has-text-warning"><fa-icon [icon]="faUser"></fa-icon></span> Data Steward(s) : <a>Iris Jacobs</a></p>
        </div>
    </div>
</aurelius-atlas-ui-entity-card>
`,
    }),
};
