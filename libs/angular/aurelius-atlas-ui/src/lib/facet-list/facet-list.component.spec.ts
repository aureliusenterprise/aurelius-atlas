import { ComponentFixture, TestBed } from "@angular/core/testing";

import { FacetItem, FacetList } from "./facet-list.component";

/** The facet values the specs render: six names, the legacy slice's test set. */
const items: FacetItem[] = [
    { value: "m4i_data_attribute", label: "Data Attribute", count: 75 },
    { value: "m4i_gov_data_quality", label: "Gov. Quality", count: 32 },
    { value: "m4i_data_domain", label: "Data Domain", count: 9 },
    { value: "m4i_field", label: "Data Field", count: 8 },
    { value: "m4i_dataset", label: "Dataset", count: 5 },
    { value: "m4i_person", label: "Person", count: 2 },
];

describe("FacetList", () => {
    let fixture: ComponentFixture<FacetList>;
    let component: FacetList;

    async function setup(selectable = false) {
        await TestBed.configureTestingModule({ imports: [FacetList] }).compileComponents();
        fixture = TestBed.createComponent(FacetList);
        component = fixture.componentInstance;
        fixture.componentRef.setInput("title", "Type");
        fixture.componentRef.setInput("items", items);
        fixture.componentRef.setInput("selectable", selectable);
        fixture.detectChanges();
        return fixture.nativeElement as HTMLElement;
    }

    it("renders the Bulma menu with the title and every labelled row (UIC-33)", async () => {
        const compiled = await setup();

        expect(compiled.querySelector(".menu .menu-label")?.textContent?.trim()).toBe("Type");
        // Five values and the show-more link (UIC-34's cap), not six rows.
        const rows = compiled.querySelectorAll(".menu-list > li");
        expect(rows).toHaveLength(6);
        expect(rows[0].textContent).toContain("Data Attribute");
    });

    it("shows the count in parentheses beside the label (UIC-33)", async () => {
        const compiled = await setup(true);

        const first = compiled.querySelector(".menu-list > li")!;
        expect(first.textContent?.replace(/\s+/g, " ")).toContain("(75)");
    });

    it("renders read-only text rows when not selectable (UIC-34, SDX-05)", async () => {
        const compiled = await setup(false);

        expect(compiled.querySelector("input[type='checkbox']")).toBeNull();
        expect(compiled.querySelector(".menu-list > li .label-text")?.textContent).toContain("Data Attribute");
    });

    it("emits toggled with the wire value and the new state (UIC-34)", async () => {
        const compiled = await setup(true);
        const emitted: { value: string; checked: boolean }[] = [];
        component.toggled.subscribe((event) => emitted.push(event));

        const boxes = compiled.querySelectorAll<HTMLInputElement>("input[type='checkbox']");
        expect(boxes).toHaveLength(5); // UIC-34's five-row slice
        boxes[2].click();
        expect(emitted).toEqual([{ value: "m4i_data_domain", checked: true }]);
        boxes[2].click();
        expect(emitted[1]).toEqual({ value: "m4i_data_domain", checked: false });
    });

    it("starts the rows checked from the item's checked flag (SDX-04)", async () => {
        await TestBed.configureTestingModule({ imports: [FacetList] }).compileComponents();
        fixture = TestBed.createComponent(FacetList);
        fixture.componentRef.setInput("title", "Type");
        fixture.componentRef.setInput("items", [{ value: "x", label: "X", count: 1, checked: true }]);
        fixture.componentRef.setInput("selectable", true);
        fixture.detectChanges();

        const box = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>("input[type='checkbox']");
        expect(box?.checked).toBe(true);
    });

    it("shows the first five values and reveals the rest on show-more (UIC-34)", async () => {
        const compiled = await setup(true);

        expect(compiled.textContent).not.toContain("Person");
        const link = compiled.querySelector<HTMLAnchorElement>("a.read-more")!;
        expect(link.textContent?.trim()).toBe("Show more");

        link.click();
        fixture.detectChanges();

        expect(compiled.textContent).toContain("Person");
        const less = compiled.querySelector<HTMLAnchorElement>("a.read-more")!;
        expect(less.textContent?.trim()).toBe("Show less");

        less.click();
        fixture.detectChanges();
        expect(compiled.textContent).not.toContain("Person");
    });

    it("carries the caller's show-more labels (UIC-34, DD-136)", async () => {
        await TestBed.configureTestingModule({ imports: [FacetList] }).compileComponents();
        fixture = TestBed.createComponent(FacetList);
        fixture.componentRef.setInput("title", "Type");
        fixture.componentRef.setInput("items", items);
        fixture.componentRef.setInput("showMoreLabel", "Meer weergeven");
        fixture.detectChanges();

        const link = (fixture.nativeElement as HTMLElement).querySelector<HTMLAnchorElement>("a.read-more")!;
        expect(link.textContent?.trim()).toBe("Meer weergeven");
    });

    it("renders no link at all for five values or none (UIC-34)", async () => {
        await TestBed.configureTestingModule({ imports: [FacetList] }).compileComponents();
        fixture = TestBed.createComponent(FacetList);
        fixture.componentRef.setInput("title", "Type");
        fixture.componentRef.setInput("items", items.slice(0, 5));
        fixture.detectChanges();
        expect((fixture.nativeElement as HTMLElement).querySelector("a.read-more")).toBeNull();

        fixture.componentRef.setInput("items", []);
        fixture.detectChanges();
        const compiled = fixture.nativeElement as HTMLElement;
        expect(compiled.querySelectorAll(".menu-list > li")).toHaveLength(0);
    });
});
