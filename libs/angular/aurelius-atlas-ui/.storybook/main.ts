import { fileURLToPath } from "node:url";
import { dirname } from "node:path";
import type { StorybookConfig } from "@storybook/angular";

const config: StorybookConfig = {
    stories: ["../**/*.@(mdx|stories.@(js|jsx|ts|tsx))"],
    addons: [getAbsolutePath("@storybook/addon-docs")],
    framework: {
        name: getAbsolutePath("@storybook/angular"),
        options: {
            builder: {
                viteConfigPath: "libs/angular/aurelius-atlas-ui/vite.config.mts",
            },
        },
    },
};

export default config;

// To customize your Vite configuration you can use the viteFinal field.
// Check https://storybook.js.org/docs/react/builders/vite#configuration
// and https://nx.dev/recipes/storybook/custom-builder-configs

// Resolves a package to its absolute directory. Typed as the input literal because
// `framework.name` only accepts the package name, while Storybook expects a path here.
function getAbsolutePath<T extends string>(value: T): T {
    return dirname(fileURLToPath(import.meta.resolve(`${value}/package.json`))) as T;
}
