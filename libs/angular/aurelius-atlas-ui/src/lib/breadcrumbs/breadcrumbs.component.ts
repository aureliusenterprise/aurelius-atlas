import { CommonModule } from "@angular/common";
import { ChangeDetectionStrategy, Component, input, output } from "@angular/core";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faExclamationTriangle, type IconDefinition } from "@fortawesome/free-solid-svg-icons";

/**
 * One crumb of the trail. `icon`/`iconClass` arrive from the caller:
 * the legacy `iconsByType` type-to-icon index is application metadata,
 * the lib only renders what it is given (UIC-15).
 */
export interface Breadcrumb {
    /** The unique id of the entity the crumb points at. */
    guid: string;
    /** The crumb's display name. */
    name: string;
    /** The entity type name, used as the icon's tooltip, as the legacy crumb did. */
    typeName: string;
    /** The crumb's icon. */
    icon?: IconDefinition;
    /** The colour class of the icon: business, technical, technical-process, meta. */
    iconClass?: string;
}

/**
 * The legacy Aurelius breadcrumbs trail (`models4insight-bread-crumbs`),
 * ported without its redux store or document provider: the trail, its
 * warning, and the active entity all arrive as inputs and a crumb click
 * emits `itemClicked` — route wiring belongs to the app (7.6).
 *
 * Crumbs are anchors, so Enter activates them natively; the active crumb
 * is inert by Bulma's own `is-active` styling, as in the legacy trail.
 */
@Component({
    selector: "aurelius-atlas-ui-breadcrumbs",
    imports: [CommonModule, FontAwesomeModule],
    templateUrl: "./breadcrumbs.component.html",
    styleUrl: "./breadcrumbs.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Breadcrumbs {
    /**
     * The trail, oldest first. Empty renders nothing, as the legacy
     * component's length guard did.
     */
    readonly items = input<Breadcrumb[]>([]);

    /**
     * The guid of the entity being viewed: its crumb gets `is-active`.
     */
    readonly activeGuid = input<string | undefined>(undefined);

    /**
     * A warning to show above the trail — the legacy component set one
     * when the trail's parallel arrays did not line up; the caller
     * localises the text.
     */
    readonly warning = input<string | undefined>(undefined);

    /**
     * Accessible name of the trail. The Aurelius nav carried this literal.
     */
    readonly breadcrumbsLabel = input("breadcrumbs");

    /**
     * Emits the guid of a clicked crumb. The app routes; the lib does not (7.6).
     */
    readonly itemClicked = output<string>();

    /**
     * The FontAwesome icon used by the warning chip.
     */
    protected readonly warningIcon = faExclamationTriangle;

    /**
     * Handle a crumb activation — the legacy `directToNewEntity`, turned
     * into an emit (the anchor's `href` is the keyboard path, so the
     * default navigation is cancelled).
     * @param event The click event.
     * @param breadcrumb The crumb activated.
     */
    protected onItemClick(event: Event, breadcrumb: Breadcrumb): void {
        event.preventDefault();
        this.itemClicked.emit(breadcrumb.guid);
    }
}
