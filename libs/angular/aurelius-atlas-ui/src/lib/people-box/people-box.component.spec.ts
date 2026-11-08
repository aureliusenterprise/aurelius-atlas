import { ComponentFixture, TestBed } from "@angular/core/testing";

import { PeopleBox, PeopleRow } from "./people-box.component";

describe("PeopleBox", () => {
    let component: PeopleBox;
    let fixture: ComponentFixture<PeopleBox>;

    const rows: PeopleRow[] = [
        {
            label: "Domain Lead(s)",
            people: [{ guid: "d1", displayText: "Ada" }],
        },
        {
            label: "Data Owner(s)",
            people: [
                { guid: "o1", displayText: "Grace" },
                { guid: "o2", displayText: "Alan" },
            ],
        },
        { label: "Data Steward(s)", people: [] },
    ];

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [PeopleBox],
        }).compileComponents();

        fixture = TestBed.createComponent(PeopleBox);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("renders one row per non-empty people end (UIC-28, DET-23)", () => {
        fixture.componentRef.setInput("rows", rows);
        fixture.detectChanges();

        const rendered = fixture.nativeElement.querySelectorAll(".aurelius-people-row");
        expect(rendered).toHaveLength(2);
        expect(rendered[0].textContent).toContain("Domain Lead(s)");
        expect(rendered[0].textContent).toContain("Ada");
    });

    it("joins several people of one row with commas (UIC-28, DET-23)", () => {
        fixture.componentRef.setInput("rows", rows);
        fixture.detectChanges();

        const ownerRow = fixture.nativeElement.querySelectorAll(".aurelius-people-row")[1];
        const links = [...ownerRow.querySelectorAll("a")].map((link: HTMLAnchorElement) => link.textContent.trim());
        expect(links).toEqual(["Grace", "Alan"]);
        expect(ownerRow.textContent).toContain("Grace");
        expect(ownerRow.textContent).toContain("Alan");
    });

    it("links each person by href and emits personClicked on a click (UIC-28, DET-23)", () => {
        fixture.componentRef.setInput("rows", rows);
        fixture.detectChanges();
        const clicked: string[] = [];
        component.personClicked.subscribe((guid) => clicked.push(guid));

        const anchor: HTMLAnchorElement = fixture.nativeElement.querySelector("a");
        expect(anchor.getAttribute("href")).toBe("#");
        anchor.click();

        expect(clicked).toEqual(["d1"]);
    });

    it("shows the placeholder line with every row empty (UIC-28, DET-23)", () => {
        fixture.componentRef.setInput("rows", [
            { label: "Domain Lead(s)", people: [] },
            { label: "Data Owner(s)", people: [] },
        ]);
        fixture.componentRef.setInput("emptyLabel", "No people assigned.");
        fixture.detectChanges();

        const empty = fixture.nativeElement.querySelector("p.aurelius-people-empty");
        expect(empty).toBeTruthy();
        expect(empty.textContent.trim()).toBe("No people assigned.");
        expect(fixture.nativeElement.querySelector("a")).toBeNull();
    });

    it("shows the placeholder line with no rows at all (UIC-28, DET-23)", () => {
        fixture.componentRef.setInput("rows", []);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("p.aurelius-people-empty")).toBeTruthy();
    });

    it("carries the caller's empty label (UIC-28, DET-23)", () => {
        fixture.componentRef.setInput("rows", []);
        fixture.componentRef.setInput("emptyLabel", "Geen mensen toegewezen.");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("p.aurelius-people-empty").textContent.trim()).toBe(
            "Geen mensen toegewezen.",
        );
    });

    it("renders nothing at all when the caller hides the placeholder (UIC-28, DET-23)", () => {
        fixture.componentRef.setInput("rows", []);
        fixture.componentRef.setInput("showEmpty", false);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("p")).toBeNull();
    });

    it("marks the person icon business (UIC-28)", () => {
        fixture.componentRef.setInput("rows", rows);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("fa-icon.business")).toBeTruthy();
    });
});
