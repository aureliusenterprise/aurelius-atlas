// The chrome strings in component templates (DD-047) compile to `$localize`
// calls; the app builds load `@angular/localize/init` as a polyfill, so
// stories need the same global here.
import "@angular/localize/init";

import type { Decorator, Preview } from "@storybook/angular";

/**
 * The toolbar theme switch. Bulma 1's scheme machinery reacts to `data-theme`
 * on `<html>` — the same attribute the app's `DarkModeService` toggles — and
 * `:root:not([data-theme])` follows the OS, so "auto" is "no attribute".
 *
 * A story can default the canvas to a scheme with `parameters.theme`; the
 * toolbar always wins over the default, so every story — including the dark
 * ones — stays switchable (a story-level `globals` would lock the toolbar).
 */
const withTheme: Decorator = (storyFn, { globals, parameters }) => {
    const selected = globals["theme"];
    const theme = selected === "auto" ? parameters["theme"] : selected;
    const { dataset } = document.documentElement;
    if (theme === "dark" || theme === "light") {
        dataset["theme"] = theme;
    } else {
        delete dataset["theme"];
    }
    return storyFn();
};

const preview: Preview = {
    tags: ["autodocs"],
    decorators: [withTheme],
    globalTypes: {
        theme: {
            description: "Preview the components in the light or dark theme",
            defaultValue: "auto",
            toolbar: {
                title: "Theme",
                icon: "paintbrush",
                items: [
                    { value: "auto", title: "Auto (OS)", icon: "contrast" },
                    { value: "light", title: "Light", icon: "sun" },
                    { value: "dark", title: "Dark", icon: "moon" },
                ],
                dynamicTitle: true,
            },
        },
    },
    initialGlobals: { theme: "auto" },
    parameters: {
        // Canvas colours that match the Bulma schemes the switch drives
        // (scheme-main is white / hsl(0,0%,9%) under [data-theme]).
        backgrounds: {
            options: {
                light: { name: "Light", value: "#ffffff" },
                dark: { name: "Dark", value: "#171717" },
            },
        },
    },
};

export default preview;
