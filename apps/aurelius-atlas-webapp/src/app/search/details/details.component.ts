import { ChangeDetectionStrategy, Component, computed, effect, inject } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { ActivatedRoute, Router } from "@angular/router";
import type { AtlasEntity } from "aurelius-atlas-data-access";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faPen } from "@fortawesome/free-solid-svg-icons";
import { map } from "rxjs";

import {
    Accordion,
    Breadcrumbs,
    ClassificationChip,
    DetailsNavigation,
    Markdown,
    PropertiesItem,
    TypeName,
} from "aurelius-atlas-ui";

import { canWriteEntities } from "../editor/can-write-entities";
import { EntitySaved } from "../editor/entity-saved";
import { DetailsBreadcrumbState } from "./details-breadcrumb-state";
import { DetailsState } from "./details-state";
import { detailProperties } from "./property-filter";

/**
 * The entity details screen (DET-01, 7.6; the data spine 7.20): the Aurelius
 * `search/details/:guid` route with its default-details anatomy — header
 * (title, type-name line, classification chips, breadcrumbs trail),
 * description box, property-count level, properties accordion, and the side
 * navigation — now bound to the entity the server answers.
 *
 * The fetch follows the route's `:guid` (DET-08, DD-318): the URL is the
 * screen's whole address (DET-07) and the store keeps the entity, the
 * loading line, and the failure alert. With no entity (still loading, or a
 * read that failed — a 404 among them, DET-13), every slot keeps the
 * DET-02 empty shape: the title rides its localized fallback, the trail
 * renders under the breadcrumbs' empty guard, the description is empty, and
 * the accordion holds zero rows. No placeholder data in any state.
 *
 * The chrome's strings ride the bridge (DET-04) — keys the Aurelius
 * catalogue carries in both locales; strings bound into inputs live in
 * TypeScript as `$localize` (BRW-02). The parts stay dumb (DET-05): the
 * trail, the chips, and the rows arrive as inputs to the 7.13/7.16
 * components, and only this screen touches the router (DET-06).
 */
@Component({
    imports: [
        Accordion,
        Breadcrumbs,
        ClassificationChip,
        DetailsNavigation,
        FontAwesomeModule,
        Markdown,
        PropertiesItem,
        TypeName,
    ],
    selector: "aurelius-atlas-webapp-details",
    providers: [DetailsState, DetailsBreadcrumbState],
    templateUrl: "./details.component.html",
    styleUrl: "./details.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Details {
    private readonly route = inject(ActivatedRoute);

    private readonly router = inject(Router);

    /** The read store (DET-08): the entity, and whether a load is in flight. */
    protected readonly state = inject(DetailsState);

    /** The trail's app-side seam (DET-12, DD-317): empty until an API fills it. */
    protected readonly crumbs = inject(DetailsBreadcrumbState);

    /** Whether the pencil shows (EDT-09, DD-324): the atlas-write grant. */
    protected readonly canWrite = canWriteEntities();

    /** The pencil's icon. */
    protected readonly faPen = faPen;

    /** The pencil's accessible name — the drawer's edit title (EDT-11). */
    protected readonly editTitle = $localize`:@@search.editEntity.editEntity:Edit entity`;

    /** The entity address (DET-01): the route's `guid` parameter. */
    protected readonly guid = toSignal(this.route.paramMap.pipe(map((params) => params.get("guid") ?? "")), {
        initialValue: "",
    });

    constructor() {
        // The fetch follows the URL (DET-08): on arrival and on every guid
        // change (the results screen's URL-effect idiom).
        effect(() => {
            const guid = this.guid();
            if (guid !== "") {
                this.state.load(guid);
            }
        });

        // The editor's save tick (DD-327): the drawer overlay left this
        // screen's URL untouched, so the router reuses this component — the
        // tick for this guid re-reads the entity the editor just wrote. The
        // seq guard keeps a screen that mounts *after* the save (the create
        // flow) from loading twice: the URL effect above already reads it.
        const saved = inject(EntitySaved);
        let consumedSeq = saved.latest()?.seq ?? 0;

        effect(() => {
            const event = saved.latest();
            if (event !== null && event.guid === this.guid() && event.seq > consumedSeq) {
                consumedSeq = event.seq;
                this.state.load(event.guid);
            }
        });
    }

    /** The resolved entity, or null in every no-entity state (DET-09). */
    protected readonly entity = computed<AtlasEntity | null>(() => this.state.entity());

    /** The title (DET-09): the name attribute, else qualifiedName, else the fallback. */
    protected readonly title = computed(() => {
        const attributes = this.entity()?.attributes ?? {};
        const name = attributes["name"];
        if (typeof name === "string" && name !== "") {
            return name;
        }
        const qualifiedName = attributes["qualifiedName"];
        if (typeof qualifiedName === "string" && qualifiedName !== "") {
            return qualifiedName;
        }
        return this.titleFallback;
    });

    /** The entity's type name for the type-name line, or nothing (DET-09). */
    protected readonly typeName = computed(() => this.entity()?.typeName ?? undefined);

    /** The classification chips' labels (DET-09): the entity's classifications. */
    protected readonly classifications = computed(() =>
        (this.entity()?.classifications ?? [])
            .filter((classification) => typeof classification?.typeName === "string" && classification.typeName !== "")
            .map((classification) => classification.typeName as string),
    );

    /**
     * The attribute the description box shows (DET-10, DD-320):
     * `definition`, else `description`, each only when it is a string, else
     * nothing. The legacy box read `definition` because the legacy entity
     * types are the m4i governance types, which carry their text there;
     * this server ships the Apache Atlas model types, whose description
     * attribute is `description`. The key is remembered so the properties
     * table can drop it (DET-11): the text shows once on the screen.
     */
    protected readonly descriptionKey = computed(() => {
        const attributes = this.entity()?.attributes;
        if (!attributes) {
            return null;
        }
        for (const key of ["definition", "description"]) {
            if (typeof attributes[key] === "string") {
                return key;
            }
        }
        return null;
    });

    /** The description text (DET-10), or empty in every no-entity state. */
    protected readonly description = computed(() => {
        const key = this.descriptionKey();
        return key === null ? "" : (this.entity()?.attributes?.[key] as string);
    });

    /** The properties rows (DET-11): the legacy filtered merge, sorted by key. */
    protected readonly properties = computed(() => {
        const entity = this.entity();
        return entity ? detailProperties(entity, this.descriptionKey()) : [];
    });

    /** The count above the accordion (DET-11): the rendered row count. */
    protected readonly propertyCount = computed(() => this.properties().length);

    /** The trail the 7.13 breadcrumbs render (DET-12): empty until the API join. */
    protected readonly trail = this.crumbs.trail.asReadonly();

    /** The title's fallback while no entity answers (DET-02) — the chrome's type label. */
    protected readonly titleFallback = $localize`:@@search.details.typeSelect.label:Entity type`;

    /** The side navigation's menu label (DET-04) — the legacy 'Details'. */
    protected readonly navLabel = $localize`:@@search.details.components.navigation.details:Details`;

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

    /**
     * A property link was clicked (DET-11): the same route the crumbs take
     * — a relationship link is an entity address like any other.
     * @param guid the linked entity
     */
    protected onLinkClick(guid: string): void {
        void this.router.navigate(["/search/details", guid]);
    }

    /**
     * The pencil was clicked (EDT-01, DD-322): open the editor drawer over
     * this screen — the `drawer` aux outlet carries `edit-entity/:guid`.
     */
    protected edit(): void {
        void this.router.navigate([{ outlets: { drawer: ["edit-entity", this.guid()] } }]);
    }
}
