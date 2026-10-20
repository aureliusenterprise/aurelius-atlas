import type { Meta, StoryObj } from "@storybook/angular";
import { expect, userEvent, within } from "storybook/test";
import { SortableTable } from "./sortable-table.component";
import { TableColumn, TableRow } from "./table-column";

const meta: Meta<SortableTable<Record<string, unknown>>> = {
    component: SortableTable,
    title: "Sortable Table",
};
export default meta;

type Story = StoryObj<SortableTable<Record<string, unknown>>>;

type Row = { name: string; qualifiedName: string; type: string };

const ROWS: Row[] = [
    { name: "Glossary", qualifiedName: "Glossary", type: "glossary_term" },
    { name: "Atlas", qualifiedName: "atlas_type", type: "type" },
    { name: "Sales", qualifiedName: "sales_domain", type: "domain" },
];

const FIVE: Row[] = [
    ...ROWS,
    { name: "Breadth", qualifiedName: "breadth_term", type: "glossary_term" },
    { name: "Curation", qualifiedName: "curation_topic", type: "term" },
];

/**
 * The table is content-driven, so a story hosts it through the
 * column/row `ng-template` blocks a caller writes.
 */
const tableTemplate = (rows: string, pageSize: string, loading: string) => `
<aurelius-atlas-ui-sortable-table [rows]="${rows}" [pageSize]="${pageSize}" [loading]="${loading}">
    <ng-template aurelius-atlas-ui-table-column sortBy="name">Name</ng-template>
    <ng-template aurelius-atlas-ui-table-column sortBy="qualifiedName">Qualified name</ng-template>
    <ng-template aurelius-atlas-ui-table-column sortBy="type">Type</ng-template>
    <ng-template aurelius-atlas-ui-table-row let-row>
        <td>{{ row.name }}</td>
        <td>{{ row.qualifiedName }}</td>
        <td>{{ row.type }}</td>
    </ng-template>
</aurelius-atlas-ui-sortable-table>
`;

export const Primary: Story = {
    args: {
        rows: ROWS,
        pageSize: 10,
        loading: false,
    },
    render: (args) => ({
        moduleMetadata: { imports: [TableColumn, TableRow] },
        props: args,
        template: tableTemplate("rows", "pageSize", "loading"),
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await expect(canvas.getAllByRole("row")).toHaveLength(4);
        await expect(canvas.getAllByRole("row")[1]).toHaveTextContent("Glossary");

        await userEvent.click(canvas.getByRole("button", { name: /Name/ }));
        await expect(canvas.getByRole("columnheader", { name: /Name/ })).toHaveAttribute("aria-sort", "ascending");
        await expect(canvas.getAllByRole("row")[1]).toHaveTextContent("Atlas");
    },
};

export const Sorted: Story = {
    args: {
        rows: ROWS,
        pageSize: 10,
        loading: false,
    },
    render: (args) => ({
        moduleMetadata: { imports: [TableColumn, TableRow] },
        props: args,
        template: tableTemplate("rows", "pageSize", "loading"),
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await userEvent.click(canvas.getByRole("button", { name: /Type/ }));
        await expect(canvas.getAllByRole("row")[1]).toHaveTextContent("Sales");
    },
};

export const Empty: Story = {
    args: {
        rows: [] as Row[],
        pageSize: 10,
        loading: false,
    },
    render: (args) => ({
        moduleMetadata: { imports: [TableColumn, TableRow] },
        props: args,
        template: tableTemplate("rows", "pageSize", "loading"),
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await expect(canvas.getByText("No data available")).toBeInTheDocument();
    },
};

export const Loading: Story = {
    args: {
        rows: ROWS,
        pageSize: 10,
        loading: true,
    },
    render: (args) => ({
        moduleMetadata: { imports: [TableColumn, TableRow] },
        props: args,
        template: tableTemplate("rows", "pageSize", "loading"),
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        await expect(canvas.getByRole("status")).toBeInTheDocument();
    },
};

export const Paginated: Story = {
    args: {
        rows: FIVE,
        pageSize: 2,
        loading: false,
    },
    render: (args) => ({
        moduleMetadata: { imports: [TableColumn, TableRow] },
        props: args,
        template: tableTemplate("rows", "pageSize", "loading"),
    }),
    play: async ({ canvasElement }) => {
        const canvas = within(canvasElement);
        const next = canvas.getByRole("button", { name: "Go to next page" });
        await expect(canvas.getAllByRole("row")).toHaveLength(3);

        await userEvent.click(next);
        await expect(canvas.getAllByRole("row")).toHaveLength(3);
        await expect(canvas.getAllByRole("row")[1]).toHaveTextContent("Sales");
    },
};
