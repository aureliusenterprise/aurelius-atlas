import { ComponentFixture, TestBed } from "@angular/core/testing";
import { faTable } from "@fortawesome/free-solid-svg-icons";

import { Breadcrumb, Breadcrumbs } from "./breadcrumbs.component";

describe("Breadcrumbs", () => {
    let component: Breadcrumbs;
    let fixture: ComponentFixture<Breadcrumbs>;

    const items: Breadcrumb[] = [
        { guid: "g1", name: "Domain", typeName: "m4i_data_domain", icon: faTable, iconClass: "business" },
        { guid: "g2", name: "Entity", typeName: "m4i_data_entity" },
    ];

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Breadcrumbs],
        }).compileComponents();

        fixture = TestBed.createComponent(Breadcrumbs);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("renders nothing without items (UIC-11)", () => {
        expect(fixture.nativeElement.querySelector("nav.breadcrumb")).toBeNull();
    });

    it("renders the Bulma breadcrumb trail with one anchor per item (UIC-11)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.detectChanges();

        const nav = fixture.nativeElement.querySelector("nav.breadcrumb.is-small.has-arrow-separator");
        expect(nav).toBeTruthy();
        expect(nav.getAttribute("aria-label")).toBe("breadcrumbs");
        expect(nav.querySelectorAll("li")).toHaveLength(2);
        expect(nav.querySelectorAll("li a")).toHaveLength(2);
        expect(nav.querySelectorAll("li a")[0].textContent).toContain("Domain");
    });

    it("names the trail from the caller's label (DD-136)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.componentRef.setInput("breadcrumbsLabel", "kruimelpad");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("nav.breadcrumb").getAttribute("aria-label")).toBe("kruimelpad");
    });

    it("renders the active crumb as plain text, not a link (UIC-11, DD-624)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.componentRef.setInput("activeGuid", "g2");
        fixture.detectChanges();

        const listItems = fixture.nativeElement.querySelectorAll("li");
        expect(listItems[0].classList.contains("is-active")).toBe(false);
        expect(listItems[1].classList.contains("is-active")).toBe(true);
        // The active crumb navigates nowhere, so it is a span: no anchor,
        // no href, and it stays out of the link list screen readers tab.
        expect(listItems[1].querySelector("a")).toBeNull();
        const crumb = listItems[1].querySelector("span.truncate");
        expect(crumb.getAttribute("aria-current")).toBe("page");
        expect(crumb.textContent).toContain("Entity");
        // The clickable crumb keeps its anchor.
        expect(listItems[0].querySelector("a")).toBeTruthy();
    });

    it("renders the caller icon and class on a crumb (UIC-15)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.detectChanges();

        const icon = fixture.nativeElement.querySelector("li a .icon svg");
        expect(icon).toBeTruthy();
        expect(fixture.nativeElement.querySelector("li a .icon").getAttribute("title")).toBe("m4i_data_domain");
    });

    it("shows the warning chip above the trail (UIC-11)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.componentRef.setInput("warning", "Breadcrumb path could not be determined");
        fixture.detectChanges();

        const chip = fixture.nativeElement.querySelector(".tag.is-warning");
        expect(chip).toBeTruthy();
        expect(chip.textContent).toContain("Breadcrumb path could not be determined");
    });

    it("emits itemClicked with the guid when a crumb is clicked (UIC-11)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.detectChanges();
        const clicked: string[] = [];
        component.itemClicked.subscribe((guid) => clicked.push(guid));

        fixture.nativeElement.querySelectorAll("li a")[1].click();

        expect(clicked).toEqual(["g2"]);
    });

    it("makes crumbs native anchors, so Enter activates them (UIC-11)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.detectChanges();

        // The href is the keyboard path: a native anchor activates on Enter,
        // the click handler emits and cancels the fragment navigation.
        const anchor: HTMLAnchorElement = fixture.nativeElement.querySelector("li a");
        expect(anchor.getAttribute("href")).toBe("#");
    });

    it("prints every crumb plain with links off and emits nothing (UIC-11, DD-714)", () => {
        fixture.componentRef.setInput("items", items);
        fixture.componentRef.setInput("links", false);
        fixture.detectChanges();

        // The trail sits inside a control that owns the activation (a picker
        // row), so it must hold no nested link and no active/current crumb.
        expect(fixture.nativeElement.querySelectorAll("li a")).toHaveLength(0);
        const crumbs = [...fixture.nativeElement.querySelectorAll("li")];
        expect(crumbs).toHaveLength(2);
        for (const crumb of crumbs) {
            expect(crumb.classList.contains("is-active")).toBe(false);
            expect(crumb.querySelector("span.truncate")?.getAttribute("aria-current")).toBeNull();
        }
        expect(crumbs[0].textContent).toContain("Domain");
        expect(crumbs[1].textContent).toContain("Entity");

        // Even a crumb named activeGuid stays plain: nothing navigates.
        fixture.componentRef.setInput("activeGuid", "g1");
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelectorAll("li a")).toHaveLength(0);
        expect(fixture.nativeElement.querySelector("li").classList.contains("is-active")).toBe(false);
    });
});
