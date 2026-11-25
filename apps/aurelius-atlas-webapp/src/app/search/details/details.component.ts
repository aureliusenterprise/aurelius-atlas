import { ViewportScroller } from "@angular/common";
import { afterRenderEffect, ChangeDetectionStrategy, Component, computed, effect, inject } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { Title } from "@angular/platform-browser";
import { ActivatedRoute, Router, RouterLink } from "@angular/router";
import type { EntityView } from "aurelius-atlas-data-access";
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
    QualityDimensionList,
    SectionStats,
    TypeName,
    type QualityDimensionRow,
    type SectionStat,
} from "aurelius-atlas-ui";

import { alertOnFailure } from "../shared/alert-on-failure";
import { canWriteEntities } from "../shared/can-write-entities";
import { EntityWritten } from "../shared/entity-written";
import { nameDisplay } from "../meta/type-display";
import { typeIcon } from "../meta/type-icons";
import { APP_CONFIG } from "../../tokens";
import { DetailsBreadcrumbState } from "./details-breadcrumb-state";
import { DetailsState } from "./details-state";
import { viewProperties } from "./property-filter";
import { LineageModel } from "./lineage/lineage-model.component";
import { LineageModelState } from "./lineage/lineage-state";
import { CatalogueCard } from "../shared/catalogue-card.component";
import { ComplianceChartBox, type ComplianceChart } from "./compliance-chart.component";
import { PropagatedChips, type PropagatedChipEntry } from "../shared/propagated-chips.component";
import { DetailsGovQualityState, type GovSectionView } from "./sections/gov-quality.state";
import { DetailsRuleVerdictsState } from "./sections/rule-verdicts.state";
import { GovQualityCards } from "./sections/gov-quality-cards.component";
import { DetailsLayoutState } from "./sections/layout.state";
import { loadingLabel, RelatedSectionsState, type SectionView } from "./sections/related-sections.state";
import { DATA_QUALITY_NOT_AVAILABLE, hasGovQualityBox } from "./sections/layouts";
import { hasScoreSource, qualityRows, scorePercent } from "../shared/quality-mapping";
import type { StatDef } from "./sections/section.model";
import { peopleRowsOfSections } from "../shared/people";
import { trailOf } from "../shared/trail";
import { cardTypeAlias } from "../shared/type-alias";

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
        CatalogueCard,
        ClassificationChip,
        ComplianceChartBox,
        DetailsCardSection,
        DetailsNavigation,
        EntityCard,
        FontAwesomeModule,
        GovQualityCards,
        LineageModel,
        Markdown,
        PeopleBox,
        PropertiesItem,
        PropagatedChips,
        QualityDimensionList,
        SectionStats,
        TypeName,
        RouterLink,
    ],
    selector: "aurelius-atlas-webapp-details",
    // LineageModelState is NOT listed here (DD-415): the routed quickview
    // drawer lives in the root `drawer` aux outlet and a page-scoped provider
    // would hide the box's state from it, so the service is the root
    // singleton both this page and the drawer read.
    providers: [
        DetailsState,
        DetailsBreadcrumbState,
        DetailsLayoutState,
        RelatedSectionsState,
        DetailsGovQualityState,
        DetailsRuleVerdictsState,
    ],
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

    /** The trail the screen renders (DET-12, VDR-06): the view's stored breadcrumb. */
    protected readonly crumbs = inject(DetailsBreadcrumbState);

    /** The layout dispatch (DET-15, DD-366): the m4i layout, or the default. */
    protected readonly layoutState = inject(DetailsLayoutState);

    /** The card sections of the entity's layout (DET-17..DET-22). */
    protected readonly sections = inject(RelatedSectionsState);

    /** The Lineage Model fetch state (DD-400): the LDG-32 stat reads it. */
    protected readonly lineage = inject(LineageModelState);

    /** The Governance Quality Rules box of the layout (DET-42 as amended by 7.25a, DD-520/DD-841). */
    protected readonly govQuality = inject(DetailsGovQualityState);

    /** The opened rule's verdict rows (DET-51, DD-850): the chart's score. */
    protected readonly ruleVerdicts = inject(DetailsRuleVerdictsState);

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
        // The stores' held failures reach the drawer through the shared
        // relay (DD-871): DetailsState's failed read and RelatedSectionsState's
        // failed chunk each alert once, from the screen that shows them.
        alertOnFailure(this.state);
        alertOnFailure(this.sections);

        // The fetch follows the URL (DET-08): on arrival and on every guid
        // change (the results screen's URL-effect idiom).
        effect(() => {
            const guid = this.guid();
            if (guid !== "") {
                this.state.load(guid);
            }
        });

        // The document title names the entity once it answers (TITLE-001,
        // WCAG 2.4.2): the title strategy set the route's fallback on
        // arrival, and the data moment replaces it — the strategy owns
        // navigation, this owns the entity (title-strategy.ts).
        const titleService = inject(Title);
        const appName = inject(APP_CONFIG).appName;
        effect(() => {
            if (this.entity()) {
                titleService.setTitle(`${this.title()} - ${appName}`);
            }
        });

        // The editor's write tick (DD-327, DD-803): the drawer overlay left
        // this screen's URL untouched, so the router reuses this component —
        // a saved tick for this guid re-reads the entity the editor just
        // wrote. A deleted tick asks nothing: the delete's own navigation
        // leaves the Atlas browse landing, not this screen. The seq guard
        // keeps a screen that mounts *after* the save (the create flow) from
        // loading twice: the URL effect above already reads it.
        const written = inject(EntityWritten);
        let consumedSeq = written.latest()?.seq ?? 0;

        effect(() => {
            const event = written.latest();
            if (event !== null && event.outcome === "saved" && event.guid === this.guid() && event.seq > consumedSeq) {
                consumedSeq = event.seq;
                this.state.reload(event.guid); // VDR-07: the saved view leaves the cache first (DD-605)
            }
        });

        // The trail follows the view (DET-12, DD-606): the door's stored
        // breadcrumb, top down, with the opened entity's own crumb last —
        // the seam of 7.20 (DD-317), filled since 16.5b. A crumb shows its
        // name, or its type, or its guid (VDR-06: the stored name can be
        // gone, ASU-02), and rides the app's type map for its icon, as the
        // header badge's does (DET-26, DD-378).
        effect(() => {
            const view = this.entity();
            if (view === null) {
                this.crumbs.clear();
                return;
            }
            this.crumbs.setTrail(trailOf(view, (typeName) => typeIcon(typeName)));
        });

        // The layout dispatch follows the entity (DET-15): a direct name
        // answers at once, a supertype walk on the next microtask. The
        // seed follows the layout and the entity (DET-17): every arrival —
        // the save re-read among them — re-seeds every section.
        effect(() => {
            this.layoutState.resolve(this.entity()?.typeName ?? null);
        });
        // The rule page's verdict boxes seed from the verdict rows (DD-848):
        // the read effect below hands the screen its rows, and every arrival
        // re-seeds — the sections store's rule for a new view. The two
        // computeds keep the effect awake across the read (DET-51). The field
        // page's rules box gets the view's own rule score rows the same way
        // (DET-65, DET-66, DD-865): no request, the view already carries them.
        effect(() => {
            this.sections.seed(
                this.entity(),
                this.layoutState.layout(),
                {
                    "related-non-compliants": this.ruleVerdicts.nonCompliantGuids(),
                    "related-compliants": this.ruleVerdicts.compliantGuids(),
                },
                this.entity()?.ruleScores ?? [],
            );
        });
        // The rule box follows the entity (DET-42): every arrival re-reads,
        // the save re-read among them — the sections store's rule. Every
        // m4i layout except the rule page carries the box (DET-48).
        effect(() => {
            this.govQuality.load(hasGovQualityBox(this.layout()) ? this.entity() : null);
        });
        // The verdict read follows the rule (DET-51): the layout carrying a
        // Compliance Chart is the rule page and only the rule page, so its
        // arrival asks the door once per entity, and every other entity
        // asks nothing. The save re-read re-asks — the sections store's rule.
        effect(() => {
            const view = this.entity();
            this.ruleVerdicts.load(this.layout()?.complianceChart === undefined ? null : view);
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
            this.sectionViews();
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

    /** The resolved view, or null in every no-entity state (DET-09, VDR-01). */
    protected readonly entity = computed<EntityView | null>(() => this.state.entity());

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
     * The classification chips' labels (DET-09, DD-379, VDR-05): the view's
     * attached classification names, each by its dictionary display name —
     * the legacy chip's `name | translate`. These are the entity's own, and
     * the only ones the editor can change (DD-326).
     */
    protected readonly classifications = computed(() =>
        (this.entity()?.classificationNames ?? [])
            .filter((name) => typeof name === "string" && name !== "")
            .map((name) => nameDisplay(name)),
    );

    /**
     * The chips of the classifications propagation brought (VDR-05, VDR-12,
     * DV-197): one per propagated name, each by its dictionary display name,
     * with the entities it came from as its chip's sources — the rows the
     * shared part draws (icon, name, path; DD-836). Both doors answer these
     * now (the cards too), and the header shows the entity it opened.
     */
    protected readonly propagatedClassifications = computed<PropagatedChipEntry[]>(() =>
        (this.entity()?.propagatedClassifications ?? [])
            .filter((entry) => typeof entry.typeName === "string" && entry.typeName !== "")
            .map((entry) => ({
                label: nameDisplay(entry.typeName),
                sources: (entry.entities ?? []).filter(
                    (source) => typeof source.guid === "string" && source.guid !== "",
                ),
            })),
    );

    /**
     * The attribute the description box shows (DET-10 as amended by 18.8,
     * DD-320): `description`, only when it is a string, else nothing. The
     * legacy box read `definition` first because the legacy entity types are
     * the m4i governance types, which carried their text there; 18.8 (ADR 070)
     * retired that attribute, so the box reads the one prose attribute this
     * catalogue carries. The key is remembered so the properties table can
     * drop it (DET-11): the text shows once on the screen.
     */
    protected readonly descriptionKey = computed(() => {
        const attributes = this.entity()?.attributes;
        if (typeof attributes?.["description"] === "string") {
            return "description";
        }
        return null;
    });

    /** The description text (DET-10), or empty in every no-entity state. */
    protected readonly description = computed(() => {
        const key = this.descriptionKey();
        return key === null ? "" : (this.entity()?.attributes?.[key] as string);
    });

    /** The properties rows (DET-11, VDR-04): the view's merge, the legacy filter, sorted by key. */
    protected readonly properties = computed(() => {
        const view = this.entity();
        return view ? viewProperties(view, this.descriptionKey()) : [];
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

    /** The People box's rows of the opened entity (DET-23, VDR-03): the view's sections. */
    protected readonly people = computed(() => peopleRowsOfSections(this.entity()?.sections));

    /** The card sections as the store renders them (DET-17..DET-22). */
    protected readonly views = this.sections.views;

    /** The Governance Quality Rules box as the chrome renders it (DET-44..DET-47). */
    protected readonly govView = this.govQuality.view;

    /**
     * The Compliance Chart box of the rule page (DET-54, DD-849): the
     * layout's strings and DET-51's score, or null for every other layout.
     */
    protected readonly complianceChart = computed<ComplianceChart | null>(() => {
        const def = this.layout()?.complianceChart;
        return def === undefined ? null : { ...def, score: this.ruleVerdicts.score() };
    });

    /**
     * The layout's box list in the config's order (DET-48, DD-841): every
     * entry of the layout's `sections` row, the relationship-seeded ones
     * drawn by the sections store and the `gov-quality` entry by the box's
     * own store. The order is the spec's — the legacy's box order, which is
     * the list's order — and the template draws one pass over it.
     */
    protected readonly sectionViews = computed<DetailsSectionView[]>(() => {
        const layout = this.layout();
        if (layout === undefined) {
            return [];
        }
        const byAnchor = new Map(this.views().map((view) => [view.anchor, view]));
        const drawn: DetailsSectionView[] = [];
        for (const def of layout.sections) {
            if (def.kind === "gov-quality") {
                drawn.push(this.govView());
            } else if (def.kind === "score") {
                // The box's title is the layout's own key (DET-56), so the
                // config entry carries it; the rows ride the view (DD-852).
                drawn.push({ ...this.scoreView(), anchor: def.anchor, title: def.title });
            } else {
                const view = byAnchor.get(def.anchor);
                if (view !== undefined) {
                    drawn.push(view);
                }
            }
        }
        return drawn;
    });

    /**
     * The Data Quality score box (DET-56, DET-63, DD-852): the opened
     * view's own score rows (AVS-01, AVS-08) in DET-56's dimension order,
     * or the placeholder rows the UIC-37 list shows — no second read,
     * the box rides DET-08's read exactly like the stats bar's counts.
     */
    protected readonly scoreView = computed<Omit<ScoreSectionView, "anchor" | "title">>(() => {
        const entity = this.entity();
        const scored = hasScoreSource(entity?.quality);
        return {
            kind: "score",
            rows: scored ? qualityRows(entity?.quality) : [],
            placeholder: scored ? "" : DATA_QUALITY_NOT_AVAILABLE,
        };
    });

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
            count: this.statCount(stat),
        })),
    );

    /**
     * The grouped stats-bar boxes of the layout, with live counts
     * (DET-40, DD-518): the person bar's four headed boxes. Empty for
     * every other layout, which keeps the flat DET-24 bar above.
     */
    protected readonly statsGroups = computed(() =>
        (this.layout()?.statsGroups ?? []).map((group) => ({
            heading: group.heading,
            items: group.items.map((stat) => ({
                label: stat.label,
                target: stat.anchor,
                count: this.statCount(stat),
            })),
        })),
    );

    /**
     * The count behind one stat (DET-24): the properties' own count, the
     * lineage's word, or the section's rendered-entry count — picked by
     * the stat's source kind.
     * @param stat the layout's stat definition
     */
    private statCount(stat: StatDef): string | number {
        if (stat.source.kind === "properties") {
            return this.propertyCount();
        }
        if (stat.source.kind === "lineage") {
            return this.lineageWord(stat);
        }
        if (stat.source.kind === "score") {
            return this.scoreWord(stat);
        }
        if (stat.source.kind === "end") {
            return this.sections.endCount(stat.source.key);
        }
        return this.sections.countFor(stat.source.anchor);
    }

    /**
     * The score stat's value (DET-58, DD-853): the opened view's `overall`
     * score as the legacy's percent when its count is above zero, else the
     * layout's own `unavailable` word — the legacy's two-state
     * `noDataQuality` branch, never a zero (DET-63).
     */
    private scoreWord(stat: StatDef): string {
        const overall = this.entity()?.quality?.find((row) => row.dimension === "overall");
        if (overall !== undefined && overall.count > 0 && typeof overall.score === "number" && overall.score >= 0) {
            return scorePercent(overall.score);
        }
        return stat.unavailable ?? "";
    }

    /**
     * The lineage stat's word (LDG-32): "Available" once a model drew,
     * "Unavailable" at rest, blank while the call is pending (the legacy's
     * shape — never a count). The pair is the layout's own keys; a layout
     * without the lineage entry never asks.
     */
    private lineageWord(stat: StatDef): string {
        if (this.lineage.loading()) {
            return "";
        }
        return this.lineage.model() !== null ? (stat.available ?? "") : (stat.unavailable ?? "");
    }

    /** The card section's placeholder — `search.details.components.detailsCardsList.placeholder`. */
    protected readonly searchPlaceholder = $localize`:@@search.details.components.detailsCardsList.placeholder:Search for keywords`;

    /** The count line's word — `search.details.components.detailsCardsList.results`. */
    protected readonly resultWord = $localize`:@@search.details.components.detailsCardsList.results:result(s)`;

    /** The scroll container's label — `search.components.infiniteScrollContainer.loadNextPage`. */
    protected readonly loadLabel = $localize`:@@search.components.infiniteScrollContainer.loadNextPage:Load next page...`;

    /** The funnel button's name — `search.details.components.detailsCardsList.filter` (VCF-08). */
    protected readonly filterLabel = $localize`:@@search.details.components.detailsCardsList.filter:Filter`;

    /** The popover's empty line — `search.components.filter.notAvailable` (VCF-10). */
    protected readonly notAvailableLabel = $localize`:@@search.components.filter.notAvailable:No filters available.`;

    /** The facet menu's show-more label — `search.components.filter.facet.showMore` (UIC-34). */
    protected readonly showMoreLabel = $localize`:@@search.components.filter.facet.showMore:Show more`;

    /** The facet menu's show-less label — `search.components.filter.facet.showLess` (UIC-34). */
    protected readonly showLessLabel = $localize`:@@search.components.filter.facet.showLess:Show less`;

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
     * A propagation source was clicked (VDR-12): the same route the crumbs
     * take, so a tag's origin is one click away.
     * @param guid the entity the classification is attached to
     */
    protected onSourceClick(guid: string): void {
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
     * re-render while a chunk answers mid-type. The Governance Quality
     * Rules box rides its own store (7.25a, DD-841) — the same rule, the
     * box's rows instead of the section's cards.
     * @param view the section
     * @param text the box's text
     */
    protected onSectionText(view: DetailsSectionView, text: string | null): void {
        if (view.kind === "gov-quality") {
            this.govQuality.setText(text);
            return;
        }
        this.sections.setText(view.anchor, text);
    }

    /**
     * A section's keyword submit or clear (DET-20). Since DD-375 the
     * filter rides the typing, so a plain submit is a no-op; the clear
     * lands here.
     * @param view the section
     * @param query the submitted term, or null on clear
     */
    protected onSectionQuery(view: DetailsSectionView, query: string | null): void {
        if (view.kind === "gov-quality") {
            this.govQuality.setQuery(query);
            return;
        }
        this.sections.setQuery(view.anchor, query);
    }

    /** A section's reset link was clicked (DET-20, DET-44).
     * @param view the section */
    protected onSectionReset(view: DetailsSectionView): void {
        if (view.kind === "gov-quality") {
            this.govQuality.reset();
            return;
        }
        this.sections.reset(view.anchor);
    }

    /** A section's popover row was ticked or unticked (VCF-11, DET-46).
     * @param view the section
     * @param event the group's key with the row's value and new state */
    protected onSectionFacetToggled(
        view: DetailsSectionView,
        event: { group: string; value: string; checked: boolean },
    ): void {
        if (view.kind === "gov-quality") {
            this.govQuality.toggleFacet(event.group, event.value, event.checked);
            return;
        }
        this.sections.toggleFacet(view.anchor, event.group, event.value, event.checked);
    }

    /**
     * A section's sort select changed (DET-21, DET-45).
     * @param view the section
     * @param sort the selected key
     */
    protected onSectionSort(view: DetailsSectionView, sort: string | null): void {
        if (view.kind === "gov-quality") {
            this.govQuality.setSort(sort);
            return;
        }
        this.sections.setSort(view.anchor, sort);
    }

    /** A section's direction button toggled (DET-21, DET-45).
     * @param view the section */
    protected onSectionDirection(view: DetailsSectionView): void {
        if (view.kind === "gov-quality") {
            this.govQuality.toggleDirection();
            return;
        }
        this.sections.toggleDirection(view.anchor);
    }

    /** A section's scroll container asked for the next page (DET-22, DET-47).
     * @param view the section */
    protected onSectionPage(view: DetailsSectionView): void {
        if (view.kind === "gov-quality") {
            this.govQuality.nextPage();
            return;
        }
        this.sections.nextPage(view.anchor);
    }
}

/**
 * One box of the layout's section list, as the template draws it (7.25a,
 * DET-48; 7.25c, DD-851): a relationship-seeded card section, the
 * Governance Quality Rules box, or the Data Quality score box. The
 * chrome's fields ride the first two (DET-44), the `kind` picks the store
 * a handler reaches (DD-841), and the score box has no handler at all —
 * no keyword, sort, facet, page, or count line (DET-57).
 */
type DetailsSectionView = SectionView | GovSectionView | ScoreSectionView;

/**
 * The Data Quality score box as the template draws it (DET-56, DD-852):
 * the scored dimension rows — a dimension with no rules prints no row
 * (DET-64) — or an empty list with the placeholder text.
 * The title is the layout's own key — read from the layout's section
 * entry by the template's own title binding.
 */
interface ScoreSectionView {
    kind: "score";
    anchor: string;
    title: string;
    rows: QualityDimensionRow[];
    placeholder: string;
}
