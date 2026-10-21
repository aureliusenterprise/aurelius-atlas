import { ComponentFixture, TestBed } from "@angular/core/testing";
import { faTable } from "@fortawesome/free-solid-svg-icons";

import { EntityCard } from "./entity-card.component";

describe("EntityCard", () => {
    let component: EntityCard;
    let fixture: ComponentFixture<EntityCard>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [EntityCard],
        }).compileComponents();

        fixture = TestBed.createComponent(EntityCard);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("renders the Bulma card anatomy (UIC-12)", () => {
        fixture.componentRef.setInput("guid", "g1");
        fixture.componentRef.setInput("name", "Sales Domain");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".card > .card-content")).toBeTruthy();
        const title = fixture.nativeElement.querySelector(".media .media-content p.title.is-4 a");
        expect(title).toBeTruthy();
        expect(title.textContent.trim()).toBe("Sales Domain");
        // The href is the keyboard path: a native anchor activates on Enter,
        // the click handler emits and cancels the fragment navigation (DD-066).
        expect(title.getAttribute("href")).toBe("#");
    });

    it("emits entityClicked on a title click, without navigating (DD-066, UIC-12)", () => {
        fixture.componentRef.setInput("guid", "g1");
        fixture.componentRef.setInput("name", "Sales Domain");
        fixture.detectChanges();
        const clicked: string[] = [];
        component.entityClicked.subscribe((guid) => clicked.push(guid));

        fixture.nativeElement.querySelector(".title.is-4 a").click();

        expect(clicked).toEqual(["g1"]);
    });

    it("renders the type-name badge: icon, alias over name, no suffix by default (UIC-12)", () => {
        fixture.componentRef.setInput("typeName", "m4i_data_domain");
        fixture.componentRef.setInput("typeIcon", faTable);
        fixture.componentRef.setInput("typeIconClass", "business");
        fixture.detectChanges();

        const badge = fixture.nativeElement.querySelector(".media-right .icon-text");
        expect(badge).toBeTruthy();
        expect(badge.getAttribute("title")).toBe("m4i_data_domain");
        expect(badge.querySelector(".icon svg")).toBeTruthy();
        expect(badge.querySelector(".icon").classList.contains("business")).toBe(true);
        expect(badge.textContent).toContain("m4i_data_domain");
        expect(badge.textContent).not.toContain("(");
    });

    it("prefers the alias and shows the base-type suffix on request (UIC-12)", () => {
        fixture.componentRef.setInput("typeName", "m4i_data_domain");
        fixture.componentRef.setInput("typeAlias", "Domain");
        fixture.componentRef.setInput("showBaseTypeName", true);
        fixture.detectChanges();

        const badge = fixture.nativeElement.querySelector(".media-right .icon-text");
        expect(badge.getAttribute("title")).toBe("Domain");
        expect(badge.textContent).toContain("Domain");
        expect(badge.textContent).toContain("(m4i_data_domain)");
    });

    it("hides the badge icon or name on request (UIC-12)", () => {
        fixture.componentRef.setInput("typeName", "m4i_data_domain");
        fixture.componentRef.setInput("typeIcon", faTable);
        fixture.componentRef.setInput("showIcon", false);
        fixture.componentRef.setInput("showTypeName", false);
        fixture.detectChanges();

        const badge = fixture.nativeElement.querySelector(".media-right .icon-text");
        expect(badge.querySelector(".icon")).toBeNull();
        expect(badge.textContent.trim()).toBe("");
    });

    it("omits the badge without a name (UIC-12)", () => {
        expect(fixture.nativeElement.querySelector(".media-right .icon-text")).toBeNull();
    });

    it("renders the quality column and its slot on request (UIC-12)", () => {
        fixture.componentRef.setInput("showQuality", true);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".columns .column.is-narrow.quality")).toBeTruthy();
    });

    it("omits the quality column on request (UIC-12)", () => {
        fixture.componentRef.setInput("showQuality", false);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".columns .column.is-narrow.quality")).toBeNull();
    });

    it("swaps the body for the loading row with the loader (UIC-12)", () => {
        fixture.componentRef.setInput("name", "Sales Domain");
        fixture.componentRef.setInput("loading", true);
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".title.is-4")).toBeNull();
        expect(fixture.nativeElement.querySelector(".media h6.title.is-6")).toBeTruthy();
        expect(fixture.nativeElement.querySelector(".media-right .loader")).toBeTruthy();
    });

    it("interpolates the name into the loading label, as the Aurelius string did (UIC-12)", () => {
        fixture.componentRef.setInput("name", "Sales Domain");
        fixture.componentRef.setInput("loading", true);
        fixture.componentRef.setInput("loadingLabel", "Loading");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("h6.title.is-6").textContent.trim()).toBe("Loading Sales Domain...");
    });

    it("keeps the loading label bare without a name (DD-047)", () => {
        fixture.componentRef.setInput("loading", true);
        fixture.componentRef.setInput("loadingLabel", "Bezig met laden");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector("h6.title.is-6").textContent.trim()).toBe("Bezig met laden");
    });
});
