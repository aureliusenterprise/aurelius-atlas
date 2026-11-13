import { ComponentFixture, TestBed } from "@angular/core/testing";

import { Modal } from "./modal.component";

describe("Modal", () => {
    let component: Modal;
    let fixture: ComponentFixture<Modal>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [Modal],
        }).compileComponents();

        fixture = TestBed.createComponent(Modal);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it("renders nothing while closed (UIC-01)", () => {
        expect(fixture.nativeElement.querySelector(".modal")).toBeNull();
    });

    it("opens and closes through the model (UIC-01)", () => {
        component.open();
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector(".modal")).toBeTruthy();

        component.close();
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector(".modal")).toBeNull();
    });

    it("keeps the plain content anatomy when no title is set (UIC-09)", () => {
        component.open();
        fixture.detectChanges();

        expect(fixture.nativeElement.querySelector(".modal-content")).toBeTruthy();
        expect(fixture.nativeElement.querySelector(".modal-card")).toBeNull();
    });

    it("shows the close button by default, hidden on request (UIC-01)", () => {
        component.open();
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector(".modal-close")).toBeTruthy();

        fixture.componentRef.setInput("showCloseButton", false);
        fixture.detectChanges();
        expect(fixture.nativeElement.querySelector(".modal-close")).toBeNull();
    });

    it("closes from the close button, without emitting (plain anatomy unchanged, UIC-09)", () => {
        const cancels: void[] = [];
        component.cancelRequested.subscribe(() => cancels.push(undefined));
        component.open();
        fixture.detectChanges();

        (fixture.nativeElement.querySelector(".modal-close") as HTMLElement).click();
        fixture.detectChanges();

        expect(cancels).toHaveLength(0);
        expect(component.active()).toBe(false);
    });

    describe("card anatomy (UIC-01)", () => {
        beforeEach(() => {
            fixture.componentRef.setInput("title", "Delete branch");
            fixture.componentRef.setInput("confirmLabel", "Delete");
            fixture.componentRef.setInput("cancelLabel", "Close");
            component.open();
            fixture.detectChanges();
        });

        it("renders the legacy header, body and footer (UIC-01)", () => {
            expect(fixture.nativeElement.querySelector(".modal-card-head .modal-card-title").textContent.trim()).toBe(
                "Delete branch",
            );
            expect(fixture.nativeElement.querySelector(".modal-card-body")).toBeTruthy();
            expect(fixture.nativeElement.querySelectorAll(".modal-card-foot .button")).toHaveLength(2);
        });

        it("names the dialog through its title heading (DLG-HEAD-001)", () => {
            const dialog = fixture.nativeElement.querySelector("dialog.aurelius-modal");
            const heading = dialog.querySelector(".modal-card-title");
            expect(heading.tagName).toBe("H2");
            expect(dialog.getAttribute("aria-labelledby")).toBe(heading.id);
            expect(dialog.hasAttribute("aria-label")).toBe(false);
        });

        it("emits confirm from the confirm button and stays open (UIC-01)", () => {
            const confirms: void[] = [];
            component.confirmRequested.subscribe(() => confirms.push(undefined));

            (fixture.nativeElement.querySelector(".modal-card-foot .button.is-success") as HTMLElement).click();

            expect(confirms).toHaveLength(1);
            expect(component.active()).toBe(true);
        });

        it("ignores confirm presses while a caller action is pending (UIC-01)", () => {
            const confirms: void[] = [];
            component.confirmRequested.subscribe(() => confirms.push(undefined));
            fixture.componentRef.setInput("confirmPending", true);
            fixture.detectChanges();

            const confirmButton = fixture.nativeElement.querySelector(".modal-card-foot .button.is-success");
            expect(confirmButton.disabled).toBe(true);
            confirmButton.click();

            expect(confirms).toHaveLength(0);
        });

        it("omits the confirm button without a confirm label (UIC-01)", () => {
            fixture.componentRef.setInput("confirmLabel", undefined);
            fixture.detectChanges();

            expect(fixture.nativeElement.querySelector(".button.is-success")).toBeNull();
            expect(fixture.nativeElement.querySelectorAll(".modal-card-foot .button")).toHaveLength(1);
        });

        it("omits the cancel button without a cancel label (UIC-01)", () => {
            fixture.componentRef.setInput("cancelLabel", undefined);
            fixture.detectChanges();

            expect(fixture.nativeElement.querySelectorAll(".modal-card-foot .button")).toHaveLength(1);
        });

        it.each([
            ["a backdrop click", ".modal-background"],
            ["the header delete button", ".modal-card-head .delete"],
            ["the cancel button", ".modal-card-foot .button:last-child"],
        ] as const)("dismisses from %s (UIC-01)", (_label, selector) => {
            const cancels: void[] = [];
            component.cancelRequested.subscribe(() => cancels.push(undefined));

            (fixture.nativeElement.querySelector(selector) as HTMLElement).click();

            expect(cancels).toHaveLength(1);
            expect(component.active()).toBe(false);
        });

        it("dismisses on the dialog's cancel event, the platform Escape path (UIC-01, UIC-40)", () => {
            const cancels: void[] = [];
            component.cancelRequested.subscribe(() => cancels.push(undefined));
            component.open();
            fixture.detectChanges();

            const dialog = fixture.nativeElement.querySelector("dialog.aurelius-modal") as HTMLDialogElement;
            const event = new Event("cancel", { cancelable: true });
            dialog.dispatchEvent(event);

            // The handler prevents the bare close: dismissal stays the
            // card anatomy's cancelRequested path (the model drives the
            // real close through the effect).
            expect(event.defaultPrevented).toBe(true);
            expect(cancels).toHaveLength(1);
            expect(component.active()).toBe(false);
        });
    });

    it("restores focus to the opener when the layer closes (UIC-40)", () => {
        const opener = document.createElement("button");
        document.body.append(opener);
        opener.focus();
        expect(document.activeElement).toBe(opener);

        component.open();
        fixture.detectChanges();

        component.close();
        fixture.detectChanges();
        expect(document.activeElement).toBe(opener);

        opener.remove();
    });

    it("ignores backdrop clicks in the plain anatomy, as existing callers manage closing (UIC-09)", () => {
        component.open();
        fixture.detectChanges();
        const cancels: void[] = [];
        component.cancelRequested.subscribe(() => cancels.push(undefined));

        (fixture.nativeElement.querySelector(".modal-background") as HTMLElement).click();

        expect(cancels).toHaveLength(0);
        expect(component.active()).toBe(true);
    });

    it("lets Escape close the plain anatomy (MODAL-ESC-001)", () => {
        component.open();
        fixture.detectChanges();
        const cancels: void[] = [];
        component.cancelRequested.subscribe(() => cancels.push(undefined));

        const dialog = fixture.nativeElement.querySelector("dialog.aurelius-modal") as HTMLDialogElement;
        const event = new Event("cancel", { cancelable: true });
        dialog.dispatchEvent(event);

        // No preventDefault: the platform owns the close (in a browser the
        // dialog itself closes, and the close event mirrors it into the
        // model). Here the handler emits nothing and blocks nothing.
        expect(event.defaultPrevented).toBe(false);
        expect(cancels).toHaveLength(0);
        expect(component.active()).toBe(true);
    });

    it("mirrors a native close into the model (MODAL-ESC-001)", () => {
        component.open();
        fixture.detectChanges();

        // The plain anatomy's Escape path in a browser: cancel goes
        // unprevented, the dialog closes natively, and the close event
        // brings the model along so the layer and the caller's binding
        // stay in step.
        const dialog = fixture.nativeElement.querySelector("dialog.aurelius-modal") as HTMLDialogElement;
        dialog.dispatchEvent(new Event("close"));
        fixture.detectChanges();

        expect(component.active()).toBe(false);
    });

    it("names the plain anatomy from the label input (MODAL-NAME-001)", () => {
        fixture.componentRef.setInput("label", "Cookie consent");
        component.open();
        fixture.detectChanges();

        const dialog = fixture.nativeElement.querySelector("dialog.aurelius-modal");
        expect(dialog.getAttribute("aria-label")).toBe("Cookie consent");
        expect(dialog.hasAttribute("aria-labelledby")).toBe(false);
    });
});
