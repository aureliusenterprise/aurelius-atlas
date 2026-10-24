import { ComponentFixture, TestBed } from "@angular/core/testing";

import { PropertiesItem } from "./properties-item.component";

describe("PropertiesItem", () => {
    let fixture: ComponentFixture<PropertiesItem>;

    function set(value: unknown): void {
        fixture.componentRef.setInput("value", value);
        fixture.detectChanges();
    }

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [PropertiesItem],
        }).compileComponents();

        fixture = TestBed.createComponent(PropertiesItem);
        fixture.detectChanges();
    });

    it("title-cases a string value, as the legacy template did (UIC-13)", () => {
        set("sales domain");

        expect(fixture.nativeElement.textContent.trim()).toBe("Sales Domain");
    });

    it("renders a number title-cased (UIC-13)", () => {
        set(42);

        expect(fixture.nativeElement.textContent.trim()).toBe("42");
    });

    it("renders a boolean title-cased (UIC-13)", () => {
        set(true);

        expect(fixture.nativeElement.textContent.trim()).toBe("True");
    });

    it("renders link arrays as anchors with an href keyboard path (UIC-13)", () => {
        set([
            { guid: "g1", displayText: "Owner" },
            { guid: "g2", displayText: "Steward" },
        ]);

        const anchors = fixture.nativeElement.querySelectorAll("a");
        expect(anchors).toHaveLength(2);
        expect(anchors[0].textContent.trim()).toBe("Owner");
        expect(anchors[1].textContent.trim()).toBe("Steward");
        // The href is the keyboard path: a native anchor activates on Enter,
        // the click handler emits and cancels the fragment navigation.
        expect(anchors[0].getAttribute("href")).toBe("#");
    });

    it("emits itemClicked with the link guid (UIC-13, DD-154)", () => {
        set([{ guid: "g1", displayText: "Owner" }]);
        const clicked: string[] = [];
        fixture.componentInstance.itemClicked.subscribe((guid) => clicked.push(guid));

        fixture.nativeElement.querySelector("a").click();

        expect(clicked).toEqual(["g1"]);
    });

    it("renders the N/A label for an empty array (UIC-13)", () => {
        set([]);

        expect(fixture.nativeElement.querySelector("div").textContent.trim()).toBe("N/A");
    });

    it("names the empty label from the caller (DD-136)", () => {
        fixture.componentRef.setInput("emptyLabel", "Geen");
        set([]);

        expect(fixture.nativeElement.querySelector("div").textContent.trim()).toBe("Geen");
    });

    it("renders nothing for a plain object, as the legacy component did (UIC-13)", () => {
        set({ nested: true });

        expect(fixture.nativeElement.textContent.trim()).toBe("");
    });

    it("renders nothing for a null value (UIC-13)", () => {
        set(null);

        expect(fixture.nativeElement.textContent.trim()).toBe("");
    });
});
