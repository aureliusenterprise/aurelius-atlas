import type { Meta, StoryObj } from "@storybook/angular";
import { DarkMode } from "./dark-mode.component";

/**
 * The app's theme button: each click cycles dark → light → Auto (follow the
 * OS), writing `data-theme` on the document root and remembering the choice.
 * It themes the page it renders on — here, the story canvas itself.
 */
const meta: Meta<DarkMode> = {
    component: DarkMode,
    title: "Dark Mode",
};
export default meta;

type Story = StoryObj<DarkMode>;

/**
 * The button in its initial state (Auto). Click it to cycle the canvas
 * through dark, light, and Auto.
 */
export const Primary: Story = {};
