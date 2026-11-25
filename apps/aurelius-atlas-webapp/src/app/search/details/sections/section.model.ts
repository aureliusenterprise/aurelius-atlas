/**
 * The shapes a details layout speaks (DET-16, DD-366): one {@link SectionDef}
 * per card box, one {@link TypeLayout} per m4i type, the stats-bar types, the
 * side-navigation entry, and the facet group keys the filter popover counts.
 * Pure types — the table of rows lives in `layouts.ts`, and the score mapping
 * that reads the AVS-01 rows lives in `../../shared/quality-mapping.ts`
 * (7.43, DD-869). The table, the stores drawing it, and their specs all
 * import the shapes from here, so no one depends on the data to name them.
 */

/**
 * One facet group of a section's filter popover (VCF-09, VCF-10, DD-619).
 * A chain or role key is the relation attribute the rows count — the
 * card's stored derived relations of that type or role (AVS-02, LAS-05;
 * the three role keys count the door's role relations, VCF-18/AVS-10);
 * the two own-field keys count the card's type name (the dictionary name,
 * DET-26) and its display text. The flat `m4i_person` group of 16.5e went
 * with the roles (DD-629): the legacy engine facet counted the one derived
 * people field, as it never stored the roles (DV-170).
 */
export type FacetGroupKey =
    | "m4i_data_domain"
    | "m4i_data_entity"
    | "domainLead"
    | "businessOwner"
    | "steward"
    | "m4i_collection"
    | "m4i_dataset"
    | "m4i_system"
    | "typeName"
    | "name"
    // The governance box's two groups (DET-46, 7.25a): the rule's dimension
    // and its rule type, the legacy box's own facet ask.
    | "dataqualityruledimension"
    | "dataqualitytype";

/** One card section of a layout (DET-17..DET-22 render it). */

export interface SectionDef {
    /** The box's anchor id without the `#` — the legacy section id. */
    readonly anchor: string;
    /** The box title (the `detailsCards.title` key's text). */
    readonly title: string;
    /** The `relationshipAttributes` keys whose entries seed the section. */
    readonly seedKeys: readonly string[];
    /**
     * The popover's facet groups, in legacy order (VCF-10, DD-619's
     * table): each legacy `*-cards` component asked its own `facets` over
     * the engine, and these keys carry that ask. An empty list renders
     * the popover's "No filters available." line (VCF-10).
     */
    readonly facets: readonly FacetGroupKey[];
    /**
     * Which store draws the section (7.25a, DD-841; 7.25c, DD-851). Absent
     * means the relationship-seeded card section of DET-17..DET-22;
     * `"gov-quality"` is the Governance Quality Rules box, which draws
     * the same chrome over its own rows (its store seeds from a rule
     * search and a verdict call, not an end); `"score"` is the Data
     * Quality score box — no store at all: its rows are the opened view's
     * own score rows and the screen draws the box with no keyword, sort,
     * facet, page, or count line (DET-56, DET-57).
     */
    readonly kind?: "gov-quality" | "score";
    /**
     * Which seed fills the section (7.25b, DD-848). Absent means the
     * view's relationship ends (DET-17); `"verdicts"` is a rule page's
     * verdict box, seeded from the opened rule's stored verdicts of one
     * verdict value — the screen hands the GUIDs to the sections store's
     * seed, and the box is the shared chrome in every other way (DET-53).
     */
    readonly seedFrom?: "verdicts";
    /**
     * Which sort options the box offers (DET-21, DET-59, DD-854). Absent
     * means `"name"` — DET-21's Relevance/Name pair; `"score"` is the
     * legacy score pages' ask: the pair plus the five dimension sorts over
     * the cards' own score rows (the ten boxes DET-59 names); `"rules"` is
     * the field page's Data Quality Rules box: the pair plus Dimension and
     * Quality Score over the score rows the opened view carries (DET-66,
     * AVS-13, DD-863).
     */
    readonly sorts?: "name" | "score" | "rules";
}

/**
 * Which count a stat shows: a section's seed count, the properties rows,
 * the Lineage Model fetch state (LDG-32: "Available"/"Unavailable",
 * blank while the call is pending — the legacy's shape, never a count),
 * or one `relationshipAttributes` end's entry count (DET-40, DD-519: the
 * person bar counts its five responsibility ends on their own, while the
 * one merged section dedupes across them). Since 7.25c it can also be the
 * score stat (DET-58, DD-853): the opened view's `overall` score row as a
 * percent, or the layout's `unavailable` word — a value like the lineage's,
 * never a count.
 */
