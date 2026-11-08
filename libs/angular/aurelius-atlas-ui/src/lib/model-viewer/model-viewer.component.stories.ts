import { computed, signal } from "@angular/core";
import type { Meta, StoryObj } from "@storybook/angular";
import { expect, waitFor } from "storybook/test";

import { ModelViewer } from "./model-viewer.component";
import { AR3_ICON_TYPES, NO_RELATION_OPTIONS } from "./archimate-shapes";
import { CATEGORY_PALETTE, deriveCategoryLegend } from "./category-colors";
import type { Ar3DiagramModel, Ar3RelationOptions, Ar3View, Ar3ViewConnection, Ar3ViewNode } from "./ar3-types";

/**
 * The model viewer canvas (DD-419): one ar3 view drawn like the legacy
 * modelview2. These stories show every shape family, layer fill, junction,
 * and relation marker the ported tables know, so each can be checked with an
 * eye. The models are hand-built literals — each story states the shapes it
 * wants to show, not a fetched document. Pan and zoom work here too: drag
 * and the wheel ride the canvas (LDG-16).
 */

/**
 * A palette colour as a browser reports it: a real browser serialises an
 * inline `fill` back as `rgb(r, g, b)`, so a play pin compares against this
 * form, not the hex the palette stores.
 */
function rgb(hex: string): string {
    if (hex.startsWith("rgb")) {
        return hex;
    }
    const n = parseInt(hex.slice(1), 16);
    return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
}

/** One placed node of a story fixture. */
interface PlacedNode {
    /** The element's `@xsi_type` — the key of the shape, fill, and glyph tables. */
    readonly type: string;
    readonly x: number;
    readonly y: number;
    readonly width?: number;
    readonly height?: number;
    /** The name to draw (an empty string draws none). Defaults to the key. */
    readonly name?: string;
}

/** One connection of a story fixture. */
interface PlacedConnection {
    /** The relation's `@xsi_type`, or null for the untabled plain line. */
    readonly type: string | null;
    readonly source: string;
    readonly target: string;
    readonly name?: string;
    /** The relation's styling options (LDG-36: accessType, isDirected). */
    readonly options?: Ar3RelationOptions;
}

/** The layout grid the fixtures place nodes on. */
const COL = 260;
const ROW = 150;

/**
 * Build a model and its single view from the fixture (UIC-29's input shape).
 * The node's concept is its key — the element it references — so
 * `selected`/`highlightedGuid` read the same keys the fixture names.
 * @param nodes the nodes by key, placed by x/y
 * @param connections the connections, named by source/target key
 */
function diagram(
    nodes: Record<string, PlacedNode>,
    connections: readonly PlacedConnection[] = [],
): { model: Ar3DiagramModel; view: Ar3View } {
    const view: Ar3View = {
        id: "v1",
        name: "The View",
        nodes: Object.entries(nodes).map(([key, placed]) => ({
            id: `n-${key}`,
            ref: key,
            label: "",
            displayName: placed.name ?? key,
            x: placed.x,
            y: placed.y,
            width: placed.width ?? 140,
            height: placed.height ?? 70,
        })),
        connections: connections.map((connection, index) => ({
            id: `c${index + 1}`,
            ref: connection.type === null ? null : `r${index + 1}`,
            source: `n-${connection.source}`,
            target: `n-${connection.target}`,
            displayName: connection.name ?? "",
            bendpoints: [],
        })),
    };
    const model: Ar3DiagramModel = {
        elements: new Map(Object.entries(nodes).map(([key, placed]) => [key, { type: placed.type }])),
        relations: new Map(
            connections.flatMap((connection, index) =>
                connection.type === null
                    ? []
                    : [
                          [
                              `r${index + 1}`,
                              {
                                  id: `r${index + 1}`,
                                  type: connection.type,
                                  options: connection.options ?? NO_RELATION_OPTIONS,
                              },
                          ] as const,
                      ],
            ),
        ),
        views: [view],
    };
    return { model, view };
}

/** The shipped lineage chain: dataset, process, dataset (7.22b's fixture). */
const lineageChain = diagram(
    {
        topic: { type: "lineage_dataset", x: 0, y: 70, name: "Ingest Topic" },
        job: { type: "lineage_process", x: COL, y: 70, name: "Load Job" },
        table: { type: "lineage_dataset", x: COL * 2, y: 70, name: "Sales Table" },
    },
    [
        { type: "lineage_relation", source: "topic", target: "job" },
        { type: "lineage_relation", source: "job", target: "table" },
    ],
);

