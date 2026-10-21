// The chrome strings in component templates (DD-047) compile to `$localize`
// calls; the app builds load `@angular/localize/init` as a polyfill, so
// stories need the same global here.
import "@angular/localize/init";

import type { Preview } from "@storybook/angular";

const preview: Preview = {
    tags: ["autodocs"],
};

export default preview;
