import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FormsModule } from "@angular/forms";
import { faSortAlphaDown, faSortAlphaUp, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { CardSortOption, DetailsCardSection } from "./details-card-section.component";

/** The rendered button's first svg path, or null. */
function glyph(button: Element): string | null {
    return button.querySelector("svg path")?.getAttribute("d") ?? null;
}

/** The icon's own path data — the pin compares against the real glyph. */
function alphaPath(icon: IconDefinition): string {
    return icon.icon[4] as string;
}

/** A host projecting two card columns — the section's grid contract. */
@Component({
    selector: "aurelius-atlas-ui-card-project-host",
    imports: [DetailsCardSection],
    template: `
        <aurelius-atlas-ui-details-card-section [title]="'Fields'" [sortOptions]="options">
            <div class="column">one</div>
            <div class="column">two</div>
        </aurelius-atlas-ui-details-card-section>
    `,
})
class ProjectHost {
    readonly options: CardSortOption[] = [{ key: "relevance", label: "Relevance" }];
}

describe("DetailsCardSection", () => {
    let component: DetailsCardSection;
    let fixture: ComponentFixture<DetailsCardSection>;

    const options: CardSortOption[] = [
        { key: "relevance", label: "Relevance" },
        { key: "name", label: "Name" },
    ];

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [DetailsCardSection, FormsModule],
        }).compileComponents();

        fixture = TestBed.createComponent(DetailsCardSection);
        component = fixture.componentInstance;
        fixture.componentRef.setInput("title", "Data Attributes");
        fixture.componentRef.setInput("sortOptions", options);
        fixture.detectChanges();
    });

    it("renders the section title and its seed count (UIC-27, DET-17)", () => {
        fixture.componentRef.setInput("count", 27);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("h2.title").textContent.trim()).toBe("Data Attributes");
        expect(fixture.nativeElement.querySelector("h6.aurelius-card-section-count").textContent).toContain("27");
        expect(fixture.nativeElement.querySelector("h6.aurelius-card-section-count").textContent).toContain(
            "result(s)",
        );
    });

    it("keeps the count line a reset link while unfiltered (UIC-27, DET-20, DD-374)", () => {
        fixture.componentRef.setInput("count", 3);
        fixture.componentRef.setInput("filtered", false);
        fixture.detectChanges();

        // The legacy reset link is always there, underlined; an
        // unfiltered reset is a no-op the parent can ignore.
        const link: HTMLAnchorElement = fixture.nativeElement.querySelector("h6.aurelius-card-section-count a");
        expect(link).toBeTruthy();
        expect(link.textContent).toContain("3");

        let resets = 0;
        component.resetRequested.subscribe(() => resets++);
        link.click();
        expect(resets).toBe(1);
    });

    it("shows the filtered count as a reset link while filtered (UIC-27, DET-20)", () => {
        fixture.componentRef.setInput("filtered", true);
        fixture.componentRef.setInput("filteredCount", 2);
        fixture.detectChanges();

        const link: HTMLAnchorElement = fixture.nativeElement.querySelector("h6.aurelius-card-section-count a");
        expect(link).toBeTruthy();
        expect(link.textContent).toContain("2");
        expect(link.textContent).toContain("result(s)");

        let resets = 0;
        component.resetRequested.subscribe(() => resets++);
        link.click();
        expect(resets).toBe(1);
    });

    it("lists the sort options and binds the selected key (UIC-27, DET-21)", async () => {
        fixture.componentRef.setInput("sort", "relevance");
        fixture.detectChanges();
        // ngModel writes the selected value on a microtask.
        await fixture.whenStable();

        const select: HTMLSelectElement = fixture.nativeElement.querySelector("select");
        expect([...select.options].map((option) => option.textContent?.trim())).toEqual(["Relevance", "Name"]);
        expect(select.value).toBe("relevance");
    });

    it("emits the new key when the sort select changes (UIC-27, DET-21)", () => {
        const select: HTMLSelectElement = fixture.nativeElement.querySelector("select");
        select.value = "name";
        select.dispatchEvent(new Event("change"));
        fixture.detectChanges();

        expect(component.sort()).toBe("name");
    });

    it("toggles the direction button and swaps its glyph (UIC-27, DET-21)", () => {
        fixture.componentRef.setInput("sortDescending", false);
        fixture.detectChanges();
        const button: HTMLButtonElement = fixture.nativeElement.querySelector("button.aurelius-card-section-direction");

        let toggles = 0;
        component.sortDirectionToggled.subscribe(() => toggles++);
        button.click();
        expect(toggles).toBe(1);

        // The glyph is the demo's alphabetical pair, in the legacy's
        // pairing (DET-21): ascending carries faSortAlphaDown and
        // descending faSortAlphaUp — FontAwesome names the glyph for the
        // direction the alphabet runs, and the demo shows the down
        // arrow at its ascending default (measured on the live page;
        // the legacy's own `sortDirection.value ? faSortDown : faSortUp`
        // pairs the same way).
        expect(glyph(button)).toBe(alphaPath(faSortAlphaDown));
        fixture.componentRef.setInput("sortDescending", true);
        fixture.detectChanges();
        expect(glyph(button)).toBe(alphaPath(faSortAlphaUp));
    });

    it("forwards the keyword submit and clear (UIC-27, DET-20)", () => {
        fixture.detectChanges();

        const submitted: (string | null)[] = [];
        component.querySubmitted.subscribe((query) => submitted.push(query));

        const search: HTMLInputElement = fixture.nativeElement.querySelector("input[type='search']");
        search.value = "genome";
        search.dispatchEvent(new Event("input"));
        fixture.detectChanges();
        // The search-field submits on the native `search` event (UIC-01).
        search.dispatchEvent(new Event("search"));
        fixture.detectChanges();

        const clear: HTMLElement = fixture.nativeElement.querySelector("aurelius-atlas-ui-search-field .delete");
        clear?.dispatchEvent(new Event("click"));
        fixture.detectChanges();

        expect(submitted).toContain("genome");
        expect(submitted).toContain(null);
    });

    it("projects its cards into the grid (UIC-27, DET-22)", () => {
        TestBed.resetTestingModule();
        TestBed.configureTestingModule({ imports: [ProjectHost] });
        const withCards = TestBed.createComponent(ProjectHost);
        withCards.detectChanges();

        expect(withCards.nativeElement.querySelectorAll(".aurelius-card-section-grid .column")).toHaveLength(2);
    });

    it("emits nextPage from the scroll button while more remain (UIC-27, DET-22)", () => {
        fixture.componentRef.setInput("allLoaded", false);
        fixture.componentRef.setInput("loadLabel", "Load next page...");
        fixture.detectChanges();

        let pages = 0;
        component.nextPage.subscribe(() => pages++);

        const button: HTMLButtonElement = fixture.nativeElement.querySelector(
            "aurelius-atlas-ui-infinite-scroll-container button",
        );
        expect(button).toBeTruthy();
        button.click();
        expect(pages).toBe(1);
    });

    it("hides the sentinel once every card is loaded (UIC-27, DET-22)", () => {
        fixture.componentRef.setInput("allLoaded", true);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("aurelius-atlas-ui-infinite-scroll-container button")).toBeNull();
    });

    it("opens and closes the facet popover from the funnel button (UIC-42, VCF-08)", () => {
        fixture.componentRef.setInput("facets", [{ key: "typeName", title: "Type Name", items: [] }]);
        fixture.detectChanges();

        const dropdown: HTMLElement = fixture.nativeElement.querySelector(".aurelius-card-section-filter");
        const button: HTMLButtonElement = fixture.nativeElement.querySelector(".aurelius-card-section-funnel");
        expect(dropdown.classList.contains("is-active")).toBe(false);
        expect(button.getAttribute("aria-expanded")).toBe("false");

        button.click();
        fixture.detectChanges();
        expect(dropdown.classList.contains("is-active")).toBe(true);
        expect(button.getAttribute("aria-expanded")).toBe("true");
        expect(button.getAttribute("aria-controls")).toBe(dropdown.querySelector(".dropdown-menu")?.id);

        button.click();
        fixture.detectChanges();
        expect(dropdown.classList.contains("is-active")).toBe(false);
    });

    it("renders the facet groups through FacetList and emits a tick with its group key (UIC-42, VCF-08, VCF-11)", () => {
        fixture.componentRef.setInput("facets", [
            {
                key: "typeName",
                title: "Type Name",
                items: [
                    { value: "m4i_data_attribute", label: "Data Attribute", count: 2, checked: false },
                    { value: "m4i_data_field", label: "Data Field", count: 1, checked: true },
                ],
            },
        ]);
        fixture.detectChanges();
        fixture.nativeElement.querySelector(".aurelius-card-section-funnel").click();
        fixture.detectChanges();

        const menus = fixture.nativeElement.querySelectorAll(".dropdown-content aurelius-atlas-ui-facet-list");
        expect(menus).toHaveLength(1);
        expect(normalize(menus[0].querySelector(".menu-label")?.textContent)).toBe("Type Name");
        const rows = [...menus[0].querySelectorAll(".menu-list li label.checkbox")];
        expect(rows.map((row) => normalize(row.textContent))).toEqual(["Data Attribute (2)", "Data Field (1)"]);
        expect((rows[1].querySelector("input") as HTMLInputElement).checked).toBe(true);

        const toggled: { group: string; value: string; checked: boolean }[] = [];
        component.facetToggled.subscribe((event) => toggled.push(event));
        const box = rows[0].querySelector("input")!;
        box.checked = true;
        box.dispatchEvent(new Event("change"));
        fixture.detectChanges();

        expect(toggled).toEqual([{ group: "typeName", value: "m4i_data_attribute", checked: true }]);
    });

    it("shows the not-available line in an empty popover (UIC-42, VCF-10)", () => {
        fixture.componentRef.setInput("facets", []);
        fixture.componentRef.setInput("notAvailableLabel", "No filters available.");
        fixture.detectChanges();
        fixture.nativeElement.querySelector(".aurelius-card-section-funnel").click();
        fixture.detectChanges();

        const line: HTMLElement = fixture.nativeElement.querySelector(".aurelius-card-section-no-filters");
        expect(normalize(line.textContent)).toBe("No filters available.");
        expect(fixture.nativeElement.querySelector("aurelius-atlas-ui-facet-list")).toBeNull();
    });

    it("marks the funnel's icon while the caller's state is applied (UIC-42, VCF-08, DV-169)", () => {
        // The caller's filterActive carries the whole query-object rule
        // (keyword, selection, sort, direction); the part only paints it.
        // The mark is the glyph's colour, so the button face keeps its
        // background — the scss sets the icon's colour under .is-primary.
        fixture.componentRef.setInput("filterActive", false);
        fixture.detectChanges();
        const button: HTMLButtonElement = fixture.nativeElement.querySelector(".aurelius-card-section-funnel");
        expect(button.classList.contains("is-primary")).toBe(false);

        fixture.componentRef.setInput("filterActive", true);
        fixture.detectChanges();
        expect(button.classList.contains("is-primary")).toBe(true);
    });

    it("closes the open popover on a click outside it (UIC-42, VCF-08)", () => {
        fixture.nativeElement.querySelector(".aurelius-card-section-funnel").click();
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector(".aurelius-card-section-filter").className).toContain("is-active");

        document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector(".aurelius-card-section-filter").className).not.toContain(
            "is-active",
        );
    });
});

/** Collapse an element's text the way the rendered DOM spaces it. */
function normalize(text: string | null | undefined): string {
    return (text ?? "").replace(/\s+/g, " ").trim();
}