/** The host template: the canvas inside a fixed drawing box. */
const template = `
<div [style.width.px]="width" [style.height.px]="height">
    <aurelius-atlas-ui-model-viewer
        [model]="model"
        [view]="view"
        [selected]="selected"
        [highlightedGuid]="highlightedGuid"
        [categories]="categories"
        [categoryColors]="categoryColors"
        (conceptSelected)="onClick($event)"
    />
</div>
`;

/** The canvas clicks this story collects (UIC-29's emit seam). */
const clicked: string[] = [];

const host = (args: Record<string, unknown>) => ({
    props: {
        width: 760,
        height: 300,
        selected: null,
        highlightedGuid: null,
        categories: null,
        categoryColors: null,
        ...args,
        onClick: (concept: string) => clicked.push(concept),
    },
    template,
});

const meta: Meta<ModelViewer> = {
    component: ModelViewer,
    title: "Model Viewer",
    args: { model: lineageChain.model, view: lineageChain.view, selected: null, highlightedGuid: null },
    argTypes: { model: { control: false }, view: { control: false } },
};
export default meta;
type Story = StoryObj<ModelViewer>;

/**
 * The shipped chain: two pale-blue datasets around a pale-teal process, each
 * a plain rectangle with its glyph (the database card, the gear), the
 * generic arrows of `lineage_relation` between them. Click a node — the
 * canvas emits its concept (the story prints it to the console).
 */
