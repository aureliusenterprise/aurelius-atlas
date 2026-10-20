import { ChangeDetectionStrategy, Component } from "@angular/core";

/**
 * Placeholder for the Aurelius browse screen — the default destination of the
 * Aurelius router (`'' -> /search/browse`, SHL-04).
 *
 * 7.1 ships only the destination of the default route, so the router, the
 * locale build, and the e2e surface are real before the feature arrives. The
 * Aurelius `BrowseModule` (hero, domain grids, the `Shell` chrome) is ported
 * by 7.5, which replaces this file.
 */
@Component({
    selector: "aurelius-atlas-webapp-browse",
    templateUrl: "./browse.component.html",
    styleUrl: "./browse.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Browse {}
