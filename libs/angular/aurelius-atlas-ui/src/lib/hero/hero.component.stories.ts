import type { Meta, StoryObj } from "@storybook/angular";
import { Hero } from "./hero.component";

/**
 * A page banner: title and subtitle, with slots before and after the
 * title (a button, a search box) and a tab row beneath.
 */
const meta: Meta<Hero> = {
    component: Hero,
    title: "Hero",
};
export default meta;

type Story = StoryObj<Hero>;

const primaryTemplate = `
<aurelius-atlas-ui-hero title="Atlas" subtitle="Search the catalogue">
    <ng-container before-title>
        <a class="button is-info">Open Editor</a>
    </ng-container>
    <ng-container after-title>
        <input class="input" placeholder="Search..." />
    </ng-container>
    <ng-container navigation>
        <li class="is-active"><a>Technical context</a></li>
        <li><a>Business context</a></li>
        <li><a>Governance</a></li>
    </ng-container>
</aurelius-atlas-ui-hero>
`;

/**
 * The full banner: an "Open Editor" button before the title, a search box
 * after it, and three tabs below, the first active.
 */
export const Primary: Story = {
    render: (args) => ({
        props: args,
        template: primaryTemplate,
    }),
};

/** Title and subtitle only: no slots, no tabs. */
export const TitleOnly: Story = {
    args: {
        title: "Atlas",
    },
};
