import { ViewportScroller } from "@angular/common";
import { afterRenderEffect, ChangeDetectionStrategy, Component, computed, effect, inject } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { ActivatedRoute, Router, RouterLink } from "@angular/router";
import type { AtlasEntity } from "aurelius-atlas-data-access";
import { FontAwesomeModule } from "@fortawesome/angular-fontawesome";
import { faPenToSquare } from "@fortawesome/free-solid-svg-icons";
import { map } from "rxjs";

import {
    Accordion,
    Breadcrumbs,
    ClassificationChip,
    DetailsCardSection,
    DetailsNavigation,
    EntityCard,
    Markdown,
    PeopleBox,
    PropertiesItem,
    SectionStats,
    TypeName,
    type SectionStat,
} from "aurelius-atlas-ui";

import { canWriteEntities } from "../editor/can-write-entities";
import { EntitySaved } from "../editor/entity-saved";
import { nameDisplay } from "../meta/type-display";
import { typeIcon } from "../meta/type-icons";
import { DetailsBreadcrumbState } from "./details-breadcrumb-state";
import { DetailsState } from "./details-state";
import { detailProperties } from "./property-filter";
import { CardContent } from "./sections/card-content.component";
import { DetailsLayoutState } from "./sections/layout.state";
import { loadingLabel, RelatedSectionsState, type SectionView } from "./sections/related-sections.state";
import { cardTypeAlias } from "./shared/card";
import { peopleRows } from "./shared/people";

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
        CardContent,
        ClassificationChip,
        DetailsCardSection,
        DetailsNavigation,
        EntityCard,
        FontAwesomeModule,
        Markdown,
        PeopleBox,
        PropertiesItem,
        SectionStats,
        TypeName,
        RouterLink,
    ],
    selector: "aurelius-atlas-webapp-details",
    providers: [DetailsState, DetailsBreadcrumbState, DetailsLayoutState, RelatedSectionsState],
    templateUrl: "./details.component.html",
    styleUrl: "./details.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Details {
    private readonly route = inject(ActivatedRoute);

    private readonly router = inject(Router);

    /** The router's own scroll seam (DD-381): the anchor jump with the navbar offset. */
    private readonly viewportScroller = inject(ViewportScroller);

    /** The read store (DET-08): the entity, and whether a load is in flight. */
    protected readonly state = inject(DetailsState);

    /** The trail's app-side seam (DET-12, DD-317): empty until an API fills it. */
    protected readonly crumbs = inject(DetailsBreadcrumbState);

    /** The layout dispatch (DET-15, DD-366): the m4i layout, or the default. */
    protected readonly layoutState = inject(DetailsLayoutState);

    /** The card sections of the entity's layout (DET-17..DET-22). */
    protected readonly sections = inject(RelatedSectionsState);

    /** Whether the pencil shows (EDT-09, DD-324): the atlas-write grant. */
    protected readonly canWrite = canWriteEntities();

    /** The pencil's icon — the demo header's `fa-edit`/pen-to-square (DD-346). */
    protected readonly faPenToSquare = faPenToSquare;

    /** The pencil's accessible name — the drawer's edit title (EDT-11). */
    protected readonly editTitle = $localize`:@@search.editEntity.editEntity:Edit entity`;

    /** The entity address (DET-01): the route's `guid` parameter. */
    protected readonly guid = toSignal(this.route.paramMap.pipe(map((params) => params.get("guid") ?? "")), {
        initialValue: "",
    });

    /** The address's anchor (DET-25, DD-381): the section the URL names. */
    protected readonly fragment = toSignal(this.route.fragment, { initialValue: null });

    /** The address this screen has landed its anchor on once (DD-381). */
    private landedKey = "";

    /** The anchor whose box this screen is still waiting for (DD-381). */
    private waitedKey = "";

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

        // The layout dispatch follows the entity (DET-15): a direct name
        // answers at once, a supertype walk on the next microtask. The
        // seed follows the layout and the entity (DET-17): every arrival —
        // the save re-read among them — re-seeds every section.
        effect(() => {
            this.layoutState.resolve(this.entity()?.typeName ?? null);
        });
        effect(() => {
            this.sections.seed(this.entity(), this.layoutState.layout());
        });

        // A deep link's anchor lands when its box arrives (DET-25, DD-381).
        // The router's own anchor jump runs at NavigationEnd, and on a cold
        // arrival at a card section the entity has not answered yet, so the
        // box is not on the page and the router's jump finds nothing. This
        // effect watches for that case: a fragment whose box was missing on
        // arrival lands once the render brings it. A fragment that arrives
        // while its box already stands (a click, a back or forward step)
        // belongs to the router — its anchor scroll or its position
        // restore — and the effect only records it. The content reads keep
        // the effect awake across the renders that fill the boxes.
        afterRenderEffect(() => {
            const anchor = this.fragment();
            this.entity();
            this.views();
            if (anchor === null || anchor === "") {
                return;
            }
            const key = `${this.guid()}#${anchor}`;
            if (key === this.landedKey) {
                return;
            }
            if (document.getElementById(anchor) === null) {
                // The box has not arrived: the jump waits for it.
                this.waitedKey = key;
                return;
            }
            this.landedKey = key;
            if (this.waitedKey !== key) {
                return;
            }
            // The router's own jump path: the offset below the fixed
            // navbar is the one its scroller reads (DD-381).
            this.viewportScroller.scrollToAnchor(anchor);
        });
    }

    /** The resolved entity, or null in every no-entity state (DET-09). */
    protected readonly entity = computed<AtlasEntity | null>(() => this.state.entity());

    /**
     * The m4i layout of the entity's type, or undefined for the DET-01
     * default (DET-15) — the switch below the header.
     */
    protected readonly layout = computed(() => this.layoutState.layout());

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

    /**
     * The header badge's type name (DET-26, DD-379): the dictionary display
     * name of the entity's type — the legacy badge's `typeName | translate`.
     * A name the dictionary never saw stays raw, as the legacy's missing key did.
     */
    protected readonly typeDisplay = computed(() => nameDisplay(this.typeName()));

    /**
     * The header badge's icon (DET-26, DD-378): the app's type-to-icon map
     * resolved for the entity's type — the legacy read the same index, and
     * an unmapped type (a `DataSet`) renders no icon, as the legacy's
     * `*ngIf` did.
     */
    protected readonly typeIconDef = computed(() => typeIcon(this.typeName()));

    /**
     * Resolve a card's badge icon (DET-19, DD-378): the same map lookup,
     * per card entity. The ui card takes icon and class as inputs (UIC-15).
     * @param typeName the card entity's type name, or nothing
     */
    protected iconFor(typeName: string | null | undefined) {
        return typeIcon(typeName ?? undefined);
    }

    /**
     * Resolve a card badge's type name (DET-19, DET-26, DD-379): the
     * dictionary display name, per card entity — the same resolver the
     * header badge rides. The ui card takes display strings as inputs (UIC-15).
     * @param typeName the card entity's type name, or nothing
     */
    protected nameFor(typeName: string | null | undefined) {
        return nameDisplay(typeName ?? undefined);
    }

    /**
     * The classification chips' labels (DET-09, DD-379): the entity's
     * classifications, each by its dictionary display name — the legacy
     * chip's `name | translate`.
     */
    protected readonly classifications = computed(() =>
        (this.entity()?.classifications ?? [])
            .filter((classification) => typeof classification?.typeName === "string" && classification.typeName !== "")
            .map((classification) => nameDisplay(classification.typeName as string)),
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

    /**
     * The badge's alias (DET-26, DD-371): `attributes.typeAlias` as a
     * non-empty string, for the header badge — the cards carry their own
     * alias from the store's card view.
     */
    protected readonly typeAlias = computed(() => {
        const entity = this.entity();
        return entity === null ? undefined : cardTypeAlias(entity);
    });

    /** The People box's rows of the opened entity (DET-23). */
    protected readonly people = computed(() => {
        const entity = this.entity();
        return entity === null ? [] : peopleRows(entity);
    });

    /** The card sections as the store renders them (DET-17..DET-22). */
    protected readonly views = this.sections.views;

    /** The description box's title: the layout's own key, or the default's. */
    protected readonly descriptionTitle = computed(
        () => this.layout()?.descriptionTitle ?? $localize`:@@search.details.default.description:Description`,
    );

    /** The properties accordion's title: the layout's own key, or the default's. */
    protected readonly propertiesTitle = computed(
        () => this.layout()?.propertiesTitle ?? $localize`:@@search.details.default.properties:Properties`,
    );

    /** The stats bar of the layout, with live counts (DET-24). */
    protected readonly stats = computed<SectionStat[]>(() =>
        (this.layout()?.stats ?? []).map((stat) => ({
            label: stat.label,
            target: stat.anchor,
            count:
                stat.source.kind === "properties" ? this.propertyCount() : this.sections.countFor(stat.source.anchor),
        })),
    );

    /** The card section's placeholder — `search.details.components.detailsCardsList.placeholder`. */
    protected readonly searchPlaceholder = $localize`:@@search.details.components.detailsCardsList.placeholder:Search for keywords`;

    /** The count line's word — `search.details.components.detailsCardsList.results`. */
    protected readonly resultWord = $localize`:@@search.details.components.detailsCardsList.results:result(s)`;

    /** The scroll container's label — `search.components.infiniteScrollContainer.loadNextPage`. */
    protected readonly loadLabel = $localize`:@@search.components.infiniteScrollContainer.loadNextPage:Load next page...`;

    /** The People box's placeholder — `search.components.people.empty`. */
    protected readonly peopleEmpty = $localize`:@@search.components.people.empty:No people assigned.`;

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
     * this screen — the `drawer` aux outlet carries `edit/:guid`.
     */
    protected edit(): void {
        void this.router.navigate([{ outlets: { drawer: ["edit", this.guid()] } }]);
    }

    /**
     * A card's title or a person link was activated (DET-19, DET-23): the
     * same details route the crumbs and property links take.
     * @param guid the entity to open
     */
    protected onCardClick(guid: string): void {
        void this.router.navigate(["/search/details", guid]);
    }

    /**
     * A stats-bar heading was clicked (DET-24): route to the box's
     * fragment (DET-25, DD-381). The 7.16 part cancels the bare `#href`
     * jump on its emit (DD-154's pattern) — uncancelled, it resolves
     * against the document's `<base href="/">` and leaves the screen
     * (DD-380). The router's own anchor scrolling then smooth-scrolls the
     * box below the navbar, and the address names the section: the same
     * URL the side navigation's `routerLink` items carry.
     * @param target the box's anchor id
     */
    protected onStatClick(target: string): void {
        void this.router.navigate([], { relativeTo: this.route, fragment: target });
    }

    /**
     * The loading card's row text (DET-18): `search.details.loading`
     * ("Loading {{name}}...") at the card's display text. The card gets no
     * name input, so it renders the label as given — the interpolation
     * happened here, at the display text the seed carries.
     * @param displayText the card's seed display text
     * @returns the localized loading text
     */
    protected loadingText(displayText: string): string {
        return loadingLabel(displayText);
    }

    /**
     * The search box's text as typed (the card section's `queryChange`
     * model): the store filters on it (DD-375) and the echo survives a
     * re-render while a chunk answers mid-type.
     * @param view the section
     * @param text the box's text
     */
    protected onSectionText(view: SectionView, text: string | null): void {
        this.sections.setText(view.anchor, text);
    }

    /**
     * A section's keyword submit or clear (DET-20). Since DD-375 the
     * filter rides the typing, so a plain submit is a no-op; the clear
     * lands here.
     * @param view the section
     * @param query the submitted term, or null on clear
     */
    protected onSectionQuery(view: SectionView, query: string | null): void {
        this.sections.setQuery(view.anchor, query);
    }

    /** A section's reset link was clicked (DET-20).
     * @param view the section */
    protected onSectionReset(view: SectionView): void {
        this.sections.reset(view.anchor);
    }

    /**
     * A section's sort select changed (DET-21).
     * @param view the section
     * @param sort the selected key
     */
    protected onSectionSort(view: SectionView, sort: string | null): void {
        this.sections.setSort(view.anchor, sort);
    }

    /** A section's direction button toggled (DET-21).
     * @param view the section */
    protected onSectionDirection(view: SectionView): void {
        this.sections.toggleDirection(view.anchor);
    }

    /** A section's scroll container asked for the next page (DET-22).
     * @param view the section */
    protected onSectionPage(view: SectionView): void {
        this.sections.nextPage(view.anchor);
    }
}
