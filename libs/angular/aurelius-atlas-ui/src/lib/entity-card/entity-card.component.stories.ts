import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent } from "storybook/test";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faProjectDiagram, faTable, faUser } from "@fortawesome/free-solid-svg-icons";

import { Breadcrumb, Breadcrumbs } from "../breadcrumbs/breadcrumbs.component";
import { EntityCard } from "./entity-card.component";

/**
 * The entity card: a clickable title link, a type-name badge, and content
 * and quality slots the caller projects. Clicking the title emits
 * `entityClicked` with the guid — navigating is the caller's job.
 */
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

/**
 * The card with a title, a type badge, a projected content list and a
 * quality column. Pressing Enter on the focused title emits the click.
 */
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

/**
 * The badge shows the type's friendly alias — "Domain" — with the raw type
 * name next to it, `(m4i_data_domain)`.
 */
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

/**
 * While the entity is being fetched, the card body is replaced by a
 * "Loading …" row and a spinner.
 */
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
 * A dataset as it appears in the search results: the title links to the
 * entity, the badge names its type, and the body stacks the trail from the
 * domain down to this entity, a one-line description, and the data owner
 * and steward rows with their person icons.
 *
 * The trail ends with the entity itself — the last crumb repeats the card
 * title, and clicking the title (not the crumb) opens the entity.
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

/**
 * The card on the dark theme: the ink flips to light greys and the
 * technical blue lifts for the dark surface. It opens dark — the toolbar
 * Theme switch (top bar) flips it to light or Auto at any time.
 */
export const OnDark: Story = {
    args: {
        guid: "g2",
        name: "hourly data",
        typeName: "m4i_dataset",
        typeAlias: "Data Entity",
        typeIcon: faTable,
        typeIconClass: "technical",
        showQuality: false,
    },
    parameters: { theme: "dark" },
    play: async ({ canvasElement }) => {
        const color = (selector: string) => {
            const el = canvasElement.querySelector<HTMLElement>(selector);
            if (!el) throw new Error(`${selector} is missing`);
            return getComputedStyle(el).color;
        };
        // The toolbar Theme switch can move this story to either scheme, so
        // the play() asserts the ink of whichever one is active.
        const dark = document.documentElement.dataset["theme"] !== "light";
        if (dark) {
            // Bulma's dark surface, the DD-156 ink: title #ededed, body #b5b5b5.
            await expect(canvasElement.querySelector(".card")).toHaveStyle({
                "background-color": "rgb(20, 22, 26)",
            });
            await expect(color(".title.is-4 a")).toBe("rgb(237, 237, 237)");
            await expect(color("[card-content] p")).toBe("rgb(181, 181, 181)");
            // The legacy pure blue lifts to Bulma's dark-adapted lightness.
            await expect(color(".media-right .icon.technical")).toBe("rgb(128, 128, 255)");
        } else {
            // Light: Bulma's scheme-main card with the legacy ink the brand
            // sheet keeps (title #363636, body #4a4a4a — SHM-01).
            await expect(canvasElement.querySelector(".card")).toHaveStyle({
                "background-color": "rgb(255, 255, 255)",
            });
            await expect(color(".title.is-4 a")).toBe("rgb(54, 54, 54)");
            await expect(color("[card-content] p")).toBe("rgb(74, 74, 74)");
            // Light scheme keeps the legacy pure blue.
            await expect(color(".media-right .icon.technical")).toBe("rgb(0, 0, 255)");
        }
    },
    render: (args) => ({
        moduleMetadata: { imports: [FontAwesomeModule] },
        props: { ...args, onClick: (guid: string) => clicked.push(guid) },
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
        <p class="block">This data entity yields the hourly statistics.</p>
    </div>
</aurelius-atlas-ui-entity-card>
`,
    }),
};
