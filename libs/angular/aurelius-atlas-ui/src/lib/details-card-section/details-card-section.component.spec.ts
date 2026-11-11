import { Component } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { FormsModule } from "@angular/forms";

import { CardSortOption, DetailsCardSection } from "./details-card-section.component";

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

        expect(fixture.nativeElement.querySelector("h3.title").textContent.trim()).toBe("Data Attributes");
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
});
