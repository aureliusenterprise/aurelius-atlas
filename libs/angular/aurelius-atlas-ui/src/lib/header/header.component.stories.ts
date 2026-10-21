import type { Meta, StoryObj } from "@storybook/angular";
import { expect } from "storybook/test";
import { Header } from "./header.component";

/**
 * The app navbar: a logo brand linking home, projected navigation links on
 * the left, actions on the right, and a burger that opens the menu on
 * narrow screens.
 */
const meta: Meta<Header> = {
    component: Header,
    title: "Header",
};
export default meta;

type Story = StoryObj<Header>;

const template = `
<aurelius-atlas-ui-header [expanded]="expanded" [logo]="logo" [name]="name">
    <ng-container navbar-start>
        <a class="navbar-item" routerLink="/">Home</a>
        <a class="navbar-item" routerLink="/about">About</a>
    </ng-container>
    <ng-container navbar-end>
        <div class="navbar-item">
            <div class="buttons">
                <a class="button is-primary">Log in</a>
            </div>
        </div>
    </ng-container>
</aurelius-atlas-ui-header>
`;

/**
 * Desktop: brand, links and the Log in button all in the bar, the burger
 * hidden.
 */
export const Primary: Story = {
    args: {
        expanded: false,
        logo: "assets/favicon.ico",
        name: "Aurelius UI",
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText(/Home/gi)).toBeTruthy();
        await expect(canvas.getByText(/About/gi)).toBeTruthy();
        await expect(canvas.getByText(/Log in/gi)).toBeTruthy();
    },
    render: (args) => ({
        props: args,
        template,
    }),
};

/** The burger menu opened: the links and actions drop below the bar. */
export const Expanded: Story = {
    args: {
        expanded: true,
        logo: "assets/favicon.ico",
        name: "Aurelius UI",
    },
    play: async ({ canvas }) => {
        await expect(canvas.getByText(/Home/gi)).toBeTruthy();
        await expect(canvas.getByText(/About/gi)).toBeTruthy();
        await expect(canvas.getByText(/Log in/gi)).toBeTruthy();
    },
    render: (args) => ({
        props: args,
        template,
    }),
};

/** Nothing projected: the bar with only the brand. */
export const Empty: Story = {
    args: {
        expanded: false,
        logo: "assets/favicon.ico",
        name: "Aurelius UI",
    },
};
