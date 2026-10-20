import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { SortableTable } from "./sortable-table.component";
import { TableColumn, TableRow } from "./table-column";

type Row = { name: string; size: number };

/**
 * Host wrapper declaring the table through content templates, as a caller
 * does. Its state is signals — under zoneless change detection a plain
 * field write never marks the view dirty, so `detectChanges` would skip it.
 */
@Component({
    imports: [SortableTable, TableColumn, TableRow],
    template: `
        <aurelius-atlas-ui-sortable-table
            [rows]="rows()"
            [pageSize]="pageSize()"
            [loading]="loading()"
            (rowClicked)="clicked.push($event)"
            (rowSelected)="selected.push($event)"
            (rowDeselected)="deselected.set(deselected() + 1)"
            (pageChanged)="pages.push($event)"
        >
            <ng-template aurelius-atlas-ui-table-column sortBy="name">Name</ng-template>
            <ng-template aurelius-atlas-ui-table-column sortBy="size">Size</ng-template>
            <ng-template aurelius-atlas-ui-table-column [isNarrow]="true">Actions</ng-template>
            <ng-template aurelius-atlas-ui-table-row let-row>
                <td>{{ row.name }}</td>
                <td>{{ row.size }}</td>
                <td>–</td>
            </ng-template>
        </aurelius-atlas-ui-sortable-table>
    `,
})
class Host {
    readonly rows = signal<Row[]>([
        { name: "beta", size: 2 },
        { name: "alpha", size: 3 },
        { name: "gamma", size: 1 },
    ]);

    readonly pageSize = signal(10);
    readonly loading = signal(false);
    readonly deselected = signal(0);
    readonly clicked: Row[] = [];
    readonly selected: Row[] = [];
    readonly pages: number[] = [];
}

describe("SortableTable", () => {
    let host: Host;
    let fixture: ComponentFixture<Host>;

    function root(): HTMLElement {
        return fixture.nativeElement as HTMLElement;
    }

    function headers(): HTMLElement[] {
        return Array.from(root().querySelectorAll("thead th"));
    }

    function bodyRows(): HTMLTableRowElement[] {
        return Array.from(root().querySelectorAll("tbody tr"));
    }

    function cellTexts(rowIndex: number): string[] {
        return Array.from(bodyRows()[rowIndex].querySelectorAll("td")).map((td) => td.textContent?.trim() ?? "");
    }

    async function clickHeader(index: number): Promise<void> {
        (headers()[index].querySelector("button") as HTMLElement).click();
        fixture.detectChanges();
        await fixture.whenStable();
    }

    beforeEach(async () => {
        await TestBed.configureTestingModule({ imports: [Host] }).compileComponents();
        fixture = TestBed.createComponent(Host);
        fixture.detectChanges();
        host = fixture.componentInstance;
        await fixture.whenStable();
    });

    it("renders header content and row templates (UIC-01)", () => {
        expect(headers().map((th) => th.textContent?.trim())).toEqual(["Name", "Size", "Actions"]);
        expect(bodyRows()).toHaveLength(3);
        expect(cellTexts(0)).toEqual(["beta", "2", "–"]);
    });

    it("keeps the source order while unsorted (UIC-05)", () => {
        expect(cellTexts(0)[0]).toBe("beta");
        expect(headers()[0].getAttribute("aria-sort")).toBe("none");
    });

    it("sorts ascending on the first header click (UIC-05)", async () => {
        await clickHeader(0);

        expect(cellTexts(0)[0]).toBe("alpha");
        expect(headers()[0].getAttribute("aria-sort")).toBe("ascending");
        expect(headers()[1].getAttribute("aria-sort")).toBe("none");
    });

    it("cycles to descending on the second click, like matSort (UIC-05)", async () => {
        await clickHeader(0);
        await clickHeader(0);

        expect(cellTexts(0)[0]).toBe("gamma");
        expect(headers()[0].getAttribute("aria-sort")).toBe("descending");
    });

    it("switches the sorted column, starting ascending (UIC-05)", async () => {
        await clickHeader(0);
        await clickHeader(1);

        expect(cellTexts(0)[1]).toBe("1");
        expect(headers()[1].getAttribute("aria-sort")).toBe("ascending");
    });

    it("sorts numbers numerically, not lexicographically (UIC-05)", async () => {
        host.rows.set([
            { name: "x", size: 10 },
            { name: "y", size: 9 },
            { name: "z", size: 20 },
        ]);
        fixture.detectChanges();
        await fixture.whenStable();
        await clickHeader(1);

        expect(cellTexts(0)[1]).toBe("9");
    });

    it("statics a column without sortBy: no button (UIC-05)", () => {
        expect(headers()[2].querySelector("button")).toBeNull();
    });

    it("emits rowClicked and selects on a row click (UIC-01)", async () => {
        bodyRows()[0].click();
        fixture.detectChanges();
        await fixture.whenStable();

        expect(host.clicked.map((row) => row.name)).toEqual(["beta"]);
        expect(host.selected.map((row) => row.name)).toEqual(["beta"]);
        expect(bodyRows()[0].classList.contains("is-selected")).toBe(true);
    });

    it("deselects on a second click of the same row, like Aurelius did (UIC-01)", async () => {
        bodyRows()[0].click();
        fixture.detectChanges();
        await fixture.whenStable();
        bodyRows()[0].click();
        fixture.detectChanges();
        await fixture.whenStable();

        expect(host.selected).toHaveLength(1);
        expect(host.deselected()).toBe(1);
        expect(root().querySelector("tr.is-selected")).toBeNull();
    });

    it("pages client-side and emits pageChanged (UIC-05)", async () => {
        host.pageSize.set(2);
        fixture.detectChanges();
        await fixture.whenStable();

        expect(bodyRows()).toHaveLength(2);
        expect(root().querySelector(".pagination")).toBeTruthy();

        const next = root().querySelector(".pagination-next") as HTMLButtonElement;
        expect(next.disabled).toBe(false);
        next.click();
        fixture.detectChanges();
        await fixture.whenStable();

        expect(host.pages).toEqual([1]);
        expect(bodyRows()).toHaveLength(1);
    });

    it("hides the pagination for a single page", () => {
        expect(root().querySelector(".pagination")).toBeNull();
    });

    it("shows the Aurelius empty state, with the chrome unit (UIC-04)", async () => {
        host.rows.set([]);
        fixture.detectChanges();
        await fixture.whenStable();

        const empty = root().querySelector("p.content.has-text-centered");
        expect(empty?.textContent?.trim()).toBe("No data available");
        expect(root().querySelector("table")).toBeNull();
    });

    it("shows a spinner while loading (UIC-01)", async () => {
        host.loading.set(true);
        fixture.detectChanges();
        await fixture.whenStable();

        expect(root().querySelector('[role="status"]')).toBeTruthy();
        expect(root().querySelector("table")).toBeNull();
    });
});
