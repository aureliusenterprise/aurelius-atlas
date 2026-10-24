// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from "eslint-plugin-storybook";

import nx from "@nx/eslint-plugin";
import baseConfig from "../../../eslint.config.mjs";

export default [
    ...baseConfig,
    ...nx.configs["flat/angular"],
    ...nx.configs["flat/angular-template"],
    {
        files: ["**/*.ts"],
        rules: {
            "@angular-eslint/directive-selector": [
                "error",
                {
                    type: "attribute",
                    prefix: "aurelius-atlas-ui",
                    style: "kebab-case",
                },
            ],
            "@angular-eslint/component-selector": [
                "error",
                {
                    type: "element",
                    prefix: "aurelius-atlas-ui",
                    style: "kebab-case",
                },
            ],
        },
    },
    {
        files: ["**/*.html"],
        // Override or add rules here
        rules: {},
    },
    {
        files: ["**/*.ts"],
        rules: {
            // Underscore-prefixed params are intentional (e.g. the static
            // ngTemplateContextGuard signature, which types a template's
            // context without using its arguments).
            "@typescript-eslint/no-unused-vars": [
                "error",
                { argsIgnorePattern: "^_", varsIgnorePattern: "^_", caughtErrorsIgnorePattern: "^_" },
            ],
        },
    },
    ...storybook.configs["flat/recommended"],
];
