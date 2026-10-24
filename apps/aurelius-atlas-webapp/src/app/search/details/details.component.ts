import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { ActivatedRoute, Router } from "@angular/router";
import { map } from "rxjs";

import { Accordion, Breadcrumbs } from "aurelius-atlas-ui";

/**
 * The entity details screen (DET-01, 7.6): the Aurelius `search/details/:id`
 * route as the skeleton the data-free webapp can host today — the legacy
 * default-details anatomy: header (title, type-name line, breadcrumbs
 * trail), description box, property-count level, properties accordion, and
 * the side navigation.
 *
 * Empty state, not fake state (DET-02, DD-096): the Aurelius screen renders
 * one resolved entity, and `GET /v2/entity/guid/{guid}` is server 2.3
 * (planned). The skeleton fetches nothing — the title rides its localized
 * fallback, the trail renders nothing under the breadcrumbs' empty guard,
 * the description is empty, and the accordion holds zero rows. The client
 * method the wiring increment consumes (DET-03, DD-097) exists in
 * `aurelius-atlas-data-access`; calling it is the 2.3+7.6 slice's first line.
 *
 * The `:guid` is the screen's address (DET-07): a signal derived from the
 * route parameters, the URL the whole state. The chrome's strings ride the
 * bridge (DET-04) — keys the Aurelius catalogue carries in both locales;
 * strings bound into inputs live in TypeScript as `$localize` (BRW-02).
 */
@Component({
    imports: [Accordion, Breadcrumbs],
    selector: "aurelius-atlas-webapp-details",
    templateUrl: "./details.component.html",
    styleUrl: "./details.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Details {
    private readonly route = inject(ActivatedRoute);

    private readonly router = inject(Router);

    /** The entity address (DET-01): the route's `guid` parameter. */
    protected readonly guid = toSignal(this.route.paramMap.pipe(map((params) => params.get("guid") ?? "")), {
        initialValue: "",
    });

    /**
     * A crumb was clicked (DET-06): navigate the details route to that
     * guid. The caller-routes contract of the 7.13 trail (DD-154's
     * sibling) — the screen owns the router, the lib component owns the
     * crumbs.
     * @param guid the entity the crumb points at
     */
    protected onCrumbClick(guid: string): void {
        void this.router.navigate(["/search/details", guid]);
    }

    /** The title's fallback while no entity answers (DET-02) — the chrome's type label. */
    protected readonly titleFallback = $localize`:@@search.details.typeSelect.label:Entity type`;
}