export const LineageChain: Story = {
    render: host,
    play: async ({ canvasElement }) => {
        const canvas = canvasElement as HTMLElement;
        await expect([...canvas.querySelectorAll(".node-text")].map((text) => text.textContent?.trim())).toEqual([
            "Ingest Topic",
            "Load Job",
            "Sales Table",
        ]);
        // A node click emits its concept (LDG-17) — the caller answers.
        clicked.length = 0;
        const nodes = [...canvas.querySelectorAll("g.node")];
        (nodes[1] as SVGGElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await expect(clicked).toEqual(["job"]);
    },
};

/**
 * The six basic shapes the legacy `basicShapes` compose: rectangle, rounded,
 * ellipse, octagon, the grouping folder, and the waved deliverable. Each
 * shows its type's glyph and its layer fill; the grouping hides its icon.
 */
export const BasicShapes: Story = {
    args: {
        ...diagram({
            rectangle: { type: "ar3_ApplicationComponent", x: 0, y: 0, name: "Rectangle" },
            rounded: { type: "ar3_BusinessProcess", x: COL, y: 0, name: "Rounded" },
            ellipse: { type: "ar3_Value", x: COL * 2, y: 0, name: "Ellipse" },
            octagon: { type: "ar3_Goal", x: 0, y: ROW, name: "Octagon" },
            grouping: { type: "ar3_Grouping", x: COL, y: ROW, name: "Grouping" },
            waved: { type: "ar3_Deliverable", x: COL * 2, y: ROW, name: "Waved" },
        }),
        height: 360,
    } as Record<string, unknown>,
    render: host,
    play: async ({ canvasElement }) => {
        const canvas = canvasElement as HTMLElement;
        // The grouping draws no icon, the other five show one (LDG-33).
        await expect(canvas.querySelectorAll("g.node")).toHaveLength(6);
        await expect(canvas.querySelectorAll(".node-icon")).toHaveLength(5);
    },
};

/**
 * The ten layer fills of `archimate3.scss`: business yellow, application
 * cyan, technology and physical green, motivation lavender, implementation
 * pink, strategy sand, And black, Or white, location orange. The Or dot's
 * white fill sits on the white ground — its gray stroke is the only edge.
 */
export const LayerFills: Story = {
    args: {
        ...diagram({
            business: { type: "ar3_BusinessActor", x: 0, y: 0, name: "Business" },
            application: { type: "ar3_DataObject", x: COL, y: 0, name: "Application" },
            technology: { type: "ar3_Device", x: COL * 2, y: 0, name: "Technology" },
            physical: { type: "ar3_Facility", x: COL * 3, y: 0, name: "Physical" },
            motivation: { type: "ar3_Goal", x: 0, y: ROW, name: "Motivation" },
            implementation: { type: "ar3_WorkPackage", x: COL, y: ROW, name: "Implementation" },
            strategy: { type: "ar3_Capability", x: COL * 2, y: ROW, name: "Strategy" },
            location: { type: "ar3_Location", x: COL * 3, y: ROW, name: "Location" },
            and: { type: "ar3_AndJunction", x: 130, y: ROW * 2 + 20, width: 14, height: 14 },
            or: { type: "ar3_OrJunction", x: 180, y: ROW * 2 + 20, width: 14, height: 14 },
        }),
        height: 430,
        width: 1060,
    } as Record<string, unknown>,
    render: host,
    play: async ({ canvasElement }) => {
        await expect((canvasElement as HTMLElement).querySelectorAll("g.node")).toHaveLength(10);
    },
};

/**
 * The junctions and the folder: And and Or are unlabelled dots (the legacy
 * hides both icon and name), the Grouping is a folder with its name but no
 * icon. The last node's type carries no row in the tables — the plain,
 * unfilled rectangle of LDG-13's fallback, its glyph missing as the legacy's
 * icon table carried none.
 */
export const JunctionsAndFolder: Story = {
    args: {
        ...diagram({
            and: { type: "ar3_AndJunction", x: 0, y: 40, width: 14, height: 14 },
            or: { type: "ar3_OrJunction", x: 80, y: 40, width: 14, height: 14 },
            folder: { type: "ar3_Grouping", x: 200, y: 0, name: "Sales Domain" },
            plain: { type: "ar3_Junction", x: COL + 140, y: 0, name: "Untabled type" },
        }),
        height: 200,
    } as Record<string, unknown>,
    render: host,
    play: async ({ canvasElement }) => {
        const canvas = canvasElement as HTMLElement;
        // Only the folder and the untabled node draw a name; no glyph rides.
        await expect(canvas.querySelectorAll(".node-text")).toHaveLength(2);
        await expect(canvas.querySelectorAll(".node-icon")).toHaveLength(0);
    },
};

/** One row of the relation table (the order of the legacy `ar3Relations`). */
interface RelationRow {
    readonly label: string;
    readonly type: string | null;
    readonly options?: Ar3RelationOptions;
}

/** Every relation style, in the legacy table's order (LDG-36). */
const RELATION_ROWS: readonly RelationRow[] = [
    { label: "Aggregation", type: "ar3_Aggregation" },
    { label: "Assignment", type: "ar3_Assignment" },
    { label: "Composition", type: "ar3_Composition" },
    { label: "Flow (dash 4,2)", type: "ar3_Flow" },
    { label: "Influence (dash 4,2)", type: "ar3_Influence" },
    { label: "Realization (dash 2,2)", type: "ar3_Realization" },
    { label: "Serving", type: "ar3_Serving" },
    { label: "Specialization", type: "ar3_Specialization" },
    { label: "Triggering", type: "ar3_Triggering" },
    { label: "Lineage", type: "lineage_relation" },
    { label: "Access Read (dash 2,2)", type: "ar3_Access", options: { accessType: "Read", isDirected: "" } },
    { label: "Access Write (dash 2,2)", type: "ar3_Access", options: { accessType: "Write", isDirected: "" } },
    { label: "Access Read/Write (2,2)", type: "ar3_Access", options: { accessType: "ReadWrite", isDirected: "" } },
    { label: "Association directed", type: "ar3_Association", options: { accessType: "", isDirected: "true" } },
    { label: "Association plain", type: "ar3_Association", options: { accessType: "", isDirected: "" } },
    { label: "No relation (plain line)", type: null },
];

/**
 * The relation rows as one model: two lanes of eight, each row a dataset
 * pair 240 px apart with the relation between. The row's label sits on the
 * source node; the connection stays unnamed.
 */
function relationRowsModel(): { model: Ar3DiagramModel; view: Ar3View } {
    const nodes: Ar3ViewNode[] = [];
    const connections: Ar3ViewConnection[] = [];
    const elements = new Map<string, { type: string }>();
    const relations = new Map<string, { id: string; type: string; options: Ar3RelationOptions }>();
    RELATION_ROWS.forEach((row, index) => {
        const col = index % 2;
        const lane = Math.floor(index / 2);
        const x = col * 620;
        const y = lane * 110;
        for (const end of ["from", "to"] as const) {
            const key = `${index}-${end}`;
            nodes.push({
                id: `n-${key}`,
                ref: key,
                label: "",
                displayName: end === "from" ? row.label : "",
                x: x + (end === "from" ? 0 : 240),
                y,
                width: 120,
                height: 46,
            });
            elements.set(key, { type: "lineage_dataset" });
        }
        const ref = row.type === null ? null : `r-${index}`;
        connections.push({
            id: `c-${index}`,
            ref,
            source: `n-${index}-from`,
            target: `n-${index}-to`,
            displayName: "",
            bendpoints: [],
        });
        if (row.type !== null && ref !== null) {
            relations.set(ref, {
                id: ref,
                type: row.type,
                options: row.options ?? NO_RELATION_OPTIONS,
            });
        }
    });
    const view: Ar3View = { id: "v1", name: "The Relations", nodes, connections };
    return { model: { elements, relations, views: [view] }, view };
}

const relationRows = relationRowsModel();

/**
 * Every relation style of the legacy `ar3Relations` table, one pair of
 * datasets each: the filled and open arrows, the white and black diamonds,
 * the block arrows, the access hooks (Read, Write, Read/Write), the directed
 * Association's open V, the dashes (Flow/Influence 4,2, Realization/Access
 * 2,2). The last row's connection references no relation — the plain line,
 * no markers, no dash, as the legacy's missing row drew it.
 */
export const RelationStyles: Story = {
    args: { model: relationRows.model, view: relationRows.view, width: 1040, height: 940 } as Record<string, unknown>,
    render: host,
    play: async ({ canvasElement }) => {
        const canvas = canvasElement as HTMLElement;
        await expect(canvas.querySelectorAll("g.node")).toHaveLength(32);
        await expect(canvas.querySelectorAll("g.connection")).toHaveLength(16);
    },
};

/**
 * The caller's state painted (UIC-29): the selected process rides the
 * legacy's turquoise stroke (#40e0d0), the highlighted dataset its green
 * (hsl(141, 53%, 53%)). The canvas owns no state — the inputs paint it.
 */
export const SelectionAndHighlight: Story = {
    args: { selected: "job", highlightedGuid: "topic" },
    render: host,
    play: async ({ canvasElement }) => {
        const canvas = canvasElement as HTMLElement;
        await expect(canvas.querySelector("g.node.is-selected.process")).toBeTruthy();
        await expect(canvas.querySelector("g.node.is-highlighted.dataset")).toBeTruthy();
    },
};

/**
 * A relation that carries a name draws it along the path (LDG-14's
 * textPath, gated on a non-empty name).
 */
export const NamedConnection: Story = {
    args: {
        ...diagram(
            {
                feed: { type: "lineage_dataset", x: 0, y: 40, name: "Kafka Topic" },
                sink: { type: "lineage_process", x: COL * 2, y: 40, name: "BigQuery Sink" },
            },
            [{ type: "lineage_relation", source: "feed", target: "sink", name: "streams into" }],
        ),
        height: 200,
    } as Record<string, unknown>,
    render: host,
    play: async ({ canvasElement }) => {
        const label = (canvasElement as HTMLElement).querySelector("textPath")?.textContent?.trim();
        await expect(label).toBe("streams into");
        // The name sits centred beneath the line (LDG-14): the anchor is the
        // midpoint of the 600 px path and the hanging baseline keeps the
        // glyphs below the stroke.
        const text = canvasElement.querySelector("text") as SVGTextElement;
        await expect(text.getAttribute("text-anchor")).toBe("middle");
        const textPath = canvasElement.querySelector("textPath") as SVGTextPathElement;
        await expect(textPath.getAttribute("startOffset")).toBe("50%");
        await expect(textPath.getAttribute("dominant-baseline")).toBe("hanging");
    },
};

/** The All Types grid: eight nodes per row, each its type's shape and glyph. */
const ALL_TYPES_COLS = 8;
const ALL_TYPES_COL = 200;
const ALL_TYPES_ROW = 120;

/** Every glyph-table type as one model: each node named with its type. */
function allTypesModel(): { model: Ar3DiagramModel; view: Ar3View } {
    const nodes: Ar3ViewNode[] = AR3_ICON_TYPES.map((type, index) => ({
        id: `n-${index}`,
        ref: `e-${index}`,
        label: "",
        displayName: type,
        x: (index % ALL_TYPES_COLS) * ALL_TYPES_COL,
        y: Math.floor(index / ALL_TYPES_COLS) * ALL_TYPES_ROW,
        width: 160,
        height: 70,
    }));
    const view: Ar3View = { id: "v1", name: "All Types", nodes, connections: [] };
    const model: Ar3DiagramModel = {
        elements: new Map(AR3_ICON_TYPES.map((type, index) => [`e-${index}`, { type }])),
        relations: new Map(),
        views: [view],
    };
    return { model, view };
}

const allTypes = allTypesModel();

/**
 * Every supported type, one node each: all 62 archimate glyphs and the two
 * lineage ones, each with its shape (LDG-33), its layer fill (LDG-34), and
 * its glyph colour (LDG-35). The node names are the raw `@xsi_type` keys. The
 * And/Or junctions draw as bare dots — the legacy hides both icon and name
 * there (LDG-33) — and the Grouping folder keeps its name but no icon, so
 * those rows show less than their neighbours on purpose.
 */
export const AllTypes: Story = {
    args: { model: allTypes.model, view: allTypes.view, width: 1600, height: 980 } as Record<string, unknown>,
    render: host,
    play: async ({ canvasElement }) => {
        await expect((canvasElement as HTMLElement).querySelectorAll("g.node")).toHaveLength(AR3_ICON_TYPES.length);
    },
};

/** The heat-map-ish chain the colour stories share: five datasets, three buckets. */
const heatChain = diagram(
    {
        raw: { type: "lineage_dataset", x: 0, y: 60, name: "raw.events" },
        stage: { type: "lineage_dataset", x: COL, y: 60, name: "stg.events" },
        mart: { type: "lineage_dataset", x: COL * 2, y: 60, name: "mart.events" },
        audit: { type: "lineage_dataset", x: COL, y: 220, name: "audit.log" },
        report: { type: "lineage_dataset", x: COL * 2, y: 220, name: "report.daily" },
    },
    [
        { type: "lineage_relation", source: "raw", target: "stage" },
        { type: "lineage_relation", source: "stage", target: "mart" },
        { type: "lineage_relation", source: "stage", target: "audit" },
        { type: "lineage_relation", source: "mart", target: "report" },
    ],
);

/** The colour view's buckets, keyed by the fixture's concept ids. */
const heatCategories = { raw: "bronze", stage: "silver", mart: "gold", audit: "silver", report: "gold" };

/**
 * The colour view (UIC-30): the caller's categories replace the class fills
 * with the legend's colours — each distinct category takes the next palette
 * colour in first-seen order, exactly the legacy's `ColorViewService` join.
 * A relation whose concept carries no category keeps its black stroke, as
 * the canvas spec's connection test pins (UIC-30).
 */
export const CategoryColors: Story = {
    args: { ...heatChain, categories: heatCategories, height: 360 } as Record<string, unknown>,
    render: host,
    play: async ({ canvasElement }) => {
        const shapes = [...(canvasElement as HTMLElement).querySelectorAll<SVGPathElement>("g.node path.node-shape")];
        await expect(shapes.map((shape) => shape.style.fill)).toEqual([
            rgb(CATEGORY_PALETTE[0]),
            rgb(CATEGORY_PALETTE[1]),
            rgb(CATEGORY_PALETTE[2]),
            rgb(CATEGORY_PALETTE[1]),
            rgb(CATEGORY_PALETTE[2]),
        ]);
    },
};

/**
 * A picked colour (UIC-31): the drawer's legend table writes an override and
 * the whole category repaints with it — here "gold" was picked to green.
 * The un-picked categories keep their palette colours.
 */
export const CategoryColorsCustom: Story = {
    args: {
        ...heatChain,
        categories: heatCategories,
        categoryColors: { gold: "#22aa44" },
        height: 360,
    } as Record<string, unknown>,
    render: host,
    play: async ({ canvasElement }) => {
        const shapes = [...(canvasElement as HTMLElement).querySelectorAll<SVGPathElement>("g.node path.node-shape")];
        await expect(shapes[2].style.fill).toBe(rgb("#22aa44"));
        await expect(shapes[0].style.fill).toBe(rgb(CATEGORY_PALETTE[0]));
    },
};

/**
 * The playground: the colour view with live pickers, so a reviewer can
 * repaint a category and watch the canvas. Each legend row under the canvas
 * holds a native colour input — the same control the app's View tab ships —
 * and picking one writes an override, so the whole category repaints and
 * the legend row follows. That is the join the app drives through the
 * shared state (UIC-31, DD-420), here with the categories a host would
 * supply. The picks are signals — the story host re-renders on a write the
 * way the app's signal write repaints the drawer — and a story switch or a
 * page reload resets them to the palette, as the app's picks die with the
 * page (DD-420).
 */
const playground = {
    render: () => {
        // The picked overrides (DD-420): category name -> hex, empty at
        // first so the palette answers, as the app's state does.
        const categoryColors = signal<Record<string, string>>({});
        return {
            props: {
                ...heatChain,
                height: 320,
                categories: heatCategories,
                categoryColors,
                // One picked swatch (UIC-31): write the override, the
                // canvas and the legend repaint through the join.
                pick: (category: string, event: Event) =>
                    categoryColors.update((current) => ({
                        ...current,
                        [category]: (event.target as HTMLInputElement).value,
                    })),
                // The legend rows: each category with its current colour,
                // the same join the canvas and the View tab read. Named
                // legendRows, not legend — a story prop lands on the host
                // context and must not shadow anything the reader owns.
                legendRows: computed(() =>
                    Object.entries(deriveCategoryLegend(heatCategories, categoryColors())).map(([category, color]) => ({
                        category,
                        color,
                    })),
                ),
            },
            template: `
<div style="width: 760px">
    <div style="height: 320px">
        <aurelius-atlas-ui-model-viewer
            [model]="model"
            [view]="view"
            [categories]="categories"
            [categoryColors]="categoryColors()"
        />
    </div>
    <table>
        <thead>
            <tr>
                <th>Category</th>
                <th>Colour</th>
            </tr>
        </thead>
        <tbody>
            @for (row of legendRows(); track row.category) {
                <tr>
                    <td>{{ row.category }}</td>
                    <td>
                        <input type="color" [value]="row.color" (input)="pick(row.category, $event)" />
                        {{ row.color }}
                    </td>
                </tr>
            }
        </tbody>
    </table>
</div>
`,
        };
    },
    play: async ({ canvasElement }: { canvasElement: HTMLElement }) => {
        const canvas = canvasElement as HTMLElement;
        // The canvas draws the heat chain and the legend lists its three
        // categories with their pickers. Then a pick is driven — the same
        // control the app's View tab ships: write a colour, the category
        // repaints, and the legend row follows.
        await waitFor(() => expect(canvas.querySelectorAll("tbody tr")).toHaveLength(3));
        const legendRow = (category: string) =>
            [...canvas.querySelectorAll<HTMLTableRowElement>("tbody tr")]
                .find((row) => row.cells[0].textContent?.trim() === category)
                ?.cells[1].textContent?.trim() ?? "";
        const fillAt = (index: number) =>
            (canvas.querySelectorAll<SVGPathElement>("g.node path.node-shape")[index] as SVGPathElement).style.fill;
        const bronze = legendRow("bronze").toLowerCase();
        const silver = legendRow("silver").toLowerCase();
        const gold = legendRow("gold").toLowerCase();
        await expect([fillAt(0), fillAt(1), fillAt(2), fillAt(3), fillAt(4)]).toEqual([
            rgb(bronze),
            rgb(silver),
            rgb(gold),
            rgb(silver),
            rgb(gold),
        ]);
        // Drive the "gold" picker: write a colour into the row's input and
        // fire its event, as a picked swatch does. Both gold nodes take the
        // new colour, the other categories keep theirs, and the legend row
        // follows. The repaint rides the re-render, so wait for it.
        const goldSwatch = [...canvas.querySelectorAll<HTMLInputElement>("tbody input[type='color']")][2];
        goldSwatch.value = "#123456";
        goldSwatch.dispatchEvent(new Event("input", { bubbles: true }));
        await waitFor(() => expect(fillAt(2)).toBe(rgb("#123456")));
        await expect(fillAt(4)).toBe(rgb("#123456"));
        await expect(fillAt(0)).toBe(rgb(bronze));
        await expect(fillAt(1)).toBe(rgb(silver));
        await expect(legendRow("gold").toLowerCase()).toContain("#123456");
    },
};
export const Playground: Story = playground as unknown as Story;
