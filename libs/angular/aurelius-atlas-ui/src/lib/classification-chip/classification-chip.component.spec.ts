import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { ClassificationChip } from "./classification-chip.component";

/** The host projects the sources slot — the content the chip must render (DD-099). */
@Component({
    imports: [ClassificationChip],
    template: `
        <aurelius-atlas-ui-classification-chip
            [label]="label()"
            [tooltip]="tooltip()"
            [leadLabel]="leadLabel()"
            [leadColor]="leadColor()"
            [loading]="loading()"
            [propagated]="propagated()"
            [originLabel]="originLabel()"
        >
            <div class="dropdown-divider" chip-sources></div>
            <div class="dropdown-item source-row" chip-sources>Source entity</div>
        </aurelius-atlas-ui-classification-chip>
    `,
})
class HostComponent {
    readonly label = signal("PII");
    // Signal fields: under zoneless, plain host-field writes never mark
    // the view dirty (the lib's spec convention).
    readonly tooltip = signal<string | undefined>("Personally identifiable information");
    readonly leadLabel = signal<string | undefined>(undefined);
    readonly leadColor = signal("is-primary");
    readonly loading = signal(false);
    readonly propagated = signal(false);
    readonly originLabel = signal<string | undefined>(undefined);
}

describe("ClassificationChip", () => {
    let fixture: ComponentFixture<HostComponent>;
    let host: HostComponent;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [HostComponent],
        }).compileComponents();

        fixture = TestBed.createComponent(HostComponent);
        host = fixture.componentInstance;
        fixture.detectChanges();
    });

    const tags = () => (fixture.nativeElement as HTMLElement).querySelectorAll(".tags.has-addons > .tag");

    it("renders the addons chip with the hashtag lead and the label (UIC-16)", () => {
        expect(tags()).toHaveLength(2);
        const lead = fixture.nativeElement.querySelector(".tags .tag.is-primary");
        expect(lead.getAttribute("title")).toBe("Classification");
        expect(lead.getAttribute("aria-hidden")).toBe("true");
        expect(lead.querySelector(".icon svg")).toBeTruthy();
        expect([...tags()].at(-1)!.textContent).toContain("PII");
    });

    it("tooltips the label tag with the caller's description (UIC-16)", () => {
        const label = [...tags()].at(-1) as HTMLElement;
        expect(label.getAttribute("title")).toBe("Personally identifiable information");
    });

    it("omits the title when the caller has no description (UIC-16)", () => {
        host.tooltip.set(undefined);
        fixture.detectChanges();
        expect([...tags()].at(-1)!.hasAttribute("title")).toBe(false);
    });

    it("renders the lead as the kind's word — the term chip (UIC-16, DD-099)", () => {
        host.leadLabel.set("Term");
        host.leadColor.set("is-info");
        fixture.detectChanges();

        const lead = fixture.nativeElement.querySelector(".tags .tag.is-info");
        expect(lead.textContent.trim()).toBe("Term");
        expect(lead.querySelector(".icon svg")).toBeNull();
    });

    it("swaps the label for the loader tag while loading (UIC-16)", () => {
        host.loading.set(true);
        fixture.detectChanges();

        expect(fixture.nativeElement.textContent).not.toContain("PII");
        expect(fixture.nativeElement.querySelector(".tag .loader")).toBeTruthy();
    });

    it("adds the propagation trigger with the Aurelius defaults (UIC-16, UIC-20)", () => {
        host.propagated.set(true);
        fixture.detectChanges();

        const trigger = fixture.nativeElement.querySelector(".tag.is-primary.dropdown.is-hoverable");
        expect(trigger).toBeTruthy();
        expect(trigger.getAttribute("title")).toBe("Is propagated");
        expect(trigger.querySelector(".dropdown-item strong").textContent).toBe("PII");
        expect(trigger.querySelector(".dropdown-item span").textContent).toBe("originates from the following sources:");
        expect(trigger.querySelector(".icon svg")).toBeTruthy();
    });

    it("projects the caller's sources rows into the dropdown (UIC-16, DD-099)", () => {
        host.propagated.set(true);
        fixture.detectChanges();

        const rows = fixture.nativeElement.querySelectorAll(".dropdown-item.source-row");
        expect(rows).toHaveLength(1);
        expect(rows[0].textContent).toBe("Source entity");
    });

    it("localises the origin line from the caller (UIC-20, DD-136)", () => {
        host.propagated.set(true);
        host.originLabel.set("komt voor uit de volgende bronnen:");
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".dropdown-item span").textContent).toBe(
            "komt voor uit de volgende bronnen:",
        );
    });
});