export type StatSource =
    | { kind: "section"; anchor: string }
    | { kind: "properties" }
    | { kind: "lineage" }
    | { kind: "end"; key: string }
    | { kind: "score" };

/** One heading of the stats bar, flat or grouped (DET-24, DET-40). */

export interface StatDef {
    /** The heading's label (the layout's stat key's text). */
    readonly label: string;
    /** The anchor the heading links to, without the `#`. */
    readonly anchor: string;
    /** Which count the heading shows. */
    readonly source: StatSource;
    /**
     * The value word when the lineage model has drawn (LDG-32, the
     * `...available` key) — only the `lineage` kind carries the pair.
     */
    readonly available?: string;
    /** The value word when it rests empty (the `...unavailable` key). */
    readonly unavailable?: string;
}

/**
 * One grouped stats-bar box (DET-40, DD-518): the legacy person page's
 * four headed groups — Domain Lead, Data Owner, Data Steward, Other —
 * each holding one or two heading-links. A layout with `statsGroups`
 * renders these instead of the flat `stats` list.
 */
export interface StatGroupDef {
    /** The group's heading (the legacy box heading's key's text). */
    readonly heading: string;
    /** The group's stats, in legacy order. */
    readonly items: readonly StatDef[];
}

/** One side-navigation entry (DET-25 renders the layout's set). */

export interface NavDef {
    /** The entry's label. */
    readonly label: string;
    /** The anchor, without the `#`. */
    readonly anchor: string;
}

/** One type's layout: everything below the header that differs per type. */

export interface TypeLayout {
    /** The description box's title (the layout's own `description` key). */
    readonly descriptionTitle: string;
    /**
     * Whether the layout renders the description box (DET-39, DD-518).
     * Absent means true — the nine rows of 7.21a/7.21c/7.27 all carry the
     * box; only the person page omits it, as the legacy's did.
     */
    readonly descriptionBox?: boolean;
    /** Whether the layout renders the People box (DET-23). */
    readonly peopleBox: boolean;
    /** The People box's title, when it has one. */
    readonly peopleTitle: string;
    /** The card sections, in legacy order. */
    readonly sections: readonly SectionDef[];
    /** The stats-bar entries, in legacy order. */
    readonly stats: readonly StatDef[];
    /**
     * The grouped stats-bar boxes (DET-40, DD-518), in legacy order, when
     * the layout groups its bar: the person row's four headed boxes. A
     * layout with these renders them instead of the flat `stats` list, so
     * every other row keeps the DET-24 bar unchanged.
     */
    readonly statsGroups?: readonly StatGroupDef[];
    /** The properties accordion's title (the layout's own `properties` key). */
    readonly propertiesTitle: string;
    /** The side-navigation entries, in legacy order. */
    readonly nav: readonly NavDef[];
    /**
     * The anchor of the card box the Lineage Model box follows (LDG-09,
     * DD-388), when the layout carries one: the dataset's and the process'
     * rows name it, every other layout leaves the box out entirely.
     */
    readonly lineageAfter?: string;
    /**
     * The Compliance Chart box (DET-54, DD-849), when the layout carries
     * one: the rule page's score pie between the stats bar and its first
     * card box, with the two-row legend beside it — the legacy's labels.
     */
    readonly complianceChart?: ComplianceChartDef;
}

/** The Compliance Chart box's strings (DET-54, DD-849): title and legend. */

export interface ComplianceChartDef {
    /** The box's title (the `complianceChart` key's text). */
    readonly title: string;
    /** The legend's first row — the red swatch's label. */
    readonly nonCompliant: string;
    /** The legend's second row — the green swatch's label. */
    readonly compliant: string;
}

/** The layout key: one of the ten m4i catalogue types. */

export type M4iLayoutType =
    | "m4i_data_domain"
    | "m4i_data_entity"
    | "m4i_data_attribute"
    | "m4i_field"
    | "m4i_data_quality"
    | "m4i_gov_data_quality"
    | "m4i_dataset"
    | "m4i_collection"
    | "m4i_system"
    | "m4i_generic_process"
    | "m4i_person";
