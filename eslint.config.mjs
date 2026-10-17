import nx from "@nx/eslint-plugin";

export default [
    ...nx.configs["flat/base"],
    ...nx.configs["flat/typescript"],
    ...nx.configs["flat/javascript"],
    {
        ignores: [
            "**/dist",
            "**/vite.config.*.timestamp*",
            "**/vitest.config.*.timestamp*",
            // Vendored Apache Atlas dashboards, kept byte-identical to release-2.4.0 (DD-017)
            "apps/aurelius-atlas-dashboard/dashboardv2/**",
            "apps/aurelius-atlas-dashboard/dashboardv3/**",
        ],
    },
    {
        files: ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"],
        rules: {
            "@nx/enforce-module-boundaries": [
                "error",
                {
                    enforceBuildableLibDependency: true,
                    allow: ["^.*/eslint(\\.base)?\\.config\\.[cm]?[jt]s$"],
                    depConstraints: [
                        {
                            sourceTag: "*",
                            onlyDependOnLibsWithTags: ["*"],
                        },
                    ],
                },
            ],
        },
    },
    {
        files: ["**/*.ts", "**/*.tsx", "**/*.cts", "**/*.mts", "**/*.js", "**/*.jsx", "**/*.cjs", "**/*.mjs"],
        // Override or add rules here
        rules: {},
    },
    {
        files: ["**/*.json"],
        // Override or add rules here
        rules: {},
        languageOptions: {
            parser: await import("jsonc-eslint-parser"),
        },
    },
];
