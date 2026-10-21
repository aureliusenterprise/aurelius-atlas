import { ChangeDetectionStrategy, Component } from "@angular/core";
import { RouterOutlet } from "@angular/router";

import { ShellFooter } from "./shell/footer.component";
import { ShellHeader } from "./shell/header.component";

/**
 * The application root: the shell chrome around the router outlet (SHC-01).
 *
 * The Aurelius root renders `<models4insight-shell>`, which wraps its
 * `router-outlet` in the header, the loading/pipeline sticky block, and the
 * footer; the sticky block is not ported (DD-056), so the frame here is the
 * header, the outlet, and the footer — SHL-03's "bare outlet" reading of the
 * Aurelius root component lands as this chrome.
 */
@Component({
    imports: [RouterOutlet, ShellFooter, ShellHeader],
    selector: "aurelius-atlas-webapp-root",
    templateUrl: "./app.component.html",
    styleUrl: "./app.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {}
