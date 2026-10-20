import { ChangeDetectionStrategy, Component } from "@angular/core";
import { RouterOutlet } from "@angular/router";

/**
 * The application root: a router outlet and nothing else, as the Aurelius root
 * component is (SHL-03).
 *
 * The Aurelius `Shell` chrome (nav bar, breadcrumbs, app bar) is applied by the
 * feature route configs of `libs/shell`, not by the root, and arrives with the
 * search and browse slices (7.4, 7.5).
 */
@Component({
    imports: [RouterOutlet],
    selector: "aurelius-atlas-webapp-root",
    templateUrl: "./app.component.html",
    styleUrl: "./app.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {}
