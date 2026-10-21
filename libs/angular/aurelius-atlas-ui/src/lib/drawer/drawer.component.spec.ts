import { Component, ViewChild } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";

import { Drawer } from "./drawer.component";

describe("Drawer", () => {
    let component: Drawer;
    let fixture: ComponentFixture<Drawer>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Drawer],
        }).compileComponents();

        fixture = TestBed.createComponent(Drawer);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("renders nothing while closed (SPL-02)", () => {
        expect(fixture.nativeElement.querySelector(".aurelius-drawer")).toBeNull();
    });

    it("opens and closes through the model (SPL-02)", () => {
        component.open();
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector(".aurelius-drawer-panel")).toBeTruthy();

        component.close();
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector(".aurelius-drawer")).toBeNull();
    });

    it("toggle flips the open state (SPL-02)", () => {
        component.toggle();
        fixture.detectChanges();
        expect(component.active()).toBe(true);

        component.toggle();
        fixture.detectChanges();
        expect(component.active()).toBe(false);
    });

    it("renders the title heading and the close control (SPL-02)", () => {
        fixture.componentRef.setInput("title", "Settings");
        fixture.componentRef.setInput("ariaLabel", "Settings sluiten");
        component.open();
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".aurelius-drawer-title").textContent.trim()).toBe("Settings");
        const close = fixture.nativeElement.querySelector(".aurelius-drawer-head .delete");
        expect(close.getAttribute("aria-label")).toBe("Settings sluiten");
        const panel = fixture.nativeElement.querySelector(".aurelius-drawer-panel");
        expect(panel.getAttribute("role")).toBe("dialog");
        expect(panel.getAttribute("aria-modal")).toBe("true");
        expect(panel.getAttribute("aria-label")).toBe("Settings");
    });

    it("projects content into the body (SPL-02)", () => {
        const hosted = TestBed.createComponent(HostComponent);
        hosted.detectChanges();
        hosted.componentInstance.drawer.open();
        hosted.detectChanges();

        expect(hosted.nativeElement.querySelector(".aurelius-drawer-body p").textContent).toBe("hello");
    });

    it.each([
        ["a scrim click", ".aurelius-drawer-scrim"],
        ["the close button", ".aurelius-drawer-head .delete"],
    ])("dismisses on %s, emitting cancelRequested (SPL-02)", (_name, selector) => {
        const cancels: void[] = [];
        component.cancelRequested.subscribe(() => cancels.push(undefined));
        component.open();
        fixture.detectChanges();

        (fixture.nativeElement.querySelector(selector) as HTMLElement).click();
        fixture.detectChanges();

        expect(cancels).toHaveLength(1);
        expect(component.active()).toBe(false);
    });

    it("dismisses on Escape on the panel, emitting cancelRequested (SPL-02)", () => {
        const cancels: void[] = [];
        component.cancelRequested.subscribe(() => cancels.push(undefined));
        component.open();
        fixture.detectChanges();

        const panel = fixture.nativeElement.querySelector(".aurelius-drawer-panel") as HTMLElement;
        panel.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        fixture.detectChanges();

        expect(cancels).toHaveLength(1);
        expect(component.active()).toBe(false);
    });

    it("moves focus into the panel on open and back to the opener on close (SPL-02)", () => {
        const opener = document.createElement("button");
        document.body.append(opener);
        opener.focus();
        expect(document.activeElement).toBe(opener);

        component.open();
        fixture.detectChanges();
        const panel = fixture.nativeElement.querySelector(".aurelius-drawer-panel");
        expect(document.activeElement).toBe(panel);

        component.close();
        fixture.detectChanges();
        expect(document.activeElement).toBe(opener);

        opener.remove();
    });
});

@Component({
    imports: [Drawer],
    template: `
        <aurelius-atlas-ui-drawer #drawer title="Settings">
            <p>hello</p>
        </aurelius-atlas-ui-drawer>
    `,
})
class HostComponent {
    @ViewChild("drawer") drawer!: Drawer;
}
