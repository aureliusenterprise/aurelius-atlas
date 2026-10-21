import type { Meta, StoryObj } from "@storybook/angular";
import { Hero } from "./hero.component";

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

export const Primary: Story = {
    render: (args) => ({
        props: args,
        template: primaryTemplate,
    }),
};

export const TitleOnly: Story = {
    args: {
        title: "Atlas",
    },
};
